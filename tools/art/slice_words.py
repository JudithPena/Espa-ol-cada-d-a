"""Нарезка листа картинок слов из нейросети на файлы content/art/<slug>.webp (360×360).

    python tools/art/slice_words.py лист.png 3x3 tu usted yo ...

Лист — сетка одинаковых квадратных ячеек, картинки слева направо, сверху вниз. От ячейки срезается
узкое поле (белые промежутки сетки), остальное уменьшается до 360×360. Слова и файлы связывает
ART_SLUGS в espanol/site.py — допишите туда новые слова.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "content" / "art"
SIZE = 360
INSET = 0.015   # доля ячейки, срезаемая с каждого края (белые промежутки между ячейками)


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        sys.exit(__doc__)
    sheet, grid, slugs = Path(argv[0]), argv[1], argv[2:]
    cols, rows = (int(x) for x in grid.lower().split("x"))
    img = Image.open(sheet).convert("RGB")
    cw, ch = img.width / cols, img.height / rows
    for k, slug in enumerate(slugs):
        r, c = divmod(k, cols)
        box = (round((c + INSET) * cw), round((r + INSET) * ch), round((c + 1 - INSET) * cw), round((r + 1 - INSET) * ch))
        img.crop(box).resize((SIZE, SIZE), Image.LANCZOS).save(OUT / f"{slug}.webp", "WEBP", quality=82, method=6)
        print(f"{slug}.webp")


if __name__ == "__main__":
    main(sys.argv[1:])
