// Бот курса на Cloudflare Workers.
//  • По расписанию (каждый час) в часы PUBLISH_HOURS по Киеву запускает на GitHub публикацию урока —
//    у Cloudflare расписание точное, а cron в GitHub Actions опаздывает на несколько часов.
//  • Отвечает в личке: /repaso — личные повторения слов из вышедших уроков с кнопками,
//    /progreso — сколько слов выучено, /id — номер чата (для TELEGRAM_REVIEW_CHAT_ID).
// Слова — bot/data/words.json (python -m espanol bot-data), озвучка — bot/public/audio/.
// Прогресс каждого ученика хранится в KV (binding SRS).

import WORDS from "../data/words.json" with { type: "json" };
import { SESSION_SIZE, answer, currentId, dayNumber, localHour, newUser, progress, startSession } from "./srs.js";

const BY_ID = new Map(WORDS.map((w) => [w.id, w]));

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
    const hours = String(env.PUBLISH_HOURS || "").split(",").map((h) => Number(h.trim())).filter((h) => h >= 0);
    if (!hours.includes(localHour(new Date(event.scheduledTime), env.TIMEZONE))) return;
    ctx.waitUntil(dispatchPublish(env));
  },
};

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
  if (update.callback_query) return handleCallback(update.callback_query, env, origin);
  const msg = update.message;
  if (!msg || !msg.chat || msg.chat.type !== "private") return;
  const [command, param = ""] = (msg.text || "").trim().split(/\s+/);
  const cmd = command.split("@")[0].toLowerCase();
  const chat = msg.chat.id;
  // Ссылки из уроков: t.me/бот?start=l-<урок> — слова этого урока, ?start=repaso — обычное повторение.
  if (cmd === "/start" && param.startsWith("l-")) return startRepaso(env, chat, msg.from.id, origin, param.slice(2));
  if (cmd === "/repaso" || (cmd === "/start" && param === "repaso")) return startRepaso(env, chat, msg.from.id, origin);
  if (cmd === "/progreso") return sendProgress(env, chat, msg.from.id);
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
      "/repaso — повторить слова\n/progreso — сколько слов уже выучено",
    reply_markup: START_BUTTON,
  });
}

async function handleCallback(cq, env, origin) {
  const chat = cq.message && cq.message.chat.id;
  const [action, id] = String(cq.data || "").split(":");
  if (action === "go") {
    await tg(env, "answerCallbackQuery", { callback_query_id: cq.id });
    return startRepaso(env, chat, cq.from.id, origin);
  }
  const user = await loadUser(env, cq.from.id);
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
  if (own.length) {
    user.session = { queue: own.slice(0, SESSION_SIZE).map((w) => w.id), pos: 0, retry: [], right: 0, wrong: 0 };
    await saveUser(env, userId, user);
    return sendCard(env, chat, user, origin);
  }
  const words = (await availableWords(env)).filter((w) => BY_ID.has(w.id));
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
  if (word.audio) { // карточка с озвучкой: слово и пример можно сразу послушать
    const cached = await env.SRS.get(`audio:${word.audio}`);
    const sent = await tg(env, "sendAudio", {
      chat_id: chat, audio: cached || `${origin}/audio/${word.audio}`,
      title: word.es, performer: "Español cada día",
      caption: front(word, s), parse_mode: "HTML", reply_markup: markup,
    });
    if (sent.ok) {
      const file = sent.result.audio || sent.result.voice;
      if (!cached && file) await env.SRS.put(`audio:${word.audio}`, file.file_id);
      return sent;
    }
  }
  return tg(env, "sendMessage", { chat_id: chat, text: front(word, s), parse_mode: "HTML", reply_markup: markup });
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
    text: `📊 <b>Ваш прогресс</b>\n\n${summary(p)}\n\nПора повторить сейчас: ${p.due}`,
    reply_markup: p.due || p.fresh ? START_BUTTON : undefined,
  });
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
