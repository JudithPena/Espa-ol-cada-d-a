"""Independent grammar units for the website; not part of the channel course."""

import json
import base64
import hashlib
from collections import Counter
from itertools import product
from pathlib import Path


GRAMMAR = Path(__file__).resolve().parent.parent / "content" / "grammar"


def _image_uri(directory: Path, relative: str) -> str:
    image = (directory / relative).resolve()
    if not image.is_relative_to(directory.resolve()) or image.suffix != ".webp":
        raise ValueError("invalid grammar image path")
    return "data:image/webp;base64," + base64.b64encode(image.read_bytes()).decode()


def write_theory_illustrations(units: list[dict], output: Path) -> None:
    """Keep theory art out of the initial HTML; only the opened scene is downloaded."""
    for unit in units:
        for section in unit["sections"]:
            art = section.get("illustration")
            if not art:
                continue
            data = base64.b64decode(art["image"].split(",", 1)[1], validate=True)
            relative = f"g/{hashlib.sha256(data).hexdigest()[:20]}.webp"
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            art["image"] = relative


def load_grammar(directory: Path = GRAMMAR, *, schema_check: bool | None = None) -> list[dict]:
    """Load grammar. Official course is always schema checked before publication.

    Minimal temporary fixtures retain the historical validation contract unless
    callers explicitly request schema_check=True (used by schema regression tests).
    """
    from .grammar_quality import schema_validator, structure_unit, breaking_findings

    directory = Path(directory)
    if schema_check is None:
        schema_check = directory.resolve() == GRAMMAR.resolve()
    validator = schema_validator() if schema_check else None
    units = []
    for path in sorted(directory.glob("[0-9]*.json")):
        unit = json.loads(path.read_text(encoding="utf-8"))
        # Validate raw JSON before dereferencing nested fields or embedding art.
        if validator is not None:
            issues = breaking_findings(structure_unit(unit, path.name, validator))
            if issues:
                problem = issues[0]
                raise ValueError(f"{path}: {problem.rule}: {problem.message}")
        if 'revision' in unit and (type(unit['revision']) is not int or unit['revision'] < 1):
            raise ValueError(f"{path}: revision must be a positive integer")
        if any(u["id"] == unit["id"] for u in units):
            raise ValueError(f"{path}: duplicate grammar unit id")
        if "learningOrder" in unit:
            routes = {f"section:{i}" for i in range(len(unit['sections']))} | {'summary'} | {f"exercise:{g['id']}" for g in unit['exercises']}
            if set(unit['learningOrder']) != routes or len(unit['learningOrder']) != len(routes):
                raise ValueError(f"{path}: learningOrder must contain every stage exactly once")
        for section in unit["sections"]:
            dialogues = section.get('dialogues', [])
            if not isinstance(dialogues, list):
                raise ValueError(f"{path}: dialogues must be a list")
            for dialogue in dialogues:
                if (not isinstance(dialogue, dict) or not isinstance(dialogue.get('title'), str) or not dialogue['title'].strip()
                        or not isinstance(dialogue.get('lines'), list) or len(dialogue['lines']) < 2
                        or any(not isinstance(pair, list) or len(pair) != 2
                               or not all(isinstance(t, str) and t.strip() for t in pair)
                               for pair in dialogue['lines'])):
                    raise ValueError(f"{path}: dialogue requires title and bilingual turns")
            art = section.get("illustration")
            if art is not None:
                if isinstance(art, dict) and 'captionDialogue' in art and type(art['captionDialogue']) is not bool:
                    raise ValueError(f"{path}: captionDialogue must be boolean")
                if isinstance(art, dict) and 'captionExamples' in art and type(art['captionExamples']) is not bool:
                    raise ValueError(f"{path}: captionExamples must be boolean")
                if not isinstance(art, dict) or not art.get("image") or not art.get("alt") or not art.get("examples") or any(
                    not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(text, str) and text.strip() for text in pair)
                    for pair in art.get("examples", [])
                ):
                    raise ValueError(f"{path}: theory illustration requires image, alt and bilingual examples")
                if art.get('captionDialogue') and len(art['examples']) < 2:
                    raise ValueError(f"{path}: dialogue requires at least two bilingual turns")
                art["image"] = _image_uri(directory, art["image"])
        ids = set()
        for group in [s["check"] for s in unit["sections"] if s.get("check")] + unit["exercises"]:
            if 'revision' in group and (type(group['revision']) is not int or group['revision'] < 1):
                raise ValueError(f"{path}: revision must be a positive integer")
            if group["id"] in ids:
                raise ValueError(f"{path}: duplicate exercise id")
            ids.add(group["id"])
            if 'theorySections' in group:
                sections = group['theorySections']
                if (not isinstance(sections, list) or not sections
                        or any(type(i) is not int or not 0 <= i < len(unit['sections']) for i in sections)
                        or len(set(sections)) != len(sections)):
                    raise ValueError(f"{path}: theorySections must identify distinct existing theory sections")
            for format in [group.get('inputFormat')] + [q.get('inputFormat') for q in group['questions']]:
                if format is not None and (not isinstance(format, dict) or any(
                    not isinstance(format.get(key), str) or not format[key].strip()
                    for key in ('instruction', 'placeholder')
                ) or 'example' in format and (not isinstance(format['example'], str) or not format['example'].strip())):
                    raise ValueError(f"{path}: input format requires instruction, placeholder and a nonempty example when supplied")
            for key in ('allowNoArticle', 'articleContractions', 'deferAnswerFeedback', 'limitedAttempt'):
                if key in group and type(group[key]) is not bool:
                    raise ValueError(f"{path}: {key} must be boolean")
            for item in [group] + group['questions']:
                if 'accentSensitive' in item and type(item['accentSensitive']) is not bool:
                    raise ValueError(f"{path}: accentSensitive must be boolean")
                if 'shuffleOptions' in item:
                    if type(item['shuffleOptions']) is not bool:
                        raise ValueError(f"{path}: shuffleOptions must be boolean")
                    if item['shuffleOptions'] is False and (not isinstance(item.get('optionOrderReason'), str) or not item['optionOrderReason'].strip()):
                        raise ValueError(f"{path}: fixed option order requires optionOrderReason")
            for q in group["questions"]:
                if group.get('deferAnswerFeedback') and (not isinstance(q.get('retryHint'), str) or not q['retryHint'].strip()):
                    raise ValueError(f"{path}: deferred answer feedback requires a retry hint")
                if 'feedbackAnswers' in q and (not isinstance(q['feedbackAnswers'], list) or not q['feedbackAnswers']
                        or any(a not in q.get('answers', []) for a in q['feedbackAnswers'])
                        or len(set(q['feedbackAnswers'])) != len(q['feedbackAnswers'])):
                    raise ValueError(f"{path}: feedbackAnswers must list distinct accepted answers")
                if 'inputChars' in q and (not isinstance(q['inputChars'], list) or not q['inputChars']
                        or len(set(q['inputChars'])) != len(q['inputChars'])
                        or any(c not in ['á', 'é', 'í', 'ó', 'ú', 'ü', 'ñ'] for c in q['inputChars'])):
                    raise ValueError(f"{path}: inputChars must contain distinct Spanish characters")
                if 'gapWordCounts' in q and (not q.get('gapParts')
                        or len(q['gapWordCounts']) != len(q['gapParts']) - 1
                        or any(type(n) is not int or n < 1 for n in q['gapWordCounts'])
                        or sum(q['gapWordCounts']) != len(q['answers'][0].split())):
                    raise ValueError(f"{path}: gapWordCounts must describe the words in each gap")
                if q.get('interaction') == 'article-input':
                    article_answers = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'al', 'del', 'lo', 'uno', 'без артикля'}
                    if (q.get('options') or q.get('tiles') or q.get('guidedGaps') or q.get('gapParts')
                            or not q.get('answers') or any(a.lower() not in article_answers for a in q['answers'])
                            or 'Без артикля' in q['answers'] and not group.get('allowNoArticle')):
                        raise ValueError(f"{path}: article-input requires short article answers and an explicit omission control")
                if not q.get("explain") or not q.get("answers"):
                    raise ValueError(f"{path}: answer and explanation required")
                if q.get("options") and not set(q["answers"]) <= set(q["options"]):
                    raise ValueError(f"{path}: correct answer missing from options")
                if 'answerWarnings' in q:
                    warnings = q['answerWarnings']
                    if (not isinstance(warnings, dict) or not warnings
                            or not set(warnings) <= set(q['answers'])
                            or any(not isinstance(warning, dict)
                                   or warning.get('preferred') not in q['answers']
                                   or warning.get('preferred') in warnings
                                   or any(not isinstance(warning.get(key), str) or not warning[key].strip()
                                          for key in ('message', 'explanation', 'source'))
                                   or not warning['source'].startswith('https://')
                                   for warning in warnings.values())):
                        raise ValueError(f"{path}: answer warnings require an accepted variant, a preferred green answer, feedback and source")
                if "optionLabels" in q:
                    labels = q["optionLabels"]
                    if (not isinstance(labels, dict) or not q.get("options")
                            or not set(labels) <= set(q["options"])
                            or not all(isinstance(label, str) and label.strip() for label in labels.values())
                            or len({labels.get(value, value) for value in q["options"]}) != len(q["options"])):
                        raise ValueError(f"{path}: option labels must identify distinct existing options")
                if "guidedGaps" in q:
                    frame = q["guidedGaps"]
                    parts, choices = frame.get("parts", []), frame.get("choices", [])
                    if (not 1 <= len(choices) <= 6 or len(parts) != len(choices)+1
                            or not all(isinstance(p, str) for p in parts)
                            or any(not isinstance(c, list) or not 2 <= len(c) <= 6
                                   or not all(isinstance(w, str) and w.strip() for w in c) for c in choices)
                            or not any(''.join(p+(values[i] if i<len(values) else '') for i,p in enumerate(parts)).strip()
                                       in q['answers'] for values in product(*choices))):
                        raise ValueError(f"{path}: guided gaps must allow a complete accepted answer")
                if "tiles" in q:
                    tiles = q["tiles"]
                    if (q.get("interaction") != "build" or q.get("options") or not isinstance(tiles, list)
                            or not all(isinstance(t, str) and t.strip() for t in tiles)
                            or Counter(q["answers"][0].split()) - Counter(tiles)):
                        raise ValueError(f"{path}: tiles must allow building the complete answer")
                if "clock" in q:
                    clock = q["clock"]
                    if not isinstance(clock, dict) or any(type(clock.get(k)) is not int or not 0 <= clock[k] <= limit for k, limit in [("hour", 23), ("minute", 59)]):
                        raise ValueError(f"{path}: clock requires a valid hour and minute")
                if "distance" in q and q["distance"] not in {"near", "listener", "far"}:
                    raise ValueError(f"{path}: invalid demonstrative distance")
                if q.get("image"):
                    q["image"] = _image_uri(directory, q["image"])
                if "pictureCount" in q and (type(q["pictureCount"]) is not int or not 1 <= q["pictureCount"] <= 12 or not q.get("image")):
                    raise ValueError(f"{path}: pictureCount requires an image and an integer from 1 to 12")
                if "ratings" in q:
                    ratings = q["ratings"]
                    if not ratings.get("label") or not ratings.get("people") or any(
                        not p.get("name") or type(p.get("level")) is not int or not 1 <= p["level"] <= 3
                        for p in ratings["people"]
                    ):
                        raise ValueError(f"{path}: ratings require named people with levels from 1 to 3")
            family = group.get("family")
            if family and family.get("portraits"):
                family["portraits"] = {name: _image_uri(directory, image) for name, image in family["portraits"].items()}
        units.append(unit)
    return units
