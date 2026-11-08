"""Озвучка сайта заранее: каждое испанское слово и фразу сайта записываем нейроголосом (edge-tts).

Встроенные голоса телефонов звучат по-разному, а на телефоне без испанского голоса испанский текст
читается русским голосом. Поэтому сайт проигрывает готовые MP3 из папки `a/` рядом со страницей,
а встроенный голос остаётся запасным — для того, чего нет в записи.

Голоса — только Испания (курс учит испанский Испании): две женщины и мужчина. Слово всегда звучит одним
и тем же голосом (выбор по хешу текста). В диалогах у каждого персонажа свой постоянный голос (`CAST`):
голосов Испании у edge-tts всего три, поэтому персонажей одного пола различаем ещё и высотой тона —
голос записывается как «es-ES-AlvaroNeural@-14Hz».
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

VOICES = ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-ES-XimenaNeural"]
F1, F2, M = "es-ES-ElviraNeural", "es-ES-XimenaNeural", "es-ES-AlvaroNeural"
# Персонаж → (пол, голос@тон, аватар). Один и тот же персонаж во всех диалогах звучит и выглядит одинаково,
# а собеседники одного диалога — всегда по-разному (проверяет tests/test_site.py). Аватар — файл
# content/art/avatars/<аватар>.webp (иллюстрация из нейросети, см. docs/avatars_guide.md); пока файла нет,
# на сайте нейтральная иконка. Новый персонаж без строки здесь получит голос по полу и нейтральную иконку.
CAST: dict[str, tuple[str, str, str]] = {
    "Lucía": ("f", F1, "lucia"),
    "Ana": ("f", F2, "ana"),
    "Elena": ("f", F2 + "@-6Hz", "elena"),
    "Clara": ("f", F1 + "@+6Hz", "clara"),
    "Irina": ("f", F1 + "@+6Hz", "irina"),
    "Olga": ("f", F2 + "@+6Hz", "olga"),
    "Karina": ("f", F2 + "@+10Hz", "karina"),
    "Profesora": ("f", F1 + "@-8Hz", "profesora"),
    "Recepcionista": ("f", F1 + "@-4Hz", "recepcionista"),
    "Dependienta": ("f", F2, "dependienta"),
    "Médica": ("f", F2 + "@-8Hz", "medica"),
    "Madre": ("f", F1 + "@-12Hz", "madre"),
    "Señora": ("f", F1 + "@-14Hz", "senora"),
    "Pablo": ("m", M, "pablo"),
    "Diego": ("m", M + "@+8Hz", "diego"),
    "Iván": ("m", M + "@+6Hz", "ivan"),
    "Carlos": ("m", M + "@+4Hz", "carlos"),
    "Tom": ("m", M + "@+10Hz", "tom"),
    "Hugo": ("m", M + "@+6Hz", "hugo"),
    "Sergio": ("m", M + "@-4Hz", "sergio"),
    "Camarero": ("m", M + "@-14Hz", "camarero"),
    "Señor García": ("m", M + "@-16Hz", "senor_garcia"),
}
_SPARE = {"f": [F1, F2, F1 + "@-8Hz", F2 + "@+6Hz", F1 + "@+6Hz", F2 + "@-8Hz"],
          "m": [M, M + "@-14Hz", M + "@+8Hz", M + "@-6Hz", M + "@+14Hz"]}


def _gender(name: str) -> str:
    """Пол незнакомого персонажа по имени: «-a» — женский (Marta, Profesora), иначе мужской."""
    word = name.split()[-1].lower()
    return "f" if word.endswith(("a", "á")) or name.lower().startswith(("señora", "doña")) else "m"


def cast(speakers: list[str]) -> dict[str, dict]:
    """Голоса собеседников одного диалога: {имя: {v: голос, g: пол, a: аватар}}; одинаковых голосов нет."""
    out: dict[str, dict] = {}
    for name in speakers:
        g, v, a = CAST.get(name) or (_gender(name), "", "")
        used = {c["v"] for c in out.values()}
        if not v or v in used:
            v = next((x for x in _SPARE[g] if x not in used), _SPARE[g][0])
        out[name] = {"v": v, "g": g, "a": a}
    return out
RATE = "-5%"
AUDIO_DIR = "a"


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def _voice(text: str) -> str:
    return VOICES[int(hashlib.sha1(text.encode()).hexdigest(), 16) % len(VOICES)]


def _spanish(text: str) -> bool:
    """Испанский вариант ответа (озвучиваем): есть латиница и нет кириллицы."""
    return any("a" <= ch.lower() <= "z" or ch in "áéíóúüñÁÉÍÓÚÜÑ" for ch in text) and not any("а" <= ch.lower() <= "я" or ch in "ёЁ" for ch in text)


def file_id(text: str, voice: str) -> str:
    return hashlib.sha1(f"{voice}|{RATE}|{text}".encode()).hexdigest()[:16]


def audio_texts(data: dict) -> dict[str, tuple[str, str]]:
    """Ключ для страницы → (текст, голос). Ключ — сам текст; реплика диалога — «@голос|текст»."""
    out: dict[str, tuple[str, str]] = {}

    def add(text, voice=None, key=None):
        text = _clean(text)
        # Только то, в чём есть латиница: русская плитка «пиво» из «¿Cómo se dice «пиво»…?» испанским голосом не читается.
        if text and any("a" <= ch.lower() <= "z" or ch in "áéíóúüñÁÉÍÓÚÜÑ" for ch in text):
            out.setdefault(key or text, (text, voice or _voice(text)))

    def cards(items):
        for c in items or []:
            for ex in c.get("ex") or []:
                add(ex[1])
            for pair in c.get("pairs") or []:
                add(pair[1])

    for lesson in data.get("lessons", []):
        for w in lesson.get("words", []):
            add(w.get("say"))
            for ex in w.get("ex") or []:
                add(ex[0])
        for b in lesson.get("blocks", []):
            t = b.get("t")
            if t == "examples":
                for item in b["items"]:
                    add(item[2])
            elif t == "dialogue":
                for line in b["lines"]:
                    voice = b["cast"][line[0]]["v"]
                    add(line[3], voice, key=f"@{voice}|{_clean(line[3])}")
                    add(line[3])
            elif t == "reading":
                add(b.get("say"))
            elif t == "conjugation":
                for f in b.get("forms", []):
                    add(f)
            cards(b.get("cards"))
            if t == "compare":
                for c in b["cards"]:
                    add(c.get("say"))
            elif t == "choose":   # вопрос на слух, реплики-контекст, испанские варианты (звучат после ответа)
                for it in b["items"]:
                    add(it.get("say"))
                    for line in it.get("lines") or []:
                        voice = it["cast"][line[0]]["v"]
                        add(line[3], voice, key=f"@{voice}|{_clean(line[3])}")
                    if it["o"] and _spanish(it["o"][0][1]):   # верный вариант звучит после ответа
                        add(it["o"][0][1])
            elif t == "write":
                for it in b["items"]:
                    add(it.get("say"))
                    for a in it["a"]:                       # звучит тот ответ, который ученик ввёл
                        if _spanish(a):
                            add(a)
            elif t == "match":
                for left, right, say_l, say_r in b["pairs"]:
                    add(say_l)
                    add(say_r)
            elif t == "sort":
                for _, items in b["groups"]:
                    for _, say in items:
                        add(say)
            elif t == "build":
                for it in b["items"]:
                    for es in [it["es"], *it.get("alt", [])]:
                        add(es)
                    for es in [it["es"], *it.get("alt", [])]:   # плитка звучит словом своего порядка
                        for tok in es.split(" "):
                            add(tok)
            if t not in ("choose", "write"):
                cards([x for x in b.get("items") or [] if isinstance(x, dict)])
            cards(b.get("steps") if t == "list" else None)
        for es, _ in lesson.get("sentences", []):
            add(es)
            for tok in es.split(" "):  # «Соберите фразу» озвучивает каждое угаданное слово
                add(tok)
    for video in data.get("videos", []):
        for seg in video.get("segments", []):
            add(seg.get("es"))
            for w in seg.get("words", []):
                add(w.get("say"))
    return out


async def _synth(text: str, voice: str, path: Path, sem: asyncio.Semaphore) -> bool:
    import edge_tts

    async with sem:
        for attempt in range(4):
            try:
                tmp = path.with_suffix(".part")
                name, _, pitch = voice.partition("@")
                await edge_tts.Communicate(text, name, rate=RATE, pitch=pitch or "+0Hz").save(str(tmp))
                if tmp.stat().st_size < 500:
                    raise RuntimeError("пустая запись")
                tmp.replace(path)
                return True
            except Exception as err:  # сеть, лимиты сервиса — пробуем ещё раз
                log.warning("озвучка %r (%s), попытка %d: %s", text, voice, attempt + 1, err)
                await asyncio.sleep(2 * (attempt + 1))
    return False


def record(data: dict, out_dir: str | Path, cache_dir: str | Path, concurrency: int = 8) -> dict[str, str]:
    """Записывает недостающее в cache_dir, копирует нужное в out_dir/a и возвращает карту ключ → id файла."""
    from .tts import available

    texts = audio_texts(data)
    cache, target = Path(cache_dir), Path(out_dir) / AUDIO_DIR
    cache.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    jobs = {file_id(t, v): (t, v) for t, v in texts.values()}
    missing = {i: tv for i, tv in jobs.items() if not (cache / f"{i}.mp3").exists()}
    if missing and available():
        print(f"Озвучка сайта: записываю {len(missing)} из {len(jobs)}…", flush=True)
        from .tts import _trust_extra_ca
        _trust_extra_ca()

        async def run():
            sem = asyncio.Semaphore(concurrency)
            await asyncio.gather(*(_synth(t, v, cache / f"{i}.mp3", sem) for i, (t, v) in missing.items()))
        asyncio.run(run())
    elif missing:
        print(f"Озвучка сайта: edge-tts не установлен, {len(missing)} записей не будет (сработает голос телефона).")
    result = {}
    for key, (t, v) in texts.items():
        i = file_id(t, v)
        src = cache / f"{i}.mp3"
        if src.exists():
            dst = target / f"{i}.mp3"
            if not dst.exists():
                shutil.copyfile(src, dst)
            result[key] = i
    print(f"Озвучка сайта: {len(result)} из {len(texts)} фраз с записью.")
    return result
