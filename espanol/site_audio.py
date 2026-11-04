"""Озвучка сайта заранее: каждое испанское слово и фразу сайта записываем нейроголосом (edge-tts).

Встроенные голоса телефонов звучат по-разному, а на телефоне без испанского голоса испанский текст
читается русским голосом. Поэтому сайт проигрывает готовые MP3 из папки `a/` рядом со страницей,
а встроенный голос остаётся запасным — для того, чего нет в записи.

Голоса — только Испания (курс учит испанский Испании): две женщины и мужчина. Слово всегда звучит одним
и тем же голосом (выбор по хешу текста), в диалогах у каждого собеседника свой голос.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
from pathlib import Path

log = logging.getLogger(__name__)

VOICES = ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-ES-XimenaNeural"]
# Собеседники диалога по порядку появления: женщина, мужчина, другая женщина, снова мужчина.
DIALOGUE_VOICES = ["es-ES-ElviraNeural", "es-ES-AlvaroNeural", "es-ES-XimenaNeural", "es-ES-AlvaroNeural"]
RATE = "-5%"
AUDIO_DIR = "a"


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def _voice(text: str) -> str:
    return VOICES[int(hashlib.sha1(text.encode()).hexdigest(), 16) % len(VOICES)]


def file_id(text: str, voice: str) -> str:
    return hashlib.sha1(f"{voice}|{RATE}|{text}".encode()).hexdigest()[:16]


def audio_texts(data: dict) -> dict[str, tuple[str, str]]:
    """Ключ для страницы → (текст, голос). Ключ — сам текст; реплика диалога — «@N|текст» (N — собеседник)."""
    out: dict[str, tuple[str, str]] = {}

    def add(text, voice=None, key=None):
        text = _clean(text)
        if text and any(ch.isalpha() for ch in text):
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
                speakers = list(dict.fromkeys(line[0] for line in b["lines"]))
                for line in b["lines"]:
                    who = speakers.index(line[0])
                    voice = DIALOGUE_VOICES[who % len(DIALOGUE_VOICES)]
                    add(line[3], voice, key=f"@{who}|{_clean(line[3])}")
                    add(line[3])
            elif t == "reading":
                add(b.get("say"))
            elif t == "conjugation":
                for f in b.get("forms", []):
                    add(f)
            cards(b.get("cards"))
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
                await edge_tts.Communicate(text, voice, rate=RATE).save(str(tmp))
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
