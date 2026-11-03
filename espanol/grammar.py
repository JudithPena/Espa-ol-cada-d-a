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
        if "learningOrder" in unit:
            routes = {f"section:{i}" for i in range(len(unit['sections']))} | {'summary'} | {f"exercise:{g['id']}" for g in unit['exercises']}
            if set(unit['learningOrder']) != routes or len(unit['learningOrder']) != len(routes):
                raise ValueError(f"{path}: learningOrder must contain every stage exactly once")
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
