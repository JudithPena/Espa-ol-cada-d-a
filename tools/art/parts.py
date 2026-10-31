"""Детали для картинок к словам: персонажи, пузыри, небо. viewBox 320×200, плоский стиль."""
import math

W, H = 320, 200
INK = "#1f2747"
SKIN = {"a": "#f4c9a3", "b": "#e2a97e", "c": "#bf8660"}
HAIR = {"brown": "#4a3022", "dark": "#23202a", "red": "#b5532c", "blond": "#d9a441", "grey": "#c9ccd6"}
SHIRT = {"blue": "#2346c4", "red": "#e2513d", "yellow": "#f2a516", "green": "#2f9e6e", "purple": "#7a5cc7",
         "pink": "#e86f9c", "teal": "#1f8f9a", "navy": "#26305e"}
SKY = {"day": "#dbe7ff", "warm": "#ffe8c4", "mint": "#d8f2e4", "pink": "#ffe1e4", "lilac": "#e8e1ff",
       "night": "#1f2858", "dusk": "#ffcf9e", "cream": "#fff3dc", "grey": "#e4e8f1"}


def svg(slug, body, bg="day"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-hidden="true">'
            f'<rect width="{W}" height="{H}" rx="18" fill="{SKY.get(bg, bg)}"/>{body}</svg>')


def ground(color="#c9e3b4", y=168):
    return f'<path d="M0 {y} Q{W/2} {y-10} {W} {y} V{H-18} Q{W} {H} {W-18} {H} H18 Q0 {H} 0 {H-18} Z" fill="{color}"/>'


def floor(color="#e9dccb", y=170):
    return f'<path d="M0 {y} H{W} V{H-18} Q{W} {H} {W-18} {H} H18 Q0 {H} 0 {H-18} Z" fill="{color}"/>'


def sun(x, y, r=22, color="#ffc93c", rays=True):
    out = ""
    if rays:
        for k in range(10):
            a = k * math.pi / 5
            x1, y1 = x + math.cos(a) * (r + 6), y + math.sin(a) * (r + 6)
            x2, y2 = x + math.cos(a) * (r + 15), y + math.sin(a) * (r + 15)
            out += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
    return out + f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def moon(x, y, r=20, color="#ffe08a"):
    # Полумесяц одной фигурой: внешняя дуга и внутренняя.
    return (f'<path d="M{x} {y-r} A{r} {r} 0 1 0 {x} {y+r} A{r*0.78:.1f} {r*0.78:.1f} 0 1 1 {x} {y-r} Z" '
            f'fill="{color}" transform="rotate(-25 {x} {y})"/>')


def star(x, y, s=6, color="#ffe08a"):
    return (f'<path d="M{x} {y-s} Q{x+s*0.18} {y-s*0.18} {x+s} {y} Q{x+s*0.18} {y+s*0.18} {x} {y+s} '
            f'Q{x-s*0.18} {y+s*0.18} {x-s} {y} Q{x-s*0.18} {y-s*0.18} {x} {y-s} Z" fill="{color}"/>')


def cloud(x, y, s=1.0, color="#ffffff"):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="{color}"><ellipse cx="0" cy="0" rx="26" ry="14"/>'
            f'<circle cx="-12" cy="-8" r="13"/><circle cx="10" cy="-12" r="16"/></g>')


def heart(x, y, s=10, color="#e8506b"):
    return (f'<path d="M{x} {y+s*0.9} C{x-s*1.7} {y-s*0.1} {x-s*0.7} {y-s*1.3} {x} {y-s*0.35} '
            f'C{x+s*0.7} {y-s*1.3} {x+s*1.7} {y-s*0.1} {x} {y+s*0.9} Z" fill="{color}"/>')


def bubble(x, y, w, h, tail="left", content="", fill="#ffffff"):
    """Пузырь реплики; (x, y) — левый верхний угол; tail — куда смотрит хвостик (left/right)."""
    tx = x + 18 if tail == "left" else x + w - 18
    dx = -10 if tail == "left" else 10
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{min(h/2, 16)}" fill="{fill}" '
            f'stroke="{INK}" stroke-opacity=".12" stroke-width="2"/>'
            f'<path d="M{tx-7} {y+h-1} L{tx+dx} {y+h+12} L{tx+7} {y+h-1} Z" fill="{fill}"/>'
            f'{content}</g>')


def text(x, y, t, size=26, color=INK, weight=800):
    return (f'<text x="{x}" y="{y}" font-family="Manrope, Segoe UI, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="middle">{t}</text>')


def qmark(x, y, size=30, color="#2346c4"):
    return text(x, y, "?", size, color)


def check(x, y, s=1, color="#2f9e6e"):
    return (f'<g transform="translate({x} {y}) scale({s})"><circle r="20" fill="{color}"/>'
            f'<path d="M-9 0 L-2 8 L10 -7" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g>')


def cross(x, y, s=1, color="#e2513d"):
    return (f'<g transform="translate({x} {y}) scale({s})"><circle r="20" fill="{color}"/>'
            f'<path d="M-8 -8 L8 8 M8 -8 L-8 8" stroke="#fff" stroke-width="5" stroke-linecap="round"/></g>')


# ---------------------------------------------------------------- персонаж

def person(x, base=200, s=1.0, skin="a", hair="brown", style="short", shirt="blue", mouth="smile",
           eyes="open", arm_l="down", arm_r="down", extra="", flip=False, age="adult", brows=None):
    """Человечек по пояс, стоит на нижнем крае; x — середина, s — масштаб.

    style: short, long, bun, curly, bald, ponytail; mouth: smile, grin, flat, sad, o, wavy;
    eyes: open, happy, closed, wide; arm_*: down, wave, up, point, hand, thumb, chin, heart, ok.
    """
    sk, hc, sc = SKIN.get(skin, skin), HAIR.get(hair, hair), SHIRT.get(shirt, shirt)
    hx, hy = 0, -112
    parts = []
    # волосы сзади
    if style == "long":
        parts.append(f'<path d="M-30 -112 Q-34 -60 -24 -66 L24 -66 Q34 -60 30 -112 Z" fill="{hc}"/>')
    if style == "ponytail":
        parts.append(f'<ellipse cx="28" cy="-104" rx="10" ry="18" fill="{hc}" transform="rotate(25 28 -104)"/>')
    if style == "bun":
        parts.append(f'<circle cx="0" cy="-146" r="12" fill="{hc}"/>')
    # тело
    parts.append(f'<path d="M-40 0 Q-42 -62 0 -66 Q42 -62 40 0 Z" fill="{sc}"/>')
    parts.append(f'<path d="M-9 -66 L0 -54 L9 -66 Z" fill="{sk}"/>')
    parts.append(f'<rect x="-8" y="-82" width="16" height="18" rx="6" fill="{sk}"/>')

    # руки
    def arm(side, pose):
        sx = 34 * side
        if pose == "down":
            return ""
        targets = {
            "wave": (52 * side, -128), "up": (40 * side, -140), "point": (78 * side, -70),
            "hand": (56 * side, -78), "thumb": (54 * side, -84), "chin": (14 * side, -88),
            "heart": (11 * side, -40), "ok": (50 * side, -98), "tray": (66 * side, -60),
        }
        ex, ey = targets[pose]
        elbow = (sx + 14 * side, -34) if pose not in ("chin", "heart") else (sx + 6 * side, -30)
        out = (f'<path d="M{sx} -50 Q{elbow[0]} {elbow[1]} {ex} {ey}" fill="none" stroke="{sc}" '
               f'stroke-width="15" stroke-linecap="round"/>')
        out += f'<circle cx="{ex}" cy="{ey}" r="9" fill="{sk}"/>'
        if pose == "wave":
            for k in (0, 1):
                out += (f'<path d="M{ex + (16 + 7*k) * side} {ey - 14 - 4*k} q{6*side} {8} 0 {16}" fill="none" '
                        f'stroke="{INK}" stroke-opacity=".35" stroke-width="3" stroke-linecap="round"/>')
        if pose == "heart" and side > 0:   # ладони сложены у груди, над ними сердечко
            out += heart(0, -48, 13)
        if pose == "thumb":
            out += f'<rect x="{ex - 3}" y="{ey - 20}" width="7" height="14" rx="3.5" fill="{sk}"/>'
        if pose == "point":
            out += f'<rect x="{ex if side > 0 else ex - 16}" y="{ey - 3}" width="16" height="6" rx="3" fill="{sk}"/>'
        if pose == "ok":
            out += f'<circle cx="{ex}" cy="{ey - 11}" r="6" fill="none" stroke="{sk}" stroke-width="5"/>'
            out += f'<rect x="{ex + 4*side - 2}" y="{ey - 26}" width="5" height="14" rx="2.5" fill="{sk}"/>'
        return out

    parts.append(arm(-1, arm_l))
    parts.append(arm(1, arm_r))
    # голова
    parts.append(f'<circle cx="{hx}" cy="{hy}" r="28" fill="{sk}"/>')
    parts.append(f'<circle cx="-27" cy="-110" r="6" fill="{sk}"/><circle cx="27" cy="-110" r="6" fill="{sk}"/>')
    # волосы спереди
    if style in ("short", "long", "bun", "ponytail"):
        parts.append(f'<path d="M-29 -112 Q-30 -146 0 -144 Q30 -146 29 -112 Q22 -130 4 -128 Q-14 -134 -29 -112 Z" fill="{hc}"/>')
    elif style == "curly":
        for cx, cy in ((-22, -126), (-10, -138), (6, -140), (20, -130), (27, -116), (-28, -114)):
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="11" fill="{hc}"/>')
    elif style == "bald":
        parts.append(f'<path d="M-29 -106 Q-31 -122 -22 -126 L-22 -108 Z M29 -106 Q31 -122 22 -126 L22 -108 Z" fill="{hc}"/>')
    # глаза
    ey = -112
    if eyes == "happy":
        parts.append(f'<path d="M-15 {ey} q5 -6 10 0 M5 {ey} q5 -6 10 0" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
    elif eyes == "closed":
        parts.append(f'<path d="M-15 {ey-2} q5 5 10 0 M5 {ey-2} q5 5 10 0" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
    elif eyes == "wide":
        parts.append(f'<circle cx="-10" cy="{ey}" r="5" fill="#fff"/><circle cx="10" cy="{ey}" r="5" fill="#fff"/>'
                     f'<circle cx="-10" cy="{ey}" r="3" fill="{INK}"/><circle cx="10" cy="{ey}" r="3" fill="{INK}"/>')
    else:
        parts.append(f'<circle cx="-10" cy="{ey}" r="3.4" fill="{INK}"/><circle cx="10" cy="{ey}" r="3.4" fill="{INK}"/>')
    if brows == "worried":
        parts.append(f'<path d="M-16 -122 L-6 -125 M16 -122 L6 -125" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>')
    if brows == "up":
        parts.append(f'<path d="M-15 -124 q5 -4 10 0 M5 -124 q5 -4 10 0" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>')
    parts.append(f'<circle cx="-17" cy="-101" r="5" fill="#ff8b8b" opacity=".35"/><circle cx="17" cy="-101" r="5" fill="#ff8b8b" opacity=".35"/>')
    mouths = {
        "smile": f'<path d="M-9 -98 Q0 -89 9 -98" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
        "grin": f'<path d="M-11 -99 Q0 -84 11 -99 Z" fill="{INK}"/><path d="M-7 -92 Q0 -88 7 -92" fill="none" stroke="#ff7b7b" stroke-width="3" stroke-linecap="round"/>',
        "flat": f'<path d="M-8 -95 H8" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
        "sad": f'<path d="M-8 -92 Q0 -100 8 -92" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
        "o": f'<ellipse cx="0" cy="-95" rx="4.5" ry="5.5" fill="{INK}"/>',
        "wavy": f'<path d="M-9 -95 q3 -4 6 0 t6 0 t6 0" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
    }
    parts.append(mouths[mouth])
    if age == "old":
        parts.append(f'<path d="M-20 -104 q-3 4 0 8 M20 -104 q3 4 0 8" fill="none" stroke="{INK}" stroke-opacity=".3" stroke-width="2"/>')
    parts.append(extra)
    flipx = -1 if flip else 1
    return f'<g transform="translate({x} {base}) scale({s * flipx} {s})">{"".join(parts)}</g>'


# дополнительные детали к персонажу (в координатах персонажа)
def mustache(color="#c9ccd6"):
    return f'<path d="M-14 -101 Q-7 -107 0 -102 Q7 -107 14 -101 Q8 -97 0 -100 Q-8 -97 -14 -101 Z" fill="{color}"/>'


def top_hat(color="#26305e", band="#e2513d"):
    return (f'<rect x="-34" y="-142" width="68" height="8" rx="4" fill="{color}"/>'
            f'<rect x="-22" y="-176" width="44" height="38" rx="6" fill="{color}"/>'
            f'<rect x="-22" y="-148" width="44" height="7" fill="{band}"/>')


def glasses():
    return (f'<circle cx="-10" cy="-112" r="8" fill="none" stroke="{INK}" stroke-width="2.5"/>'
            f'<circle cx="10" cy="-112" r="8" fill="none" stroke="{INK}" stroke-width="2.5"/>'
            f'<path d="M-2 -112 H2" stroke="{INK}" stroke-width="2.5"/>')


def necklace(color="#ffffff"):
    return "".join(f'<circle cx="{x}" cy="{-60 + abs(x) * 0.25}" r="3.4" fill="{color}"/>' for x in range(-16, 17, 8))


def tie(color="#e2513d"):
    return f'<path d="M0 -60 L-6 -52 L0 -24 L6 -52 Z" fill="{color}"/><path d="M-12 -66 L0 -58 L12 -66 L12 -60 L0 -52 L-12 -60 Z" fill="#fff"/>'


def collar_shirt():
    return f'<path d="M-12 -66 L0 -54 L12 -66 L8 -50 L0 -54 L-8 -50 Z" fill="#fff"/>'
