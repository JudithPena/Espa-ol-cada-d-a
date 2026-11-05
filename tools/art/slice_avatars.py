"""Нарезка листа аватаров из нейросети на файлы content/art/avatars/<slug>.webp.

    python tools/art/slice_avatars.py лист.png 4x3 lucia pablo ana ...

Лист — сетка одинаковых квадратных ячеек (столбцы x строки), персонажи слева направо, сверху вниз.
Из каждой ячейки берётся квадрат вокруг лица (ZOOM от стороны ячейки, центр чуть выше середины —
голова в кружке 34 px крупнее, плечи обрезаются), уменьшается до 128×128 (аватар на сайте 34 px, хватает и для экранов ×3) и сохраняется в WebP.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "content" / "art" / "avatars"
SIZE = 128
ZOOM = 0.78   # сторона квадрата — доля стороны ячейки
CY = 0.45     # центр квадрата по высоте ячейки (лицо в портретах выше середины)


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
        side = min(cw, ch) * ZOOM
        cx, cy = (c + 0.5) * cw, (r + CY) * ch
        box = (round(cx - side / 2), round(cy - side / 2), round(cx + side / 2), round(cy + side / 2))
        img.crop(box).resize((SIZE, SIZE), Image.LANCZOS).save(OUT / f"{slug}.webp", "WEBP", quality=82, method=6)
        print(f"{slug}.webp")


if __name__ == "__main__":
    main(sys.argv[1:])
