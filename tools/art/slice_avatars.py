"""Нарезка листа аватаров из нейросети на файлы content/art/avatars/<slug>.webp.

    python tools/art/slice_avatars.py лист.png 4x3 lucia pablo ana ...

Лист — сетка одинаковых квадратных ячеек (столбцы x строки), персонажи слева направо, сверху вниз.
Каждая ячейка обрезается до квадрата по центру (с небольшим полем, чтобы не задеть соседей),
уменьшается до 128×128 (аватар на сайте 34 px, хватает и для экранов ×3) и сохраняется в WebP.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "content" / "art" / "avatars"
SIZE = 128
INSET = 0.04   # доля ячейки, срезаемая с каждого края


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        sys.exit(__doc__)
    sheet, grid, slugs = Path(argv[0]), argv[1], argv[2:]
    cols, rows = (int(x) for x in grid.lower().split("x"))
    if len(slugs) > cols * rows:
        sys.exit(f"персонажей {len(slugs)}, а ячеек {cols * rows}")
    img = Image.open(sheet).convert("RGB")
    cw, ch = img.width / cols, img.height / rows
    OUT.mkdir(parents=True, exist_ok=True)
    for k, slug in enumerate(slugs):
        r, c = divmod(k, cols)
        side = min(cw, ch) * (1 - 2 * INSET)
        cx, cy = (c + 0.5) * cw, (r + 0.5) * ch
        box = (round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2))
        img.crop(box).resize((SIZE, SIZE), Image.LANCZOS).save(OUT / f"{slug}.webp", "WEBP", quality=82, method=6)
        print(f"{slug}.webp")


if __name__ == "__main__":
    main(sys.argv[1:])
