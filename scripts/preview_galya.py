"""Send a few Galya cards with pictures only to the configured author's private chat."""
import os
from pathlib import Path

from espanol.config import load_settings
from espanol.mywords import GALYA_FOLDER, load_deck, render_card
from espanol.telegram import TelegramAPI

SAMPLES = ("atropellar", "por lo visto", "aunque")


def main():
    settings = load_settings()
    chat = os.environ.get('TELEGRAM_REVIEW_CHAT_ID', '').strip()
    if not chat or int(chat) <= 0:
        raise RuntimeError('Нужен TELEGRAM_REVIEW_CHAT_ID личного чата автора')
    api = TelegramAPI(settings.token)
    deck = {w.word: w for w in load_deck(settings.content_dir, GALYA_FOLDER)}
    for name in SAMPLES:
        word = deck[name]
        with Path(word.image).open('rb') as image:
            api.call('sendPhoto', {'chat_id': chat},
                     files={'photo': ('card.png', image, 'image/png')})
        api.send_message(chat, render_card(word))
    print('Карточки Гали отправлены в личный чат автора.')


if __name__ == '__main__':
    main()
