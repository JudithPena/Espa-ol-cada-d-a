"""Картинки к словам курса для сайта: тема 0–1. Каждая сцена — функция с @scene("slug").

    python tools/art/scenes.py content/art     # пишет content/art/<slug>.svg

slug — написание слова без ударений и знаков: «¡Hola!» → hola, «¿Y tú?» → y_tu (espanol/site.py: art_slug).
Детали (персонажи, пузыри, солнце, луна) — tools/art/parts.py.
"""
import sys
from pathlib import Path

from parts import *  # noqa: F401,F403

S = {}


def scene(slug, bg="day"):
    def deco(fn):
        S[slug] = svg(slug, fn(), bg)
        return fn
    return deco


# ================================================================ тема 0

@scene("hola", "day")
def _():
    return (cloud(60, 40, .9) + cloud(250, 52, .7) + ground() +
            person(160, 200, 1.05, skin="b", hair="dark", style="short", shirt="pink", mouth="grin",
                   eyes="happy", arm_r="wave") +
            bubble(196, 26, 92, 46, "left", text(242, 58, "¡Hola!", 22)))


@scene("la_casa", "day")
def _():
    return (sun(270, 42, 18) + cloud(70, 44, .8) + ground() +
            '<rect x="96" y="92" width="128" height="80" rx="4" fill="#fff6e6"/>'
            '<path d="M84 96 L160 40 L236 96 Z" fill="#e2513d"/>'
            '<rect x="146" y="124" width="28" height="48" rx="4" fill="#8a5a3b"/><circle cx="168" cy="150" r="2.5" fill="#f2c94c"/>'
            '<rect x="108" y="110" width="26" height="24" rx="3" fill="#7fb2ff"/><rect x="186" y="110" width="26" height="24" rx="3" fill="#7fb2ff"/>'
            '<path d="M121 110 V134 M108 122 H134 M199 110 V134 M186 122 H212" stroke="#fff" stroke-width="2.5"/>'
            '<rect x="196" y="52" width="14" height="28" fill="#b9472f"/>'
            '<circle cx="46" cy="132" r="22" fill="#2f9e6e"/><rect x="43" y="146" width="6" height="26" fill="#8a5a3b"/>')


@scene("el_cafe", "warm")
def _():
    steam = "".join(f'<path d="M{x} 70 q-8 -12 0 -24 t0 -24" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".9"/>'
                    for x in (140, 160, 180))
    return (floor("#e8c9a0", 160) + steam +
            '<ellipse cx="160" cy="158" rx="78" ry="14" fill="#fff"/><ellipse cx="160" cy="156" rx="60" ry="9" fill="#efe6da"/>'
            '<path d="M112 84 H208 L200 146 Q198 156 186 156 H134 Q122 156 120 146 Z" fill="#fff"/>'
            '<ellipse cx="160" cy="84" rx="48" ry="9" fill="#6b3f26"/>'
            '<path d="M206 98 Q236 100 230 120 Q226 134 202 132" fill="none" stroke="#fff" stroke-width="10"/>'
            '<path d="M124 112 H196" stroke="#2346c4" stroke-width="6"/>')


@scene("el_taxi", "day")
def _():
    return (cloud(70, 40) + '<rect x="0" y="150" width="320" height="50" fill="#9aa3b5"/>' +
            "".join(f'<rect x="{x}" y="172" width="26" height="5" rx="2" fill="#fff"/>' for x in (20, 80, 140, 200, 260)) +
            '<path d="M56 140 Q58 112 84 110 L112 82 Q118 76 128 76 H198 Q208 76 214 82 L240 110 Q266 112 266 140 V152 H56 Z" fill="#ffc93c"/>'
            '<path d="M122 86 H158 V110 H100 Z M166 86 H204 L226 110 H166 Z" fill="#bfe0ff"/>'
            '<rect x="140" y="60" width="44" height="16" rx="4" fill="#26305e"/>'
            + text(162, 73, "TAXI", 12, "#ffc93c") +
            '<path d="M60 128 H262" stroke="#26305e" stroke-width="5" stroke-dasharray="8 8"/>'
            '<circle cx="104" cy="154" r="18" fill="#26305e"/><circle cx="104" cy="154" r="8" fill="#c9ccd6"/>'
            '<circle cx="222" cy="154" r="18" fill="#26305e"/><circle cx="222" cy="154" r="8" fill="#c9ccd6"/>'
            '<rect x="252" y="118" width="12" height="8" rx="3" fill="#fff6c2"/>')


@scene("el_hotel", "day")
def _():
    win = "".join(f'<rect x="{x}" y="{y}" width="18" height="16" rx="2" fill="{c}"/>'
                  for i, y in enumerate((58, 84, 110)) for j, x in enumerate((112, 140, 168, 196))
                  for c in [("#ffe08a" if (i + j) % 3 == 0 else "#bfe0ff")])
    return (cloud(60, 50, .8) + cloud(270, 36, .6) + ground("#c9e3b4", 170) +
            '<rect x="98" y="30" width="128" height="142" rx="6" fill="#7a5cc7"/>' + win +
            '<rect x="118" y="6" width="88" height="22" rx="6" fill="#e2513d"/>' +
            text(162, 23, "HOTEL", 15, "#fff") +
            star(130, 44, 5, "#ffe08a") + star(147, 44, 5, "#ffe08a") + star(164, 44, 5, "#ffe08a") +
            '<path d="M140 172 V144 Q140 136 148 136 H176 Q184 136 184 144 V172 Z" fill="#26305e"/>'
            '<path d="M128 136 H196" stroke="#f2a516" stroke-width="6" stroke-linecap="round"/>'
            '<circle cx="60" cy="150" r="18" fill="#2f9e6e"/><circle cx="262" cy="152" r="16" fill="#2f9e6e"/>')


@scene("la_musica", "lilac")
def _():
    note = lambda x, y, c, s=1: (f'<g transform="translate({x} {y}) scale({s})" fill="{c}"><ellipse cx="0" cy="0" rx="11" ry="8" transform="rotate(-20)"/>'
                                 f'<rect x="8" y="-46" width="4" height="46"/><path d="M8 -46 q18 6 14 22 q-2 -10 -14 -12 Z"/></g>')
    return ('<path d="M20 70 H300 M20 86 H300 M20 102 H300 M20 118 H300 M20 134 H300" stroke="#7a5cc7" stroke-opacity=".35" stroke-width="2"/>' +
            note(70, 118, "#2346c4") + note(120, 96, "#e2513d", 1.1) + note(176, 128, "#2f9e6e") + note(226, 88, "#f2a516", 1.2) +
            note(272, 112, "#e86f9c", .9) + star(40, 40, 7, "#f2a516") + star(290, 160, 6, "#7a5cc7"))


@scene("si", "mint")
def _():
    return (person(130, 200, 1.05, skin="a", hair="red", style="long", shirt="green", mouth="grin",
                   eyes="happy", arm_r="thumb") +
            '<path d="M118 52 q12 -10 24 0" fill="none" stroke="#2f9e6e" stroke-width="4" stroke-linecap="round"/>' +
            '<path d="M118 40 q12 -10 24 0" fill="none" stroke="#2f9e6e" stroke-opacity=".5" stroke-width="4" stroke-linecap="round"/>' +
            check(246, 76, 1.5))


@scene("no", "pink")
def _():
    return (person(130, 200, 1.05, skin="c", hair="dark", style="curly", shirt="purple", mouth="flat",
                   brows="worried", arm_r="ok".replace("ok", "up")) +
            '<path d="M84 74 q-10 14 0 28 M176 74 q10 14 0 28" fill="none" stroke="#e2513d" stroke-width="4" stroke-linecap="round"/>' +
            cross(246, 76, 1.5))


@scene("el_jamon", "warm")
def _():
    return (floor("#c99a6b", 158) +
            '<path d="M60 150 L120 150 L250 70 L238 60 Z" fill="#6b3f26"/>'
            '<path d="M104 124 Q86 92 120 74 Q170 48 226 66 Q246 74 236 92 Q210 132 150 140 Q116 144 104 124 Z" fill="#b8402f"/>'
            '<path d="M120 80 Q170 58 220 70" fill="none" stroke="#f3d7b4" stroke-width="8" stroke-linecap="round"/>'
            '<path d="M226 66 L262 46 Q272 42 274 52 Q276 60 266 62 L238 74" fill="#f3d7b4"/>'
            '<rect x="70" y="150" width="180" height="10" rx="4" fill="#4a3022"/>'
            '<path d="M60 166 L30 186 M260 166 L290 186" stroke="#4a3022" stroke-width="8" stroke-linecap="round"/>'
            '<path d="M30 104 l20 -6 l-2 10 z" fill="#f3d7b4" opacity=".7"/>')


@scene("el_queso", "cream")
def _():
    return (floor("#d9b98e", 158) +
            '<ellipse cx="160" cy="160" rx="110" ry="14" fill="#a87b4f"/>'
            '<path d="M70 150 L250 150 L250 104 L70 128 Z" fill="#f2b63d"/>'
            '<path d="M70 128 L250 104 L170 70 Z" fill="#ffd66b"/>'
            '<ellipse cx="110" cy="138" rx="10" ry="7" fill="#d99a26"/><ellipse cx="160" cy="132" rx="7" ry="5" fill="#d99a26"/>'
            '<ellipse cx="214" cy="128" rx="12" ry="8" fill="#d99a26"/><ellipse cx="190" cy="96" rx="8" ry="4" fill="#e8b84a"/>'
            '<ellipse cx="150" cy="104" rx="6" ry="3" fill="#e8b84a"/>')


@scene("la_guitarra", "dusk")
def _():
    return (sun(56, 48, 18, "#ffe08a") +
            '<g transform="translate(24 26) scale(.86) rotate(-35 160 110)">'
            '<rect x="152" y="-6" width="16" height="96" rx="4" fill="#6b3f26"/>'
            '<rect x="146" y="-24" width="28" height="24" rx="6" fill="#4a3022"/>'
            '<path d="M160 86 C120 86 116 118 132 132 C112 148 122 196 160 196 C198 196 208 148 188 132 C204 118 200 86 160 86 Z" fill="#d9822b"/>'
            '<circle cx="160" cy="140" r="14" fill="#4a3022"/>'
            '<rect x="146" y="168" width="28" height="7" rx="3" fill="#4a3022"/>'
            '<path d="M155 -10 V172 M160 -10 V172 M165 -10 V172" stroke="#f3e5c9" stroke-width="1.2"/></g>')


@scene("la_paella", "warm")
def _():
    rice = "".join(f'<circle cx="{x}" cy="{y}" r="2.2" fill="#e8a91c"/>' for x, y in
                   [(120, 104), (140, 96), (180, 100), (200, 112), (150, 122), (176, 126), (130, 118), (206, 98), (112, 112), (192, 124)])
    shrimp = lambda x, y, r: (f'<path d="M{x} {y} q14 -16 26 0 q-6 10 -16 8" fill="none" stroke="#f26b4f" stroke-width="7" '
                              f'stroke-linecap="round" transform="rotate({r} {x} {y})"/>')
    return (floor("#c98f5e", 150) +
            '<path d="M42 110 H70 M250 110 H278" stroke="#26305e" stroke-width="10" stroke-linecap="round"/>'
            '<ellipse cx="160" cy="114" rx="100" ry="44" fill="#26305e"/><ellipse cx="160" cy="110" rx="90" ry="36" fill="#f5c443"/>' + rice +
            shrimp(118, 100, -10) + shrimp(178, 92, 20) + shrimp(150, 120, 5) +
            '<circle cx="206" cy="118" r="7" fill="#2f9e6e"/><circle cx="104" cy="122" r="6" fill="#2f9e6e"/><circle cx="140" cy="94" r="5" fill="#e2513d"/>'
            '<path d="M214 90 a16 16 0 0 1 22 18 z" fill="#ffe36b" stroke="#f2c94c" stroke-width="2"/>')


@scene("la_tortilla", "cream")
def _():
    return (floor("#d9b98e", 156) +
            '<ellipse cx="160" cy="140" rx="110" ry="30" fill="#ffffff"/><ellipse cx="160" cy="136" rx="92" ry="22" fill="#eef1f6"/>'
            '<path d="M80 128 Q80 92 160 92 Q240 92 240 128 Q240 148 160 148 Q80 148 80 128 Z" fill="#f2c14e"/>'
            '<path d="M160 120 L240 128 Q240 148 200 147 Z" fill="#fff3cf"/>'
            '<path d="M160 120 L200 147" stroke="#e3a92d" stroke-width="3"/>'
            '<path d="M84 118 Q160 104 236 118" fill="none" stroke="#d99a26" stroke-width="4" opacity=".5"/>'
            '<circle cx="190" cy="134" r="5" fill="#ffe8a8"/><circle cx="212" cy="138" r="4" fill="#ffe8a8"/>'
            '<path d="M266 70 l10 60 M280 70 l-2 60" stroke="#c9ccd6" stroke-width="5" stroke-linecap="round"/>')


@scene("espana", "day")
def _():
    return (sun(258, 46, 18) + cloud(70, 48, .8) + ground("#e8cf8f", 168) +
            '<rect x="88" y="36" width="6" height="134" rx="3" fill="#8a8fa3"/><circle cx="91" cy="34" r="6" fill="#f2c94c"/>'
            '<path d="M94 44 Q140 34 190 44 Q230 52 240 44 V116 Q230 124 190 116 Q140 106 94 116 Z" fill="#c8102e"/>'
            '<path d="M94 62 Q140 52 190 62 Q230 70 240 62 V98 Q230 106 190 98 Q140 88 94 98 Z" fill="#ffc400"/>'
            '<rect x="118" y="68" width="16" height="22" rx="3" fill="#c8102e" opacity=".85"/>')


@scene("manana", "warm")
def _():
    return ('<path d="M0 130 H320 V182 Q320 200 302 200 H18 Q0 200 0 182 Z" fill="#8ec5a0"/>' +
            sun(110, 130, 30, "#ffb04a") + '<path d="M0 130 H320 V200 H0 Z" fill="#8ec5a0" opacity="0"/>' +
            '<path d="M0 132 Q80 118 160 132 T320 132 V182 Q320 200 302 200 H18 Q0 200 0 182 Z" fill="#7fbf94"/>' +
            '<rect x="196" y="34" width="86" height="92" rx="10" fill="#fff"/><rect x="196" y="34" width="86" height="24" rx="10" fill="#e2513d"/>'
            '<rect x="196" y="48" width="86" height="10" fill="#e2513d"/>' + text(239, 108, "+1", 34, "#e2513d") +
            '<circle cx="216" cy="34" r="4" fill="#26305e"/><circle cx="262" cy="34" r="4" fill="#26305e"/>')


@scene("gracias", "pink")
def _():
    return (person(100, 200, .95, skin="a", hair="blond", style="ponytail", shirt="teal", mouth="smile",
                   arm_r="hand") +
            '<rect x="136" y="104" width="34" height="30" rx="4" fill="#e2513d"/><path d="M153 104 V134 M136 118 H170" stroke="#ffc93c" stroke-width="5"/>'
            '<path d="M153 104 q-12 -14 -2 -16 q8 0 2 16 q6 -16 14 -14 q8 4 -14 14" fill="#ffc93c"/>' +
            person(232, 200, .95, skin="c", hair="dark", style="short", shirt="yellow", mouth="grin",
                   eyes="happy", arm_l="heart", arm_r="heart", flip=True) +
            heart(250, 46, 12) + heart(278, 70, 8, "#ff8fa3"))


@scene("la_cerveza", "warm")
def _():
    return (floor("#c98f5e", 160) +
            '<path d="M110 58 H200 V160 Q200 170 190 170 H120 Q110 170 110 160 Z" fill="#f2b63d" opacity=".95"/>'
            '<path d="M200 76 H222 Q238 76 238 94 V126 Q238 144 222 144 H200" fill="none" stroke="#e6edf7" stroke-width="12"/>'
            '<path d="M110 58 H200 V160 Q200 170 190 170 H120 Q110 170 110 160 Z" fill="none" stroke="#e6edf7" stroke-width="6"/>'
            '<path d="M104 62 Q104 36 126 40 Q134 24 154 32 Q170 20 186 34 Q206 30 206 54 Q206 66 192 64 H118 Q104 66 104 62 Z" fill="#fff"/>'
            '<circle cx="140" cy="120" r="4" fill="#fff" opacity=".7"/><circle cx="160" cy="140" r="3" fill="#fff" opacity=".7"/>'
            '<circle cx="176" cy="104" r="3.5" fill="#fff" opacity=".7"/><path d="M128 76 V150" stroke="#fff" stroke-width="6" opacity=".35" stroke-linecap="round"/>')


@scene("la_plaza", "day")
def _():
    arches = "".join(f'<path d="M{x} 150 V112 a12 12 0 0 1 24 0 V150" fill="#e8b47a"/>' for x in (20, 56, 232, 268))
    return (sun(160, 34, 14) + '<rect x="10" y="70" width="104" height="90" fill="#f2d3a6"/><rect x="206" y="70" width="104" height="90" fill="#f2d3a6"/>' +
            '<path d="M6 70 H118 M202 70 H314" stroke="#c97a4a" stroke-width="8"/>' + arches +
            "".join(f'<rect x="{x}" y="82" width="12" height="16" rx="2" fill="#7fb2ff"/>' for x in (26, 62, 238, 274)) +
            floor("#e9dccb", 150) +
            '<ellipse cx="160" cy="160" rx="70" ry="16" fill="#7fb2ff"/><ellipse cx="160" cy="156" rx="70" ry="14" fill="none" stroke="#c9ccd6" stroke-width="6"/>'
            '<rect x="154" y="104" width="12" height="52" fill="#c9ccd6"/><ellipse cx="160" cy="104" rx="26" ry="7" fill="#c9ccd6"/>'
            '<path d="M160 96 q-24 -26 -40 18 M160 96 q24 -26 40 18 M160 96 V70" fill="none" stroke="#7fb2ff" stroke-width="4" stroke-linecap="round"/>')


@scene("el_chocolate", "pink")
def _():
    squares = "".join(f'<rect x="{x}" y="{y}" width="34" height="26" rx="3" fill="#5a3320"/>'
                      for x in (86, 124, 162) for y in (70, 100, 130))
    return ('<g transform="rotate(-10 160 110)">'
            '<rect x="80" y="64" width="160" height="98" rx="8" fill="#4a2a1a"/>' + squares +
            '<path d="M196 64 H240 V162 H196 Z" fill="#e2513d"/><path d="M196 64 l12 14 l-12 14 l12 14 l-12 14 l12 14 l-12 14 l12 14" fill="none" stroke="#c43a2a" stroke-width="3"/>'
            '</g><rect x="232" y="132" width="30" height="24" rx="3" fill="#5a3320" transform="rotate(16 247 144)"/>' +
            star(60, 50, 7, "#ffffff") + star(270, 52, 5, "#ffffff"))


@scene("el_perro", "mint")
def _():
    return (ground("#a7d89a", 166) +
            '<path d="M226 104 q30 -30 36 -6" fill="none" stroke="#c98f5e" stroke-width="10" stroke-linecap="round"/>'
            '<rect x="110" y="96" width="122" height="56" rx="28" fill="#c98f5e"/>'
            '<rect x="126" y="138" width="16" height="34" rx="8" fill="#c98f5e"/><rect x="200" y="138" width="16" height="34" rx="8" fill="#c98f5e"/>'
            '<circle cx="114" cy="82" r="34" fill="#c98f5e"/>'
            '<path d="M86 60 Q70 70 76 104 Q90 100 94 76 Z M138 56 Q156 62 154 96 Q140 94 134 72 Z" fill="#8a5a3b"/>'
            '<ellipse cx="102" cy="94" rx="16" ry="12" fill="#f3d7b4"/><ellipse cx="96" cy="88" rx="6" ry="5" fill="#23202a"/>'
            '<circle cx="104" cy="74" r="4" fill="#23202a"/><circle cx="126" cy="74" r="4" fill="#23202a"/>'
            '<path d="M100 102 q4 10 10 0" fill="#e8506b"/><rect x="100" y="112" width="34" height="8" rx="4" fill="#e2513d"/>'
            '<circle cx="118" cy="122" r="5" fill="#ffc93c"/>')


@scene("el_vino", "lilac")
def _():
    return (floor("#cdb6e6", 160) +
            '<rect x="86" y="30" width="22" height="34" rx="4" fill="#2f5d3a"/><path d="M78 74 Q78 60 97 58 Q116 60 116 74 V164 Q116 170 110 170 H84 Q78 170 78 164 Z" fill="#2f5d3a"/>'
            '<rect x="82" y="104" width="30" height="34" rx="3" fill="#f3e5c9"/><rect x="86" y="24" width="22" height="10" rx="3" fill="#8a1c2c"/>'
            '<path d="M168 70 H232 Q234 112 200 118 Q166 112 168 70 Z" fill="#fff" opacity=".6"/>'
            '<path d="M170 88 H230 Q226 112 200 116 Q174 112 170 88 Z" fill="#8a1c2c"/>'
            '<rect x="197" y="116" width="6" height="40" fill="#e6edf7"/><ellipse cx="200" cy="160" rx="24" ry="6" fill="#e6edf7"/>' +
            star(260, 60, 6, "#ffffff"))


# ================================================================ тема 1

@scene("buenos_dias", "day")
def _():
    return (sun(250, 56, 24) + cloud(70, 40, .8) + ground("#c9e3b4") +
            person(130, 200, 1.0, skin="b", hair="brown", style="long", shirt="yellow", mouth="grin", eyes="happy",
                   arm_l="up", arm_r="up"))


@scene("buenas_tardes", "dusk")
def _():
    return (sun(250, 118, 30, "#ff8a3d", rays=False) +
            '<path d="M0 132 Q80 120 160 134 T320 128 V182 Q320 200 302 200 H18 Q0 200 0 182 Z" fill="#e6a26b"/>' +
            person(120, 200, 1.0, skin="a", hair="dark", style="short", shirt="teal", mouth="smile", arm_r="wave",
                   extra=collar_shirt()) +
            '<circle cx="62" cy="52" r="20" fill="#fff"/><path d="M62 52 V40 M62 52 L74 58" stroke="#26305e" stroke-width="3" stroke-linecap="round"/>' +
            text(62, 92, "17:00", 14, "#26305e"))


@scene("buenas_noches", "night")
def _():
    return (moon(250, 52, 24) + star(60, 40) + star(120, 26, 5) + star(190, 60, 4) + star(290, 110, 5) + star(30, 100, 4) +
            '<path d="M0 160 H320 V182 Q320 200 302 200 H18 Q0 200 0 182 Z" fill="#2c3672"/>'
            '<rect x="70" y="96" width="110" height="70" fill="#3a4486"/><path d="M60 100 L125 56 L190 100 Z" fill="#26305e"/>'
            '<rect x="88" y="112" width="26" height="22" rx="3" fill="#ffd66b"/><rect x="136" y="112" width="26" height="22" rx="3" fill="#ffd66b"/>'
            '<rect x="112" y="140" width="24" height="26" rx="3" fill="#26305e"/>' +
            text(236, 140, "z", 22, "#c9ccd6") + text(254, 122, "z", 28, "#c9ccd6") + text(276, 100, "z", 34, "#c9ccd6"))


@scene("adios", "day")
def _():
    return (cloud(250, 40, .8) + ground() +
            '<rect x="196" y="130" width="54" height="48" rx="8" fill="#e2513d"/><path d="M212 130 V120 H234 V130" fill="none" stroke="#26305e" stroke-width="5"/>'
            '<path d="M206 146 H240" stroke="#fff" stroke-width="4" opacity=".6"/>' +
            person(130, 200, 1.0, skin="a", hair="blond", style="short", shirt="blue", mouth="smile", arm_l="wave",
                   arm_r="hand") +
            '<path d="M232 60 l36 0 m-12 -10 l12 10 l-12 10" fill="none" stroke="#26305e" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')


@scene("hasta_luego", "mint")
def _():
    return (person(110, 200, 1.0, skin="c", hair="dark", style="ponytail", shirt="purple", mouth="grin", eyes="happy",
                   arm_r="wave") +
            '<circle cx="240" cy="84" r="44" fill="#fff"/><circle cx="240" cy="84" r="44" fill="none" stroke="#2f9e6e" stroke-width="6"/>'
            '<path d="M240 84 V56 M240 84 L258 96" stroke="#26305e" stroke-width="5" stroke-linecap="round"/>'
            '<path d="M240 40 A44 44 0 0 1 282 70" fill="none" stroke="#f2a516" stroke-width="8" stroke-linecap="round"/>'
            '<circle cx="240" cy="84" r="4" fill="#26305e"/>')


@scene("hasta_manana", "night")
def _():
    return (moon(60, 46, 18) + star(120, 30, 4) + star(28, 90, 4) + star(300, 160, 4) +
            person(120, 200, 1.0, skin="a", hair="brown", style="bun", shirt="pink", mouth="smile", eyes="happy",
                   arm_r="wave") +
            '<rect x="206" y="52" width="88" height="96" rx="10" fill="#fff"/><rect x="206" y="52" width="88" height="26" rx="10" fill="#f2a516"/>'
            '<rect x="206" y="66" width="88" height="12" fill="#f2a516"/>' + sun(250, 118, 16, "#ffb04a"))


@scene("que_tal", "day")
def _():
    return (person(92, 200, .95, skin="b", hair="dark", style="short", shirt="green", mouth="o", arm_r="hand",
                   brows="up") +
            person(236, 200, .95, skin="a", hair="red", style="long", shirt="yellow", mouth="smile", flip=True) +
            bubble(108, 22, 70, 50, "left", qmark(143, 59, 34)) + bubble(196, 34, 54, 36, "right", text(223, 60, "…", 24)))


@scene("bien", "mint")
def _():
    return (person(140, 200, 1.05, skin="a", hair="brown", style="curly", shirt="blue", mouth="smile", arm_r="thumb") +
            '<circle cx="250" cy="70" r="34" fill="#2f9e6e"/><path d="M234 70 q16 18 32 0" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round"/>'
            '<circle cx="238" cy="58" r="4" fill="#fff"/><circle cx="262" cy="58" r="4" fill="#fff"/>')


@scene("muy_bien", "warm")
def _():
    return (person(160, 200, 1.05, skin="c", hair="dark", style="ponytail", shirt="red", mouth="grin", eyes="happy",
                   arm_l="thumb", arm_r="thumb") +
            star(60, 50, 12, "#f2a516") + star(262, 46, 14, "#f2a516") + star(90, 110, 7, "#f2a516") + star(240, 116, 8, "#f2a516") +
            star(160, 22, 8, "#f2a516"))


@scene("regular", "grey")
def _():
    return (person(140, 200, 1.05, skin="b", hair="blond", style="long", shirt="navy", mouth="wavy", arm_r="hand") +
            '<path d="M196 112 l10 -8 l10 8" fill="none" stroke="#26305e" stroke-width="0"/>'
            '<path d="M222 66 q8 -8 16 0 t16 0 t16 0" fill="none" stroke="#8a8fa3" stroke-width="6" stroke-linecap="round"/>'
            '<path d="M222 90 H270" stroke="#8a8fa3" stroke-width="6" stroke-linecap="round"/>')


@scene("mal", "grey")
def _():
    drops = "".join(f'<path d="M{x} {y} q-4 8 0 10 q4 -2 0 -10" fill="#7fb2ff"/>' for x, y in ((110, 70), (140, 82), (170, 68), (196, 80), (126, 96)))
    return (cloud(150, 44, 1.6, "#9aa3b5") + drops +
            person(150, 200, .95, skin="a", hair="dark", style="short", shirt="purple", mouth="sad", brows="worried", eyes="closed"))


@scene("y_tu", "lilac")
def _():
    return (person(96, 200, .95, skin="a", hair="brown", style="long", shirt="teal", mouth="smile", arm_r="point") +
            person(244, 200, .95, skin="c", hair="dark", style="short", shirt="yellow", mouth="o", brows="up", flip=True) +
            bubble(110, 24, 60, 46, "left", qmark(140, 59, 32)))


@scene("tu", "mint")
def _():
    return (person(96, 200, .95, skin="b", hair="dark", style="curly", shirt="red", mouth="grin", arm_r="point") +
            person(240, 200, .95, skin="a", hair="blond", style="ponytail", shirt="green", mouth="smile", eyes="happy", flip=True) +
            '<path d="M186 40 l14 -14 M206 46 l20 -4 M178 30 l-2 -18" stroke="#f2a516" stroke-width="5" stroke-linecap="round"/>')


@scene("usted", "cream")
def _():
    return (person(100, 200, .95, skin="a", hair="brown", style="short", shirt="blue", mouth="smile", extra=tie()) +
            person(232, 200, .95, skin="b", hair="grey", style="bald", shirt="navy", mouth="smile", age="old",
                   extra=mustache() + glasses() + top_hat(), flip=True))


@scene("como_estas", "day")
def _():
    return (person(92, 200, .95, skin="c", hair="dark", style="ponytail", shirt="pink", mouth="grin", eyes="happy",
                   arm_r="wave") +
            person(236, 200, .95, skin="a", hair="red", style="curly", shirt="teal", mouth="smile", flip=True) +
            bubble(112, 20, 92, 48, "left", text(144, 54, "?", 30, "#2346c4") + heart(178, 44, 9)))


@scene("como_esta_usted", "cream")
def _():
    return (person(96, 200, .95, skin="a", hair="blond", style="short", shirt="green", mouth="smile", arm_r="hand",
                   extra=collar_shirt()) +
            person(236, 200, .95, skin="b", hair="grey", style="bun", shirt="purple", mouth="smile", age="old",
                   extra=necklace() + glasses(), flip=True) +
            bubble(110, 18, 64, 50, "left", qmark(142, 55, 32)))


@scene("y_usted", "cream")
def _():
    return (person(92, 200, .95, skin="b", hair="grey", style="bald", shirt="navy", mouth="smile", age="old",
                   arm_r="hand", extra=mustache() + tie()) +
            person(236, 200, .95, skin="a", hair="brown", style="long", shirt="red", mouth="o", brows="up", flip=True) +
            bubble(112, 22, 60, 46, "left", qmark(142, 57, 30)))


@scene("el_senor", "day")
def _():
    return (person(160, 200, 1.1, skin="a", hair="grey", style="bald", shirt="navy", mouth="smile", age="old",
                   extra=mustache() + tie("#2346c4") + top_hat("#26305e", "#f2a516")))


@scene("la_senora", "pink")
def _():
    return (person(160, 200, 1.1, skin="b", hair="grey", style="bun", shirt="purple", mouth="smile", age="old",
                   extra=necklace() + '<circle cx="-28" cy="-100" r="4" fill="#f2c94c"/><circle cx="28" cy="-100" r="4" fill="#f2c94c"/>'))


@scene("por_favor", "warm")
def _():
    return ('<rect x="0" y="146" width="320" height="54" rx="0" fill="#8a5a3b"/><rect x="0" y="140" width="320" height="10" fill="#6b3f26"/>' +
            person(110, 200, .95, skin="a", hair="brown", style="long", shirt="blue", mouth="smile", arm_r="hand") +
            '<path d="M222 118 H262 L258 140 H226 Z" fill="#fff"/><path d="M262 124 q12 2 6 12 q-3 4 -10 2" fill="none" stroke="#fff" stroke-width="5"/>'
            '<path d="M232 110 q-4 -8 0 -14 M246 110 q-4 -8 0 -14" fill="none" stroke="#c9ccd6" stroke-width="3" stroke-linecap="round"/>' +
            bubble(150, 30, 84, 46, "left", heart(176, 54, 8) + text(206, 62, "☕", 22)))


@scene("muchas_gracias", "pink")
def _():
    return (person(160, 200, 1.05, skin="c", hair="dark", style="long", shirt="yellow", mouth="grin", eyes="happy",
                   arm_l="heart", arm_r="heart") +
            heart(70, 60, 14) + heart(250, 52, 16) + heart(100, 120, 9, "#ff8fa3") + heart(232, 122, 10, "#ff8fa3") + heart(160, 26, 9))


@scene("de_nada", "mint")
def _():
    return (person(96, 200, .95, skin="a", hair="blond", style="ponytail", shirt="pink", mouth="grin", eyes="happy",
                   arm_l="heart", arm_r="heart") + heart(60, 50, 10) +
            person(236, 200, .95, skin="b", hair="dark", style="short", shirt="green", mouth="smile", arm_r="hand", flip=True) +
            '<path d="M168 48 q-10 -14 4 -18 M178 60 q-14 -4 -10 -16" fill="none" stroke="#2f9e6e" stroke-width="0"/>' +
            bubble(150, 30, 60, 40, "right", text(180, 58, "♪", 22, "#2f9e6e")))


@scene("perdon", "warm")
def _():
    return (floor("#e9dccb", 170) +
            person(110, 200, .95, skin="a", hair="brown", style="short", shirt="blue", mouth="o", brows="worried",
                   arm_l="chin", arm_r="hand") +
            '<path d="M196 160 q30 -10 60 4 q20 8 -10 12 q-30 4 -50 -16 Z" fill="#8a5a3b" opacity=".85"/>'
            '<path d="M200 128 H232 L228 150 H204 Z" fill="#fff" transform="rotate(70 216 140)"/>' +
            text(160, 52, "!", 34, "#e2513d") +
            person(262, 200, .8, skin="c", hair="dark", style="long", shirt="yellow", mouth="o", brows="up", flip=True))


@scene("vale", "day")
def _():
    return (person(130, 200, 1.05, skin="b", hair="brown", style="ponytail", shirt="teal", mouth="grin", eyes="happy",
                   arm_r="ok") + check(252, 70, 1.3))


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for slug, body in S.items():
        (out / f"{slug}.svg").write_text(body + "\n", encoding="utf-8")
    print(len(S), "картинок")
