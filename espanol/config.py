"""Настройки из переменных окружения (и необязательного файла .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | str = ROOT / ".env") -> None:
    """Простейший разбор .env: KEY=VALUE, уже заданные переменные не перезаписываются."""
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "да")


@dataclass
class Settings:
    token: str = ""
    chat_id: str = ""
    timezone: str = "Europe/Moscow"
    posts_per_day: int = 1
    audio: bool = True
    tts_rate: str = "-10%"
    voices: dict[str, str] = field(default_factory=dict)
    delay: float = 1.5
    content_dir: Path = ROOT / "content"
    state_file: Path = ROOT / "state" / "state.json"


def load_settings() -> Settings:
    load_dotenv()
    env = os.environ
    voices = {
        role: env[f"TTS_VOICE_{role.upper()}"]
        for role in ("f1", "f2", "f3", "m1", "m2", "m3")
        if env.get(f"TTS_VOICE_{role.upper()}")
    }
    return Settings(
        token=env.get("TELEGRAM_BOT_TOKEN", "").strip(),
        chat_id=env.get("TELEGRAM_CHAT_ID", "").strip(),
        timezone=env.get("TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow",
        posts_per_day=int(env.get("POSTS_PER_DAY") or 1),
        audio=_bool(env.get("ENABLE_AUDIO"), True),
        tts_rate=env.get("TTS_RATE", "-10%").strip() or "-10%",
        voices=voices,
        delay=float(env.get("SEND_DELAY") or 1.5),
        content_dir=Path(env.get("CONTENT_DIR") or ROOT / "content"),
        state_file=Path(env.get("STATE_FILE") or ROOT / "state" / "state.json"),
    )
