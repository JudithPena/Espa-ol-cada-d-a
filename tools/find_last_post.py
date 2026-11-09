"""Находит номера последних постов канала (для одноразовой правки поста). Ничего не публикует.

Для каждого номера просит у Telegram заменить кнопки под постом на те же (их нет): если пост есть,
ответ «message is not modified» или «can't be edited», если нет — «message to edit not found».
Токен и номер канала берутся из окружения и не печатаются."""
import os
import sys

import requests

token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
start = int(sys.argv[1])
found, misses, n = [], 0, start
while misses < 25:
    r = requests.post(f"https://api.telegram.org/bot{token}/editMessageReplyMarkup",
                      json={"chat_id": chat, "message_id": n}, timeout=30).json()
    desc = str(r.get("description", "")).lower()
    if "not found" in desc or "message_id_invalid" in desc:
        misses += 1
    else:
        misses = 0
        found.append((n, desc or "ok"))
    n += 1
for num, desc in found[-12:]:
    print(num, desc)
print("Последний найденный пост:", found[-1][0] if found else "нет")
