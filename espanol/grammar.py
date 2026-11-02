"""Independent grammar units for the website; not part of the channel course."""

import json
import base64
from pathlib import Path


GRAMMAR = Path(__file__).resolve().parent.parent / "content" / "grammar"


def _image_uri(directory: Path, relative: str) -> str:
    image = (directory / relative).resolve()
    if not image.is_relative_to(directory.resolve()) or image.suffix != ".webp":
        raise ValueError("invalid grammar image path")
    return "data:image/webp;base64," + base64.b64encode(image.read_bytes()).decode()


def load_grammar(directory: Path = GRAMMAR) -> list[dict]:
    units = []
    for path in sorted(directory.glob("*.json")):
        unit = json.loads(path.read_text(encoding="utf-8"))
        if any(u["id"] == unit["id"] for u in units):
            raise ValueError(f"{path}: duplicate grammar unit id")
        ids = set()
        for group in [s["check"] for s in unit["sections"] if s.get("check")] + unit["exercises"]:
            if group["id"] in ids:
                raise ValueError(f"{path}: duplicate exercise id")
            ids.add(group["id"])
            for q in group["questions"]:
                if not q.get("explain") or not q.get("answers"):
                    raise ValueError(f"{path}: answer and explanation required")
                if q.get("options") and not set(q["answers"]) <= set(q["options"]):
                    raise ValueError(f"{path}: correct answer missing from options")
                if q.get("image"):
                    q["image"] = _image_uri(directory, q["image"])
            family = group.get("family")
            if family and family.get("portraits"):
                family["portraits"] = {name: _image_uri(directory, image) for name, image in family["portraits"].items()}
        units.append(unit)
    return units
