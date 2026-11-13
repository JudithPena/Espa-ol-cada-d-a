#!/usr/bin/env python3
"""Контрольные снимки грамматического юнита для тестов сохранности.

    python tools/grammar_unit_snapshots.py 48                    # только показать значения
    python tools/grammar_unit_snapshots.py 48 --write            # новый юнит: записать в tests/data
    python tools/grammar_unit_snapshots.py 13 --write --rework   # доработка старого юнита

Считает те же хеши, что сверяют tests/test_grammar_redesign.py (вопросы и ответы)
и tests/test_grammar_theory_dedup.py (теория, проверки, упражнения, маршрут), и
собирает tests/data/grammar_before_unitNN.json — хеши файлов всех предыдущих юнитов.
С --rework снимок предыдущих юнитов не пересоздаётся; вместо этого хеш файла
доработанного юнита обновляется во всех снимках grammar_before_*.json
(более поздних юнитов и grammar_before_possessives.json).
Порядок работы — docs/grammar/GRAMMAR_UNIT_GUIDE.md, разделы 19 и 21.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from espanol.grammar import GRAMMAR, load_grammar  # noqa: E402

DATA = ROOT / "tests" / "data"


def digest(data) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def snapshots(number: int) -> dict:
    unit = next((u for u in load_grammar() if u["number"] == number), None)
    if unit is None:
        raise SystemExit(f"В content/grammar нет юнита {number}.")
    groups = [*[s["check"] for s in unit["sections"]], *unit["exercises"]]
    questions = digest({"id": unit["id"], "groups": [
        {"id": g["id"], "questions": [[q["prompt"], q["answers"], q.get("sourceRef")] for q in g["questions"]]}
        for g in groups]})
    raw = json.loads(next(GRAMMAR.glob(f"{number:03d}_*.json")).read_text(encoding="utf-8"))
    theory = digest({
        "titles": [s["title"] for s in raw["sections"]],
        "notes": [s.get("notes", []) for s in raw["sections"]],
        "checks": [s.get("check") for s in raw["sections"]],
        "exercises": raw["exercises"],
        "learningOrder": raw["learningOrder"],
        "summary": raw["summary"],
    })
    before = {p.name: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
              for p in sorted(GRAMMAR.glob("[0-9]*.json")) if int(p.name[:3]) < number}
    return {"questions": questions, "theory": theory, "before": before}


def update(path: Path, number: int, value: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data[str(number)] = value
    ordered = {key: data[key] for key in sorted(data, key=int)}
    path.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("unit", type=int, help="номер юнита")
    parser.add_argument("--write", action="store_true", help="записать значения в tests/data")
    parser.add_argument("--rework", action="store_true",
                        help="доработка опубликованного юнита: обновить его хеш в снимках более поздних юнитов")
    args = parser.parse_args()
    result = snapshots(args.unit)
    print(f"grammar_question_signatures.json  [{args.unit}] = {result['questions']}")
    print(f"grammar_theory_preservation.json  [{args.unit}] = {result['theory']}")
    if not args.rework:
        print(f"grammar_before_unit{args.unit}.json: файлов предыдущих юнитов — {len(result['before'])}")
    if not args.write:
        return 0
    update(DATA / "grammar_question_signatures.json", args.unit, result["questions"])
    update(DATA / "grammar_theory_preservation.json", args.unit, result["theory"])
    if args.rework:
        source = next(GRAMMAR.glob(f"{args.unit:03d}_*.json"))
        current = hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        changed = 0
        for path in sorted(DATA.glob("grammar_before_*.json")):
            later = json.loads(path.read_text(encoding="utf-8"))
            if later.get(source.name) not in (None, current):
                later[source.name] = current
                path.write_text(json.dumps(later, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                changed += 1
        print(f"Хеш {source.name} обновлён в снимках более поздних юнитов: {changed}.")
    else:
        (DATA / f"grammar_before_unit{args.unit}.json").write_text(
            json.dumps(result["before"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Записано в tests/data. Проверь git diff: измениться должны только строки этого юнита.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
