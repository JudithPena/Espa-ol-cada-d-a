"""Постоянный режим: бот сам публикует уроки по расписанию (для сервера/VPS)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from datetime import time as dtime
from typing import Callable
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)


def parse_times(values: list[str]) -> list[dtime]:
    times = []
    for value in values:
        for part in value.split(","):
            hours, minutes = part.strip().split(":")
            times.append(dtime(int(hours), int(minutes)))
    return sorted(set(times))


def next_run(now: datetime, times: list[dtime]) -> datetime:
    for day in range(0, 2):
        date = (now + timedelta(days=day)).date()
        for t in times:
            candidate = datetime.combine(date, t, tzinfo=now.tzinfo)
            if candidate > now:
                return candidate
    raise ValueError("пустое расписание")


def run_forever(publish: Callable[[], str], times: list[dtime], tz: str) -> None:
    zone = ZoneInfo(tz)
    log.info("Расписание: %s (%s)", ", ".join(t.strftime("%H:%M") for t in times), tz)
    while True:
        target = next_run(datetime.now(zone), times)
        log.info("Следующая публикация: %s", target.strftime("%Y-%m-%d %H:%M %Z"))
        while (left := (target - datetime.now(zone)).total_seconds()) > 0:
            time.sleep(min(left, 300))
        try:
            log.info(publish())
        except Exception:  # не падаем: попробуем в следующий раз
            log.exception("ошибка публикации")
