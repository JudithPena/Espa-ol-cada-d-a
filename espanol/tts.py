"""Озвучка испанского текста нейроголосами (edge-tts, без ключей API).

Каждая реплика синтезируется отдельно своим голосом, затем MP3-фрагменты
склеиваются. Между словами в лексических уроках вставляется пауза — чтобы
успеть повторить вслух за диктором (shadowing).
"""

from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)

# f — женские голоса, m — мужские. Первые два — испанский Испании.
DEFAULT_VOICES = {
    "f1": "es-ES-ElviraNeural",
    "f2": "es-ES-XimenaNeural",
    "f3": "es-MX-DaliaNeural",
    "m1": "es-ES-AlvaroNeural",
    "m2": "es-MX-JorgeNeural",
    "m3": "es-AR-TomasNeural",
}

# Формат edge-tts: MPEG-2 Layer III, 24 кГц, 48 кбит/с, моно.
BITRATE = 48_000
# Беззвучный кадр того же формата: заголовок + нулевые данные (144 байта = 24 мс).
_SILENT_FRAME = bytes([0xFF, 0xF3, 0x64, 0xC0]) + bytes(140)
_FRAME_SECONDS = 0.024


class TTSError(Exception):
    pass


def available() -> bool:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        return False
    return True


def silence(seconds: float) -> bytes:
    return _SILENT_FRAME * max(1, round(seconds / _FRAME_SECONDS))


def duration(mp3: bytes) -> int:
    return max(1, round(len(mp3) * 8 / BITRATE))


def _trust_extra_ca() -> None:
    """edge-tts использует свой набор сертификатов; добавим корпоративный CA, если он задан."""
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if not cafile or not os.path.exists(cafile):
        return
    try:
        import edge_tts.communicate as communicate

        communicate._SSL_CTX.load_verify_locations(cafile)  # noqa: SLF001
    except (ImportError, AttributeError, OSError) as exc:  # pragma: no cover
        log.debug("не удалось добавить CA для edge-tts: %s", exc)


async def _speak(text: str, voice: str, rate: str, proxy: str | None) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, proxy=proxy)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    if not chunks:
        raise TTSError(f"пустой ответ синтеза для {text[:30]!r}")
    return b"".join(chunks)


def synthesize(segments: list[tuple[str, str]], rate: str = "-10%", pauses: bool = False,
               voices: dict[str, str] | None = None) -> bytes:
    """Синтезирует список (голос, текст) в один MP3."""
    if not available():
        raise TTSError("пакет edge-tts не установлен (pip install edge-tts)")
    voices = {**DEFAULT_VOICES, **(voices or {})}
    _trust_extra_ca()
    proxy = os.environ.get("TTS_PROXY") or os.environ.get("HTTPS_PROXY") or None
    gap = silence(1.8 if pauses else 0.6)

    async def run() -> bytes:
        parts = []
        for n, (role, text) in enumerate(segments):
            if not text.strip():
                continue
            voice = voices.get(role) or voices["f1"]
            parts.append(await _speak(text, voice, rate, proxy))
            if n < len(segments) - 1:
                parts.append(gap)
        return b"".join(parts)

    return asyncio.run(run())
