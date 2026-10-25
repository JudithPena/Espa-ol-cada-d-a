// Бот курса на Cloudflare Workers.
//  • По расписанию (каждый час) в часы PUBLISH_HOURS по Киеву запускает на GitHub публикацию урока —
//    у Cloudflare расписание точное, а cron в GitHub Actions опаздывает на несколько часов.
//  • Отвечает в личке: /repaso — личные повторения слов из вышедших уроков с кнопками,
//    /progreso — сколько слов выучено, /id — номер чата (для TELEGRAM_REVIEW_CHAT_ID).
//  • В дни REMIND_DAYS в REMIND_HOUR по Киеву сам предлагает в личке повторить слова
//    всем, кто уже писал боту (кроме тех, кто нажал «Не напоминать»).
//  • «Мои слова» — личная колода автора (только чат ADMIN_CHAT_ID): /palabras — разборы новых слов
//    и повторение, каждый день в WORDS_HOUR по Киеву бот сам зовёт заниматься (deck.js).
// Слова — bot/data/words.json и bot/data/mywords.json (python -m espanol bot-data), озвучка — bot/public/audio/.
// Прогресс каждого ученика хранится в KV (binding SRS).

import DECK from "../data/mywords.json" with { type: "json" };
import WORDS from "../data/words.json" with { type: "json" };
import {
  choices, currentItem, deckProgress, freshLeft, learn, newDeck, NEW_PER_DAY, recall, startDeckSession,
} from "./deck.js";
import {
  answer, buildLessonQueue, currentId, dayNumber, localHour, localWeekday, newUser, progress, startSession,
} from "./srs.js";

const BY_ID = new Map(WORDS.map((w) => [w.id, w]));
const deckWord = (id) => DECK.find((w) => w.id === id); // колода небольшая, тесты дополняют её на ходу

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/telegram" && request.method === "POST") {
      if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
        return new Response("forbidden", { status: 403 });
      }
      const update = await request.json();
      try {
        await handleUpdate(update, env, url.origin);
      } catch (err) { // Telegram повторяет запрос при ошибке — не зацикливаемся, пишем в лог
        console.error("update failed", err && err.stack ? err.stack : err);
      }
      return new Response("ok");
    }
    return new Response("Español cada día bot");
  },

  async scheduled(event, env, ctx) {
    const now = new Date(event.scheduledTime);
    const hour = localHour(now, env.TIMEZONE);
    if (numbers(env.PUBLISH_HOURS).includes(hour)) ctx.waitUntil(dispatchPublish(env));
    if (hour === Number(env.REMIND_HOUR) && numbers(env.REMIND_DAYS).includes(localWeekday(now, env.TIMEZONE))) {
      ctx.waitUntil(sendReminders(env));
    }
    if (hour === Number(env.WORDS_HOUR)) ctx.waitUntil(sendDeckDaily(env));
  },
};

const numbers = (list) => String(list || "").split(",").map((n) => n.trim()).filter(Boolean).map(Number);

// ---------------------------------------------------------------- публикация

export async function dispatchPublish(env) {
  const api = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.PUBLISH_WORKFLOW}/dispatches`;
  const resp = await fetch(api, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "espanol-cada-dia-bot",
    },
    body: JSON.stringify({ ref: env.GITHUB_BRANCH }),
  });
  if (resp.status === 204) return true;
  const text = (await resp.text()).slice(0, 300);
  console.error("dispatch failed", resp.status, text);
  if (env.ADMIN_CHAT_ID) {
    await tg(env, "sendMessage", {
      chat_id: env.ADMIN_CHAT_ID,
      text: `⚠️ Не смог запустить публикацию урока на GitHub (ответ ${resp.status}). ` +
        "Проверьте токен BOT_GITHUB_TOKEN: возможно, у него закончился срок.",
    });
  }
  return false;
}

// ---------------------------------------------------------------- Telegram

async function tg(env, method, payload) {
  const resp = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await resp.json();
  if (!body.ok && !/message is not modified/.test(body.description || "")) {
    console.error(method, body.error_code, body.description);
  }
  return body;
}

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const keyboard = (rows) => ({ inline_keyboard: rows });
const START_BUTTON = keyboard([[{ text: "🔁 Повторить слова", callback_data: "go" }]]);

async function handleUpdate(update, env, origin) {
  if (update.callback_query) {
    await rememberUser(env, update.callback_query.from.id);
    return handleCallback(update.callback_query, env, origin);
  }
  const msg = update.message;
  if (!msg || !msg.chat || msg.chat.type !== "private") return;
  await rememberUser(env, msg.from.id);
  const [command, param = ""] = (msg.text || "").trim().split(/\s+/);
  const cmd = command.split("@")[0].toLowerCase();
  const chat = msg.chat.id;
  const owner = isOwner(env, msg.from.id);
  if (owner && (cmd === "/palabras" || (cmd === "/start" && param === "palabras"))) {
    return startDeck(env, chat, msg.from.id, origin);
  }
  // Ссылки из уроков: t.me/бот?start=l-<урок> — слова этого урока, ?start=repaso — обычное повторение.
  if (cmd === "/start" && param.startsWith("l-")) return startRepaso(env, chat, msg.from.id, origin, param.slice(2));
  if (cmd === "/repaso" || (cmd === "/start" && param === "repaso")) return startRepaso(env, chat, msg.from.id, origin);
  if (cmd === "/progreso") return sendProgress(env, chat, msg.from.id);
  if (cmd === "/recordatorio" && env.ADMIN_CHAT_ID && String(chat) === String(env.ADMIN_CHAT_ID)) {
    // проверка для автора: так выглядит напоминание по средам и субботам
    const words = (await availableWords(env)).filter((w) => BY_ID.has(w.id));
    return sendReminder(env, msg.from.id, await loadUser(env, msg.from.id), words, true);
  }
  if (cmd === "/id") {
    return tg(env, "sendMessage", { chat_id: chat, parse_mode: "HTML", text: `Номер этого чата: <code>${chat}</code>` });
  }
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: "¡Hola! 👋 Я повторяю с вами слова из уроков канала <b>Español cada día</b>.\n\n" +
      "Каждый раз — 10 карточек: слова, которые пора повторить, и несколько новых из вышедших уроков. " +
      "Вспомните перевод, откройте карточку и честно отметьте, помните ли вы слово. " +
      "Если помните, слово вернётся через несколько дней, а если нет — повторим его ещё раз.\n\n" +
      "По средам и субботам вечером я сам напомню, если есть что повторить.\n\n" +
      "/repaso — повторить слова\n/progreso — сколько слов уже выучено" +
      (owner ? "\n/palabras — ваши слова: разборы новых и повторение" : ""),
    reply_markup: START_BUTTON,
  });
}

async function handleCallback(cq, env, origin) {
  const chat = cq.message && cq.message.chat.id;
  const [action, id] = String(cq.data || "").split(":");
  if (action.startsWith("p") && isOwner(env, cq.from.id)) return handleDeckCallback(cq, env, origin);
  if (action === "go") {
    await tg(env, "answerCallbackQuery", { callback_query_id: cq.id });
    return startRepaso(env, chat, cq.from.id, origin);
  }
  const user = await loadUser(env, cq.from.id);
  if (action === "off" || action === "on") { // напоминания по средам и субботам
    user.noRemind = action === "off";
    await saveUser(env, cq.from.id, user);
    return tg(env, "answerCallbackQuery", {
      callback_query_id: cq.id,
      show_alert: true,
      text: user.noRemind
        ? "Хорошо, больше не напоминаю. Повторять можно командой /repaso, включить напоминания — в /progreso."
        : "Напоминания включены: по средам и субботам вечером.",
    });
  }
  if (!user.session || currentId(user) !== id) { // старая кнопка от прошлой карточки
    return tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text: "Эта карточка уже пройдена" });
  }
  const word = BY_ID.get(id);
  const s = user.session;
  if (!word) { // слово убрали из курса, пока шло повторение
    user.session = null;
    await saveUser(env, cq.from.id, user);
    return tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text: "Курс обновился — начните заново: /repaso" });
  }
  if (action === "s") { // показать перевод
    await tg(env, "answerCallbackQuery", { callback_query_id: cq.id });
    return editCard(env, cq.message, back(word, s), keyboard([[
      { text: "✅ Помню", callback_data: `y:${id}` },
      { text: "❌ Не помню", callback_data: `n:${id}` },
    ]]));
  }
  if (action !== "y" && action !== "n") return;
  const known = action === "y";
  const shown = back(word, s); // до ответа: потом номер карточки уже следующий
  const today = dayNumber(new Date(), env.TIMEZONE);
  const { more, retry } = answer(user, id, known, today);
  const mark = known ? "✅ Помню" : retry ? "🔁 Не помню — вернётся через пару карточек" : "🔁 Не помню — повторим в следующий раз";
  if (!more) user.session = null;
  await saveUser(env, cq.from.id, user);
  await tg(env, "answerCallbackQuery", { callback_query_id: cq.id });
  await editCard(env, cq.message, `${shown}\n\n${mark}`, keyboard([]));
  if (more) return sendCard(env, chat, user, origin);
  const words = await availableWords(env);
  const p = progress(user, words, today);
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: `🎉 <b>Готово!</b> Помню: ${s.right}, не помню: ${s.wrong}.\n\n${summary(p)}\n\n` +
      (p.due ? `Ещё пора повторить сегодня: ${p.due}.`
        : p.fresh ? "Всё, что было на сегодня, повторено. Можно взять ещё новых слов или вернуться завтра."
          : "На сегодня всё повторено, приходите завтра."),
    reply_markup: p.due || p.fresh
      ? keyboard([[{ text: p.due ? "🔁 Повторить ещё" : "🆕 Ещё новые слова", callback_data: "go" }]]) : undefined,
  });
}

// ---------------------------------------------------------------- повторение

// lesson — id урока из ссылки (с «-» вместо «/»): тогда в повторении все слова этого урока,
// даже если урок вышел только что и state.json на GitHub ещё не обновился.
async function startRepaso(env, chat, userId, origin, lesson = "") {
  const user = await loadUser(env, userId);
  const today = dayNumber(new Date(), env.TIMEZONE);
  const own = lesson ? WORDS.filter((w) => w.lesson.replace(/[^A-Za-z0-9_-]/g, "-") === lesson) : [];
  const words = (await availableWords(env)).filter((w) => BY_ID.has(w.id));
  if (own.length) { // сначала слова урока, потом — прошлые слова, которые пора повторить
    user.session = { queue: buildLessonQueue(user, own, words, today), pos: 0, retry: [], right: 0, wrong: 0 };
    await saveUser(env, userId, user);
    return sendCard(env, chat, user, origin);
  }
  if (!startSession(user, words, today)) {
    return tg(env, "sendMessage", {
      chat_id: chat,
      text: words.length
        ? "👏 Сейчас повторять нечего: все слова повторены, а новые появятся с новыми уроками. Приходите завтра!"
        : "Пока в канале нет уроков со словами.",
    });
  }
  await saveUser(env, userId, user);
  return sendCard(env, chat, user, origin);
}

function header(s) {
  return `🃏 ${s.pos + 1}/${s.queue.length}`;
}

function front(word, s) {
  return `${header(s)}\n\n<b>${esc(word.es)}</b>\n\nВспомните перевод и откройте карточку.`;
}

function back(word, s) {
  let text = `${header(s)}\n\n${esc(word.emoji)} <b>${esc(word.es)}</b>`;
  if (word.pron) text += ` [${esc(word.pron)}]`;
  text += `\n— ${esc(word.ru)}`;
  if (word.ex) text += `\n\n<i>${esc(word.ex[0])}</i> — ${esc(word.ex[1])}`;
  return text;
}

async function sendCard(env, chat, user, origin) {
  const s = user.session;
  const word = BY_ID.get(currentId(user));
  const markup = keyboard([[{ text: "👀 Показать перевод", callback_data: `s:${word.id}` }]]);
  return (word.audio && await sendAudio(env, chat, origin, word.audio, word.es, front(word, s), markup)) ||
    tg(env, "sendMessage", { chat_id: chat, text: front(word, s), parse_mode: "HTML", reply_markup: markup });
}

// Карточка с озвучкой: слово и пример можно сразу послушать. Если аудио не ушло — null, тогда шлём текстом.
async function sendAudio(env, chat, origin, file, title, caption, markup) {
  const cached = await env.SRS.get(`audio:${file}`);
  const sent = await tg(env, "sendAudio", {
    chat_id: chat, audio: cached || `${origin}/audio/${file}`,
    title, performer: "Español cada día",
    caption, parse_mode: "HTML", reply_markup: markup,
  });
  if (!sent.ok) return null;
  const audio = sent.result.audio || sent.result.voice;
  if (!cached && audio) await env.SRS.put(`audio:${file}`, audio.file_id); // дальше Telegram берёт из своего кеша
  return sent;
}

function editCard(env, message, text, markup) {
  const target = { chat_id: message.chat.id, message_id: message.message_id, parse_mode: "HTML", reply_markup: markup };
  return typeof message.text === "string" // карточка без озвучки — текст, с озвучкой — подпись к аудио
    ? tg(env, "editMessageText", { ...target, text })
    : tg(env, "editMessageCaption", { ...target, caption: text });
}

// Слово «выучено», когда его вспомнили три раза подряд с перерывами и помнят уже неделю.
function summary(p) {
  return `📚 Слов в вышедших уроках: ${p.available}\n` +
    `🌱 Учите сейчас: ${p.seen - p.learned}\n` +
    `🏆 Выучено: ${p.learned} — помните неделю и дольше\n` +
    `🆕 Ещё не начинали: ${p.fresh}`;
}

async function sendProgress(env, chat, userId) {
  const words = await availableWords(env);
  const user = await loadUser(env, userId);
  const p = progress(user, words, dayNumber(new Date(), env.TIMEZONE));
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: `📊 <b>Ваш прогресс</b>\n\n${summary(p)}\n\nПора повторить сейчас: ${p.due}\n` +
      `🔔 Напоминания по средам и субботам: ${user.noRemind ? "выключены" : "включены"}`,
    reply_markup: keyboard([
      ...(p.due || p.fresh ? [[{ text: "🔁 Повторить слова", callback_data: "go" }]] : []),
      [user.noRemind
        ? { text: "🔔 Включить напоминания", callback_data: "on" }
        : { text: "🔕 Не напоминать", callback_data: "off" }],
    ]),
  });
}

// ---------------------------------------------------------------- напоминания

export async function sendReminders(env) {
  const words = (await availableWords(env)).filter((w) => BY_ID.has(w.id));
  for (const userId of (await env.SRS.get("users", "json")) || []) {
    const user = await loadUser(env, userId);
    if (!user.noRemind) await sendReminder(env, userId, user, words);
  }
}

// Напоминание одному ученику; если повторять нечего, не пишем (кроме проверки автором — force).
async function sendReminder(env, userId, user, words, force = false) {
  const p = progress(user, words, dayNumber(new Date(), env.TIMEZONE));
  if (!p.due && !p.fresh && !force) return;
  const what = [p.due && `пора повторить: ${p.due}`, p.fresh && `новых слов из уроков: ${p.fresh}`].filter(Boolean);
  await tg(env, "sendMessage", { // личный чат с ботом — тот же номер, что и у пользователя
    chat_id: userId,
    parse_mode: "HTML",
    text: `🔔 <b>Время повторить слова!</b>\n\nСейчас ${what.join(", ") || "повторять нечего"}. ` +
      "Десять карточек — это 3–5 минут.",
    reply_markup: keyboard([
      [{ text: "🔁 Повторить слова", callback_data: "go" }],
      [{ text: "🔕 Не напоминать", callback_data: "off" }],
    ]),
  });
}

async function rememberUser(env, userId) {
  const users = (await env.SRS.get("users", "json")) || [];
  if (!users.includes(userId)) {
    users.push(userId);
    await env.SRS.put("users", JSON.stringify(users));
  }
}

// ---------------------------------------------------------------- «Мои слова»

// Колода только у автора: его личный чат — TELEGRAM_REVIEW_CHAT_ID (ADMIN_CHAT_ID).
function isOwner(env, userId) {
  return Boolean(env.ADMIN_CHAT_ID) && String(userId) === String(env.ADMIN_CHAT_ID);
}

const perDay = (env) => Number(env.WORDS_PER_DAY) || NEW_PER_DAY;

async function startDeck(env, chat, userId, origin) {
  const deck = await loadDeck(env, userId);
  const today = dayNumber(new Date(), env.TIMEZONE);
  if (deck.session && deck.session.day === today && currentItem(deck)) { // занятие уже идёт — продолжаем
    return sendDeckCard(env, chat, deck, origin);
  }
  const s = startDeckSession(deck, DECK, today, perDay(env));
  await saveDeck(env, userId, deck);
  if (!s) {
    const p = deckProgress(deck, DECK, today);
    return tg(env, "sendMessage", {
      chat_id: chat,
      text: !DECK.length ? "В колоде пока нет слов. Пришлите Claude список — он напишет к каждому слову разбор."
        : p.fresh ? "👏 На сегодня всё: новые слова будут завтра, а повторять пока нечего."
          : "👏 Всё повторено, а новые слова в колоде закончились. Пришлите Claude ещё список.",
    });
  }
  const fresh = s.queue.filter((q) => q.startsWith("l:")).length;
  const due = s.queue.length - 2 * fresh;
  await tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: "📒 <b>Мои слова</b>\n\n" +
      [fresh && `🆕 Новых слов: ${fresh} — сначала прочитайте разборы, в конце проверим`,
        due && `🔁 Повторить: ${due}`].filter(Boolean).join("\n"),
  });
  return sendDeckCard(env, chat, deck, origin);
}

// Свой счёт у разборов новых слов и у повторения (с проверкой новых): «Новое слово 3/10», «Повторение 1/12».
function deckHeader(deck, mode) {
  const s = deck.session;
  const mine = (q) => q.startsWith(`${mode}:`);
  const n = s.queue.slice(0, s.pos + 1).filter(mine).length;
  return `${mode === "l" ? "🆕 Новое слово" : "🔁 Повторение"} ${n}/${s.queue.filter(mine).length}`;
}

function deckBack(word, header) {
  let text = `${header}\n\n<b>${esc(word.word)}</b> ${esc(word.ipa)}\n— ${esc(word.ru)}`;
  if (word.ex) text += `\n\n<i>${esc(word.ex[0])}</i> — ${esc(word.ex[1])}`;
  return text;
}

const recallButtons = (id) => [
  { text: "✅ Помню", callback_data: `py:${id}` },
  { text: "❌ Не помню", callback_data: `pn:${id}` },
];
const fullButton = (id) => [{ text: "📖 Весь разбор", callback_data: `pc:${id}` }];

async function sendDeckCard(env, chat, deck, origin) {
  const [mode, id] = currentItem(deck);
  const word = deckWord(id);
  const s = deck.session;
  if (!word) { // слово убрали из колоды, пока шло занятие
    deck.session = null;
    await saveDeck(env, chat, deck);
    return tg(env, "sendMessage", { chat_id: chat, text: "Колода обновилась — начните заново: /palabras" });
  }
  const header = deckHeader(deck, mode);
  if (mode === "l") { // разбор нового слова: сначала озвучка, потом карточка целиком
    if (word.audio) await sendAudio(env, chat, origin, word.audio, word.word, `${header} · <b>${esc(word.word)}</b>`);
    return tg(env, "sendMessage", {
      chat_id: chat, parse_mode: "HTML", text: `${header}\n\n${word.card}`,
      link_preview_options: { is_disabled: true },
      reply_markup: keyboard([[{ text: "➡️ Дальше", callback_data: `pl:${id}` }]]),
    });
  }
  // Повторение: слово и варианты перевода — бот сам видит, верно ли. Варианты помним до ответа.
  s.opts = choices(word, DECK, Number(env.CHOICES) || undefined);
  s.waiting = false;
  await saveDeck(env, chat, deck);
  const text = `${header}\n\n<b>${esc(word.word)}</b>\n\n` +
    (s.opts.length ? "Выберите перевод:" : "Вспомните значение и откройте карточку.");
  const markup = keyboard(s.opts.length
    ? s.opts.map((opt, k) => [{ text: deckWord(opt).ru, callback_data: `pa:${id}:${k}` }])
    : [[{ text: "👀 Показать", callback_data: `ps:${id}` }]]);
  return (word.audio && await sendAudio(env, chat, origin, word.audio, word.word, text, markup)) ||
    tg(env, "sendMessage", { chat_id: chat, text, parse_mode: "HTML", reply_markup: markup });
}

async function handleDeckCallback(cq, env, origin) {
  const chat = cq.message && cq.message.chat.id;
  const [action, id, choice] = String(cq.data || "").split(":");
  const done = (text) => tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text });
  if (action === "pgo") {
    await done();
    return startDeck(env, chat, cq.from.id, origin);
  }
  const deck = await loadDeck(env, cq.from.id);
  const s = deck.session;
  if (action === "pc") { // разбор целиком — отдельным сообщением, в любой момент
    const word = deckWord(id);
    await done();
    return word && tg(env, "sendMessage", {
      chat_id: chat, parse_mode: "HTML", text: `📖 ${word.card}`, link_preview_options: { is_disabled: true },
    });
  }
  if (action === "pf") { // «Дальше» после ошибки
    if (!s || !s.waiting) return done("Эта карточка уже пройдена");
    await done();
    if (currentItem(deck)) return sendDeckCard(env, chat, deck, origin);
    deck.session = null;
    await saveDeck(env, cq.from.id, deck);
    return finishDeck(env, chat, deck, s);
  }
  const item = currentItem(deck);
  const word = deckWord(id);
  const mode = action === "pl" ? "l" : "r";
  if (!item || item[0] !== mode || item[1] !== id || !word) return done("Эта карточка уже пройдена");
  const today = dayNumber(new Date(), env.TIMEZONE);
  const header = deckHeader(deck, mode);
  if (action === "pl") { // разбор прочитан
    const more = learn(deck, id, today);
    if (!more) deck.session = null;
    await saveDeck(env, cq.from.id, deck);
    await done();
    await tg(env, "editMessageReplyMarkup", {
      chat_id: chat, message_id: cq.message.message_id, reply_markup: keyboard([]),
    });
    return more ? sendDeckCard(env, chat, deck, origin) : finishDeck(env, chat, deck, s);
  }
  if (action === "ps") { // показать оборот (когда вариантов нет)
    await done();
    return editCard(env, cq.message, deckBack(word, header), keyboard([recallButtons(id), fullButton(id)]));
  }
  let known;
  let chosen = null;
  if (action === "pa") { // выбран вариант перевода
    chosen = deckWord((s.opts || [])[Number(choice)]);
    if (!chosen) return done("Эта карточка уже пройдена");
    known = chosen.id === id;
  } else if (action === "py" || action === "pn") {
    known = action === "py";
  } else {
    return done();
  }
  const { more, retry } = recall(deck, id, known, today);
  const later = retry ? "Слово вернётся через пару карточек." : "Повторим в следующий раз.";
  if (!known && chosen) { // ошибка: показываем правильный ответ и ждём «Дальше», чтобы успеть прочитать
    s.waiting = true;
    await saveDeck(env, cq.from.id, deck);
    await done("❌ Неверно");
    return editCard(env, cq.message, `${deckBack(word, header)}\n\n❌ Вы выбрали: ${esc(chosen.ru)} — ` +
      `это <b>${esc(chosen.word)}</b>. ${later}`, keyboard([[{ text: "➡️ Дальше", callback_data: "pf" }], fullButton(id)]));
  }
  if (!more) deck.session = null;
  await saveDeck(env, cq.from.id, deck);
  await done(known && chosen ? "✅ Верно!" : undefined);
  const mark = known ? (chosen ? "✅ Верно!" : "✅ Помню") : `🔁 Не помню. ${later}`;
  await editCard(env, cq.message, `${deckBack(word, header)}\n\n${mark}`, keyboard([fullButton(id)]));
  return more ? sendDeckCard(env, chat, deck, origin) : finishDeck(env, chat, deck, s);
}

async function finishDeck(env, chat, deck, s) {
  const today = dayNumber(new Date(), env.TIMEZONE);
  const p = deckProgress(deck, DECK, today);
  const next = p.due ? `Ещё пора повторить: ${p.due}.`
    : !p.fresh ? "Новые слова в колоде закончились — пришлите Claude ещё список."
      : freshLeft(deck, today, perDay(env)) ? "" : "Новые слова — завтра. ¡Hasta mañana!";
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: `🎉 <b>Готово!</b> ` + (s && s.learned ? `Новых слов: ${s.learned}. ` : "") +
      (s && s.right + s.wrong ? `Верно: ${s.right}, ошибок: ${s.wrong}.` : "") + `\n\n${deckSummary(p)}` + (next ? `\n\n${next}` : ""),
    reply_markup: p.due ? keyboard([[{ text: "🔁 Повторить ещё", callback_data: "pgo" }]]) : undefined,
  });
}

function deckSummary(p) {
  return `📒 Слов в колоде: ${p.total}\n` +
    `🌱 Учите сейчас: ${p.seen - p.learned}\n` +
    `🏆 Выучено: ${p.learned} — помните неделю и дольше\n` +
    `🆕 Ещё не начинали: ${p.fresh}`;
}

// Каждый день в WORDS_HOUR: сколько сегодня новых слов и повторений. Если заниматься нечем, молчим;
// о том, что новые слова кончились, говорим один раз (до пополнения колоды).
export async function sendDeckDaily(env) {
  if (!env.ADMIN_CHAT_ID || !DECK.length) return;
  const deck = await loadDeck(env, env.ADMIN_CHAT_ID);
  const today = dayNumber(new Date(), env.TIMEZONE);
  const p = deckProgress(deck, DECK, today);
  const fresh = Math.min(freshLeft(deck, today, perDay(env)), p.fresh);
  if (!fresh && !p.due) {
    if (p.fresh || deck.toldEmpty === DECK.length) return;
    deck.toldEmpty = DECK.length;
    await saveDeck(env, env.ADMIN_CHAT_ID, deck);
    return tg(env, "sendMessage", {
      chat_id: env.ADMIN_CHAT_ID,
      text: "📒 Все слова из колоды уже в работе, сегодня повторять нечего. Пришлите Claude новый список слов.",
    });
  }
  const minutes = Math.max(3, Math.round(fresh * 1.5 + p.due * 0.3));
  const last = p.fresh && p.fresh === fresh ? "\n\n⚠️ Это последние новые слова в колоде — пришлите Claude ещё список." : "";
  return tg(env, "sendMessage", {
    chat_id: env.ADMIN_CHAT_ID,
    parse_mode: "HTML",
    text: "☀️ <b>Мои слова на сегодня</b>\n\n" +
      [fresh && `🆕 Новых слов: ${fresh}`, p.due && `🔁 Повторить: ${p.due}`].filter(Boolean).join("\n") +
      `\n\nЭто примерно ${minutes} мин.${last}`,
    reply_markup: keyboard([[{ text: "▶️ Начать", callback_data: "pgo" }]]),
  });
}

async function loadDeck(env, userId) {
  return (await env.SRS.get(`deck:${userId}`, "json")) || newDeck();
}

function saveDeck(env, userId, deck) {
  return env.SRS.put(`deck:${userId}`, JSON.stringify(deck));
}

// ---------------------------------------------------------------- данные

// Слова только из уроков, которые уже вышли в канал: список берём из state/state.json на GitHub.
export async function availableWords(env) {
  const url = `https://raw.githubusercontent.com/${env.GITHUB_REPO}/${env.GITHUB_BRANCH}/state/state.json`;
  try {
    const resp = await fetch(url, { cf: { cacheTtl: 300, cacheEverything: true } });
    const state = await resp.json();
    const published = new Set((state.published || []).map((p) => p.id));
    return WORDS.filter((w) => published.has(w.lesson));
  } catch (err) {
    console.error("state.json", err);
    return [];
  }
}

async function loadUser(env, userId) {
  return (await env.SRS.get(`user:${userId}`, "json")) || newUser();
}

function saveUser(env, userId, user) {
  return env.SRS.put(`user:${userId}`, JSON.stringify(user));
}
