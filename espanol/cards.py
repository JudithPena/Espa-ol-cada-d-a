"""Картинки для постов-статей в стиле аватарки канала: синий фон, солнце, белая карточка.

Обложка урока и карточки новых слов рисуются при отправке (Pillow).
Эмодзи берутся из системного шрифта Noto Color Emoji; если его нет, карточки
рисуются без эмодзи. Если нет Pillow, статья уходит без картинок.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

FONTS = Path(__file__).parent / "assets" / "fonts"
SPANISH_FONT = FONTS / "Baloo2-ExtraBold.ttf"   # испанские слова, как «¡Hola!» на аватарке
TEXT_FONT = FONTS / "Rubik-ExtraBold.ttf"       # русский текст
# Свои картинки для слов, у которых нет подходящего эмодзи (например, стола):
# assets/emoji/la_mesa.png — рисуется на карточке вместо эмодзи.
PICTURES = Path(__file__).parent / "assets" / "emoji"
# Запасной шрифт для знаков, которых нет в Rubik (например, θ в произношении)
FALLBACK_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]
EMOJI_FONTS = [
    os.environ.get("EMOJI_FONT", ""),
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
]

BLUE_TOP, BLUE_BOTTOM = (47, 123, 229), (23, 58, 140)
NAVY, RED, SUN, MUTED = (14, 42, 107), (230, 57, 70), (255, 200, 61), (92, 108, 140)


def available() -> bool:
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False
    return True


def _font(path: Path, size: int):
    from PIL import ImageFont

    return ImageFont.truetype(str(path), size)


def _background(w: int, h: int):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):  # диагональный градиент, как на аватарке
        t = y / max(1, h - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(BLUE_TOP, BLUE_BOTTOM))
        draw.line([(0, y), (w, y)], fill=color)
    r = round(min(w, h) * 0.2)
    draw.ellipse([w - r * 1.6, -r * 0.6, w + r * 0.4, r * 1.4], fill=SUN)
    return img, draw


def _bubble(draw, box: tuple[int, int, int, int], radius: int, tail: bool = True) -> None:
    x0, y0, x1, y1 = box
    shadow = (x0 + 6, y0 + 14, x1 + 6, y1 + 14)
    draw.rounded_rectangle(shadow, radius, fill=(18, 46, 112))
    draw.rounded_rectangle(box, radius, fill="white")
    if tail:  # хвостик реплики, как у облачка на аватарке
        tx = x0 + (x1 - x0) * 0.18
        draw.polygon([(tx, y1 - 10), (tx - 40, y1 + 90), (tx + 90, y1 - 10)], fill="white")


def _covers(path: Path, text: str) -> bool:
    font = _font(path, 40)
    missing = font.getmask("\U000F0000").getbbox()  # так выглядит «нет такого знака»
    return all(ch.isspace() or font.getmask(ch).getbbox() != missing for ch in set(text))


def _fit(text: str, path: Path, max_width: int, size: int, min_size: int = 28):
    if not _covers(path, text):
        path = next((Path(p) for p in FALLBACK_FONTS if os.path.exists(p)), path)
    font = _font(path, size)
    while size > min_size and font.getlength(text) > max_width:
        size -= 4
        font = _font(path, size)
    return font


def _emoji(img, emoji: str, center: tuple[int, int], size: int) -> bool:
    """Рисует цветной эмодзи (шрифт Noto растровый, только 109 px — масштабируем)."""
    from PIL import Image, ImageDraw, ImageFont

    path = next((p for p in EMOJI_FONTS if p and os.path.exists(p)), None)
    if not path or not emoji:
        return False
    try:
        font = ImageFont.truetype(path, 109)
    except OSError:
        return False
    layer = Image.new("RGBA", (420, 200), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((10, 30), emoji, font=font, embedded_color=True)
    box = layer.getbbox()
    if not box:
        return False
    layer = layer.crop(box)
    scale = size / max(layer.height, 1)
    layer = layer.resize((max(1, round(layer.width * scale)), size), Image.LANCZOS)
    img.paste(layer, (center[0] - layer.width // 2, center[1] - layer.height // 2), layer)
    return True


def picture(es: str) -> Path | None:
    path = PICTURES / (es.lower().replace(" ", "_") + ".png")
    return path if path.exists() else None


def _paste_picture(img, path: Path, center: tuple[int, int], size: int) -> None:
    from PIL import Image

    pic = Image.open(path).convert("RGBA")
    scale = size / max(pic.width, pic.height)
    pic = pic.resize((max(1, round(pic.width * scale)), max(1, round(pic.height * scale))), Image.LANCZOS)
    img.paste(pic, (center[0] - pic.width // 2, center[1] - pic.height // 2), pic)


def _png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def cover(kicker: str, title: str, subtitle: str, emoji: str = "") -> bytes:
    """Обложка урока 1280×720: «Урок 8 · A0», крупное название и тема."""
    from PIL import ImageDraw

    w, h = 1280, 720
    img, draw = _background(w, h)
    box = (110, 150, 1050, 560)
    _bubble(draw, box, 70)
    draw = ImageDraw.Draw(img)
    inner = box[2] - box[0] - 140
    draw.text((box[0] + 70, box[1] + 60), kicker.upper(), font=_font(TEXT_FONT, 34), fill=RED)
    font = _fit(title, TEXT_FONT, inner - (150 if emoji else 0), 92)
    draw.text((box[0] + 70, box[1] + 120), title, font=font, fill=NAVY)
    sub = _fit(subtitle, TEXT_FONT, inner, 40, 24)
    draw.text((box[0] + 70, box[3] - 110), subtitle, font=sub, fill=MUTED)
    if emoji:
        _emoji(img, emoji, (box[2] - 120, box[1] + 175), 130)
    return _png(img)


def word_card(es: str, ru: str, emoji: str = "", pron: str = "") -> bytes:
    """Карточка слова 1080×1080: эмодзи, испанское слово, произношение и перевод."""
    from PIL import ImageDraw

    w = h = 1080
    img, draw = _background(w, h)
    box = (110, 150, 970, 930)
    _bubble(draw, box, 90, tail=False)
    draw = ImageDraw.Draw(img)
    inner = box[2] - box[0] - 120
    # Длинное «hace buen tiempo / hace mal tiempo» крупнее читается в две строки.
    variants = [[es]] + ([es.split(" / ")] if " / " in es else [])
    fitted = [[(part, _fit(part, SPANISH_FONT, inner, 150, 48)) for part in v] for v in variants]
    best = max(fitted, key=lambda v: min(font.size for _, font in v) - 30 * (len(v) - 1))
    lines = [(part, font, RED, 55 if n == len(best) - 1 else 20) for n, (part, font) in enumerate(best)]
    if pron:
        lines.append((f"[{pron}]", _fit(f"[{pron}]", TEXT_FONT, inner, 44, 24), MUTED, 50))
    lines.append((ru, _fit(ru, TEXT_FONT, inner, 60, 26), NAVY, 0))
    heights = [draw.textbbox((0, 0), text, font=font, anchor="ls")[1] for text, font, _, _ in lines]
    own = picture(es)
    emoji_size = 230 if emoji or own else 0
    total = emoji_size + (60 if emoji_size else 0) + sum(-hh + gap for hh, (_, _, _, gap) in zip(heights, lines))
    y = (box[1] + box[3]) // 2 - total // 2
    if own:
        _paste_picture(img, own, (w // 2, y + emoji_size // 2), round(emoji_size * 1.15))
        y += emoji_size + 60
    elif emoji_size:
        if _emoji(img, emoji, (w // 2, y + emoji_size // 2), emoji_size):
            y += emoji_size + 60
        else:
            y += (emoji_size + 60) // 2
    for hh, (text, font, color, gap) in zip(heights, lines):
        y += -hh
        draw.text((w // 2, y), text, font=font, fill=color, anchor="ms")
        y += gap
    return _png(img)
