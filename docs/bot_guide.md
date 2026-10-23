# Бот на Cloudflare

Бот @Eduardo_maestro_bot работает на Cloudflare Workers (код — `bot/`) и делает две вещи:

1. **Публикует уроки вовремя.** Каждый час он смотрит время по Киеву, и в часы `PUBLISH_HOURS`
   (`bot/wrangler.toml`, сейчас 9 и 15) запускает на GitHub workflow «Публикация урока». У Cloudflare
   расписание точное, а `cron` в GitHub Actions опаздывает на 5–9 часов. Сама публикация, лимит постов в день
   и `state/state.json` — как раньше, в GitHub. Переход на зимнее время бот учитывает сам.
2. **Личные повторения в личке.** `/repaso` — 10 карточек: слова, которые пора повторить, и до 5 новых из уже
   вышедших уроков. На карточке — слово и его озвучка, под кнопкой «Показать перевод» — перевод и пример.
   Ученик отмечает «Помню» или «Не помню». У каждого своё расписание (система Лейтнера): слово, которое
   помнят, возвращается через 1, 3, 7, 14, 30, 60, 120 дней; забытое — через 3 карточки этого же повторения (если они ещё есть) и снова
   на следующий день. `/progreso` — сколько слов выучено. Прогресс хранится в Cloudflare KV
   (`espanol-cada-dia-srs`).

В конце каждого урока — ссылка «🔁 Повторить слова урока» (`t.me/Eduardo_maestro_bot?start=l-<id урока>`):
она открывает бота сразу на словах этого урока. В уроках без новых слов (тесты, повторения) ссылка ведёт
на обычное повторение (`?start=repaso`). Имя бота для ссылки — `bot` в `content/course.yaml`.

Бот показывает слова только тех уроков, которые уже вышли в канал: список он читает из `state/state.json`
на GitHub. Слова и озвучка выгружаются из курса (`python -m espanol bot-data`), когда workflow
«Бот на Cloudflare» (`.github/workflows/bot.yml`) выкладывает бота. Он запускается сам после правок
в `content/` или `bot/`.

## Как включить (один раз)

Все ключи — только в GitHub Secrets (репозиторий → Settings → Secrets and variables → Actions →
New repository secret). В чат и в файлы репозитория их не пишите.

1. **CLOUDFLARE_API_TOKEN.** dash.cloudflare.com → справа вверху профиль → My Profile → API Tokens →
   Create Token → шаблон **Edit Cloudflare Workers** → в Account Resources выберите свой аккаунт →
   Continue to summary → Create Token. Скопируйте токен в секрет `CLOUDFLARE_API_TOKEN`.
2. **CLOUDFLARE_ACCOUNT_ID.** dash.cloudflare.com → Workers & Pages: справа будет Account ID.
   Скопируйте его в секрет `CLOUDFLARE_ACCOUNT_ID`.
3. **BOT_GITHUB_TOKEN** — чтобы бот мог запускать публикацию. github.com → Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → Generate new token. Resource owner — аккаунт владельца
   репозитория, Repository access — Only select repositories → `Espa-ol-cada-d-a`, Permissions →
   Repository permissions → **Actions: Read and write**. Срок — год (запишите дату: потом токен нужно
   продлить, иначе бот пришлёт в личку предупреждение и уроки снова будут выходить только по `cron` GitHub).
   Скопируйте его в секрет `BOT_GITHUB_TOKEN`. Если репозиторий не ваш и fine-grained токен его не видит,
   подойдёт classic token с галочкой `repo`.
4. Actions → **«Бот на Cloudflare»** → Run workflow. Первый запуск дольше (минут 5–10): озвучиваются все слова,
   потом озвучка берётся из кеша.
5. **TELEGRAM_REVIEW_CHAT_ID.** Напишите боту `/id` и впишите число из ответа в секрет
   `TELEGRAM_REVIEW_CHAT_ID`. Это нужно сразу: теперь сообщения бота получает Cloudflare, и прежний способ
   «отправить тому, кто последним написал боту» (`--chat auto`) в «Тест урока в личку» и «Разбор видео»
   больше не работает — они шлют в этот чат. Потом ещё раз запустите «Бот на Cloudflare»: тогда бот сможет
   писать вам, если публикация не запустилась.
6. Проверьте: напишите боту `/repaso`.

## Время публикации

Время меняется в `bot/wrangler.toml` (`PUBLISH_HOURS`, часы по Киеву через запятую), после коммита
бот перевыкладывается сам. Пока бот только включается, в `publish.yml` остаётся и старый `cron`: если GitHub
сработает раньше бота, лишнего поста не будет — лимит `POSTS_PER_DAY` общий.

## Проверка

```bash
python -m espanol bot-data --no-audio   # bot/data/words.json
node --test bot/test/*.test.js          # тесты бота (повторения, расписание, кнопки)
```
