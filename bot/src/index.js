// Бот курса на Cloudflare Workers.
//  • По расписанию (каждый час) в часы PUBLISH_HOURS по Киеву запускает на GitHub публикацию урока —
//    у Cloudflare расписание точное, а cron в GitHub Actions опаздывает на несколько часов.
//    Так же в свой час выпускает в канал разборы видео (publish_at в content/videos/ → data/videos.json).
//  • Отвечает в личке: /repaso — слова из вышедших уроков: карточка нового слова, потом выбор перевода
//    (занятие — deck.js, интервалы — srs.js), /progreso — сколько слов выучено, /id — номер чата.
//  • В дни REMIND_DAYS в REMIND_HOUR по Киеву сам предлагает в личке повторить слова
//    всем, кто уже писал боту (кроме тех, кто нажал «Не напоминать»).
//  • «Мои слова» — личная колода автора (только чат ADMIN_CHAT_ID): /palabras — разборы новых слов
//    и повторение, каждый день в WORDS_HOURS (утром и вечером) по Киеву бот сам зовёт заниматься (deck.js).
// Слова — bot/data/words.json и bot/data/mywords.json (python -m espanol bot-data), озвучка — bot/public/audio/.
// Прогресс каждого ученика хранится в KV (binding SRS).

import DECK from "../data/mywords.json" with { type: "json" };
import GALYA from "../data/mywords_galya.json" with { type: "json" };
import VIDEOS from "../data/videos.json" with { type: "json" };
import WORDS from "../data/words.json" with { type: "json" };
import {
  choices, currentItem, deckProgress, freshLeft, learn, newDeck, NEW_PER_DAY, recall, startDeckSession, startSession,
  studyQueue,
} from "./deck.js";
import {
  dayNumber, localHour, localWeekday, NEW_PER_SESSION, newUser, progress, SESSION_SIZE,
} from "./srs.js";

const BY_ID = new Map(WORDS.map((w) => [w.id, w]));
// Личные колоды: у автора (ADMIN_CHAT_ID) и у Гали (GALYA_CHAT_ID), у каждой свой прогресс в KV и свои слова.
// Колоды небольшие, тесты дополняют их на ходу.

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
    ctx.waitUntil(publishVideos(env, now));
    if (hour === Number(env.REMIND_HOUR) && numbers(env.REMIND_DAYS).includes(localWeekday(now, env.TIMEZONE))) {
      ctx.waitUntil(sendReminders(env));
    }
    if (numbers(env.WORDS_HOURS).includes(hour)) ctx.waitUntil(sendDeckDaily(env, now));
  },
};

const numbers = (list) => String(list || "").split(",").map((n) => n.trim()).filter(Boolean).map(Number);

// ---------------------------------------------------------------- публикация

export function dispatchPublish(env) {
  return dispatch(env, env.PUBLISH_WORKFLOW, {}, "публикацию урока");
}

// Разборы видео по расписанию: в час publish_at бот запускает workflow «Разбор видео» в канал. Если Cloudflare
// этот час пропустил, разбор выйдет в следующий, но не позже VIDEO_LATE_HOURS. Что разбор уже запущен, бот помнит в KV.
const VIDEO_LATE_HOURS = 3;

export async function publishVideos(env, now = new Date(), videos = VIDEOS) {
  for (const v of videos) {
    const late = now.getTime() - Date.parse(v.at);
    if (late < 0 || late >= VIDEO_LATE_HOURS * 3600 * 1000) continue;
    const key = `video-sent:${v.number}`;
    if (await env.SRS.get(key)) continue;
    const inputs = { video: String(v.number), target: "канал" };
    if (!(await dispatch(env, env.VIDEO_WORKFLOW || "video.yml", inputs, `разбор видео №${v.number}`))) continue;
    await env.SRS.put(key, now.toISOString());
    if (env.ADMIN_CHAT_ID) {
      await tg(env, "sendMessage", {
        chat_id: env.ADMIN_CHAT_ID,
        text: `🎬 Разбор видео №${v.number} «${v.title}» уходит в канал, через пару минут он там появится.`,
      });
    }
  }
}

async function dispatch(env, workflow, inputs, what) {
  const api = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`;
  const resp = await fetch(api, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "espanol-cada-dia-bot",
    },
    body: JSON.stringify(Object.keys(inputs).length ? { ref: env.GITHUB_BRANCH, inputs } : { ref: env.GITHUB_BRANCH }),
  });
  if (resp.status === 204) return true;
  const text = (await resp.text()).slice(0, 300);
  console.error("dispatch failed", workflow, resp.status, text);
  if (env.ADMIN_CHAT_ID) {
    await tg(env, "sendMessage", {
      chat_id: env.ADMIN_CHAT_ID,
      text: `⚠️ Не смог запустить ${what} на GitHub (ответ ${resp.status}). ` +
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
const START_BUTTON = keyboard([[{ text: "🔁 Повторить слова", callback_data: "cgo" }]]);

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
  const mine = deckBook(env, msg.from.id);
  if (mine && (cmd === "/palabras" || (cmd === "/start" && param === "palabras"))) {
    return startStudy(mine, env, chat, msg.from.id, origin);
  }
  // Ссылки из уроков: t.me/бот?start=l-<урок> — слова этого урока, ?start=repaso — обычное повторение.
  if (cmd === "/start" && param.startsWith("l-")) {
    return startStudy(BOOKS.c, env, chat, msg.from.id, origin, param.slice(2));
  }
  if (cmd === "/repaso" || (cmd === "/start" && param === "repaso")) {
    return startStudy(BOOKS.c, env, chat, msg.from.id, origin);
  }
  if (cmd === "/progreso") return sendProgress(env, chat, msg.from.id);
  if (cmd === "/recordatorio" && owner) { // проверка для автора: так выглядит напоминание по средам и субботам
    return sendReminder(env, msg.from.id, await loadUser(env, msg.from.id), await availableWords(env), true);
  }
  if (cmd === "/id") {
    return tg(env, "sendMessage", { chat_id: chat, parse_mode: "HTML", text: `Номер этого чата: <code>${chat}</code>` });
  }
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: "¡Hola! 👋 Я повторяю с вами слова из уроков канала <b>Español cada día</b>.\n\n" +
      "Новое слово я сначала показываю карточкой: как читается, что значит, примеры. " +
      "Потом проверяю: вы выбираете перевод из нескольких вариантов. " +
      "Если ответ верный, слово вернётся через несколько дней, а если нет — повторим его ещё раз.\n\n" +
      "По средам и субботам вечером я сам напомню, если есть что повторить.\n\n" +
      "/repaso — повторить слова\n/progreso — сколько слов уже выучено" +
      (mine ? "\n/palabras — ваши слова: разборы новых и повторение" : ""),
    reply_markup: START_BUTTON,
  });
}

async function handleCallback(cq, env, origin) {
  const [action] = String(cq.data || "").split(":");
  if (action.startsWith("c")) return handleStudyCallback(BOOKS.c, cq, env, origin);
  const mine = deckBook(env, cq.from.id); // кнопки колоды: у автора «p…», у Гали «w…»
  if (mine && action.startsWith(mine.id)) return handleStudyCallback(mine, cq, env, origin);
  if (action === "go") { // кнопки из старых сообщений
    await tg(env, "answerCallbackQuery", { callback_query_id: cq.id });
    return startStudy(BOOKS.c, env, cq.message.chat.id, cq.from.id, origin);
  }
  if (action === "off" || action === "on") { // напоминания по средам и субботам
    const user = await loadUser(env, cq.from.id);
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
  // кнопки «Показать перевод» / «Помню» из повторения старого формата
  return tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text: "Повторение обновилось — начните заново: /repaso" });
}

// ---------------------------------------------------------------- колоды

// Две колоды с одним и тем же занятием (deck.js). В кнопках — буква колоды и действие:
// l — разбор прочитан, a — выбран вариант, s — показать оборот, y/n — помню / не помню, f — «Дальше» после ошибки,
// c — карточка целиком, go — начать занятие.
const BOOKS = {
  c: { // слова вышедших уроков курса — все ученики
    id: "c",
    command: "/repaso",
    title: "🔁 <b>Повторение слов</b>",
    fullLabel: "📖 Карточка",
    find: (id) => BY_ID.get(id),
    words: (env) => availableWords(env),
    load: (env, userId) => loadUser(env, userId),
    save: (env, userId, state) => saveUser(env, userId, state),
    async queue(env, state, words, today, lesson) {
      const own = lesson ? WORDS.filter((w) => w.lesson.replace(/[^A-Za-z0-9_-]/g, "-") === lesson) : [];
      if (own.length) { // сначала слова урока, потом — прошлые слова, которые пора повторить
        const first = own.slice(0, SESSION_SIZE);
        return studyQueue(state, words, today, { first, reviews: SESSION_SIZE - first.length });
      }
      const due = words.filter((w) => state.cards[w.id] && state.cards[w.id][1] <= today).length;
      const fresh = Math.max(0, Math.min(NEW_PER_SESSION, SESSION_SIZE - due));
      return studyQueue(state, words, today, { fresh, reviews: SESSION_SIZE });
    },
    empty: (env, state, words) => words.length
      ? "👏 Сейчас повторять нечего: все слова повторены, а новые появятся с новыми уроками. Приходите завтра!"
      : "Пока в канале нет уроков со словами.",
    finish(env, state, words, today) {
      const p = progress(state, words, today);
      return {
        text: `${summary(p)}\n\n` + (p.due ? `Ещё пора повторить сегодня: ${p.due}.`
          : p.fresh ? "Всё, что было на сегодня, повторено. Можно взять ещё новых слов или вернуться завтра."
            : "На сегодня всё повторено, приходите завтра."),
        button: p.due ? "🔁 Повторить ещё" : p.fresh ? "🆕 Ещё новые слова" : "",
      };
    },
  },
  p: deckBookOf("p", () => DECK, "Пришлите Claude"), // «Мои слова» автора
  w: deckBookOf("w", () => GALYA, "Передайте автору бота"), // колода Гали
};

// «Мои слова»: личная колода одного ученика (автора или Гали). id — буква кнопок, words — слова колоды,
// ask — кому писать, когда слова кончились.
function deckBookOf(id, words, ask) {
  return {
    id,
    ask,
    command: "/palabras",
    title: "📒 <b>Мои слова</b>",
    fullLabel: "📖 Весь разбор",
    find: (wordId) => words().find((w) => w.id === wordId),
    words: async () => words(),
    load: (env, userId) => loadDeck(env, userId),
    save: (env, userId, state) => saveDeck(env, userId, state),
    queue: (env, state, list, today) => startDeckSession(state, list, today, perDay(env), deckShifts(env)) ? state.session.queue : [],
    empty(env, state, list, today) {
      const p = deckProgress(state, list, today);
      return !list.length ? `В колоде пока нет слов. ${ask} список слов — к каждому будет написан разбор.`
        : p.fresh ? `👏 Пока всё: ${laterShift(env) ? `следующие новые слова — в ${laterShift(env)}:00` : "новые слова будут завтра"}, а повторять пока нечего.`
          : `👏 Всё повторено, а новые слова в колоде закончились. ${ask} ещё список.`;
    },
    finish(env, state, list, today) {
      const p = deckProgress(state, list, today);
      const next = p.due ? `Ещё пора повторить: ${p.due}.`
        : !p.fresh ? `Новые слова в колоде закончились. ${ask} ещё список.`
          : freshLeft(state, today, perDay(env), deckShifts(env)) ? "" : laterShift(env) ? `Следующие новые слова — в ${laterShift(env)}:00.` : "Новые слова — завтра. ¡Hasta mañana!";
      return { text: deckSummary(p) + (next ? `\n\n${next}` : ""), button: p.due ? "🔁 Повторить ещё" : "" };
    },
  };
}

async function startStudy(book, env, chat, userId, origin, lesson = "") {
  const state = await book.load(env, userId);
  const today = dayNumber(new Date(), env.TIMEZONE);
  if (!lesson && state.session && state.session.day === today && currentItem(state)) { // занятие уже идёт — продолжаем
    return sendStudyCard(book, env, chat, userId, state, origin);
  }
  const words = await book.words(env);
  const s = startSession(state, await book.queue(env, state, words, today, lesson), today);
  await book.save(env, userId, state);
  if (!s) return tg(env, "sendMessage", { chat_id: chat, text: book.empty(env, state, words, today) });
  const fresh = s.queue.filter((q) => q.startsWith("l:")).length;
  const due = s.queue.length - 2 * fresh;
  await tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: `${book.title}\n\n` +
      [fresh && `🆕 Новых слов: ${fresh} — сначала прочитайте карточки, в конце проверим`,
        due && `🔁 Повторить: ${due}`].filter(Boolean).join("\n"),
  });
  return sendStudyCard(book, env, chat, userId, state, origin);
}

// Свой счёт у карточек новых слов и у повторения (с проверкой новых): «Новое слово 3/10», «Повторение 1/12».
function studyHeader(state, mode) {
  const s = state.session;
  const mine = (q) => q.startsWith(`${mode}:`);
  const n = s.queue.slice(0, s.pos + 1).filter(mine).length;
  return `${mode === "l" ? "🆕 Новое слово" : "🔁 Повторение"} ${n}/${s.queue.filter(mine).length}`;
}

function studyBack(word, header) {
  let text = `${header}\n\n${word.emoji ? `${esc(word.emoji)} ` : ""}<b>${esc(word.word)}</b> ${esc(word.ipa)}\n— ${esc(word.ru)}`;
  if (word.ex) text += `\n\n<i>${esc(word.ex[0])}</i> — ${esc(word.ex[1])}`;
  return text;
}

async function sendStudyCard(book, env, chat, userId, state, origin) {
  const [mode, id] = currentItem(state);
  const word = book.find(id);
  const s = state.session;
  const b = book.id;
  if (!word) { // слово убрали, пока шло занятие
    state.session = null;
    await book.save(env, userId, state);
    return tg(env, "sendMessage", { chat_id: chat, text: `Слова обновились — начните заново: ${book.command}` });
  }
  const header = studyHeader(state, mode);
  if (mode === "l") { // новое слово: сначала озвучка, потом карточка целиком
    if (word.audio) await sendAudio(env, chat, origin, word.audio, word.word, `${header} · <b>${esc(word.word)}</b>`);
    return tg(env, "sendMessage", {
      chat_id: chat, parse_mode: "HTML", text: `${header}\n\n${word.card}`,
      link_preview_options: { is_disabled: true },
      reply_markup: keyboard([[{ text: "➡️ Дальше", callback_data: `${b}l:${id}` }]]),
    });
  }
  // Повторение: слово и варианты перевода — бот сам видит, верно ли. Варианты помним до ответа.
  s.opts = choices(word, await book.words(env), Number(env.CHOICES) || undefined);
  s.waiting = false;
  await book.save(env, userId, state);
  const text = `${header}\n\n<b>${esc(word.word)}</b>\n\n` +
    (s.opts.length ? "Выберите перевод:" : "Вспомните значение и откройте карточку.");
  const markup = keyboard(s.opts.length
    ? s.opts.map((opt, k) => [{ text: book.find(opt).ru, callback_data: `${b}a:${id}:${k}` }])
    : [[{ text: "👀 Показать", callback_data: `${b}s:${id}` }]]);
  return (word.audio && await sendAudio(env, chat, origin, word.audio, word.word, text, markup)) ||
    tg(env, "sendMessage", { chat_id: chat, text, parse_mode: "HTML", reply_markup: markup });
}

async function handleStudyCallback(book, cq, env, origin) {
  const chat = cq.message && cq.message.chat.id;
  const userId = cq.from.id;
  const [data, id, choice] = String(cq.data || "").split(":");
  const action = data.slice(1);
  const b = book.id;
  const done = (text) => tg(env, "answerCallbackQuery", { callback_query_id: cq.id, text });
  const full = (wordId) => [{ text: book.fullLabel, callback_data: `${b}c:${wordId}` }];
  if (action === "go") {
    await done();
    return startStudy(book, env, chat, userId, origin);
  }
  const state = await book.load(env, userId);
  const s = state.session;
  if (action === "c") { // карточка целиком — отдельным сообщением, в любой момент
    const word = book.find(id);
    await done();
    return word && tg(env, "sendMessage", {
      chat_id: chat, parse_mode: "HTML", text: `📖 ${word.card}`, link_preview_options: { is_disabled: true },
    });
  }
  if (action === "f") { // «Дальше» после ошибки
    if (!s || !s.waiting) return done("Эта карточка уже пройдена");
    await done();
    if (currentItem(state)) return sendStudyCard(book, env, chat, userId, state, origin);
    state.session = null;
    await book.save(env, cq.from.id, state);
    return finishStudy(book, env, chat, state, s);
  }
  const item = currentItem(state);
  const word = book.find(id);
  const mode = action === "l" ? "l" : "r";
  if (!item || item[0] !== mode || item[1] !== id || !word) return done("Эта карточка уже пройдена");
  const today = dayNumber(new Date(), env.TIMEZONE);
  const header = studyHeader(state, mode);
  if (action === "l") { // карточка нового слова прочитана
    const more = learn(state, id, today);
    if (!more) state.session = null;
    await book.save(env, cq.from.id, state);
    await done();
    await tg(env, "editMessageReplyMarkup", {
      chat_id: chat, message_id: cq.message.message_id, reply_markup: keyboard([]),
    });
    return more ? sendStudyCard(book, env, chat, userId, state, origin) : finishStudy(book, env, chat, state, s);
  }
  if (action === "s") { // показать оборот (когда вариантов нет)
    await done();
    return editCard(env, cq.message, studyBack(word, header), keyboard([[
      { text: "✅ Помню", callback_data: `${b}y:${id}` },
      { text: "❌ Не помню", callback_data: `${b}n:${id}` },
    ], full(id)]));
  }
  let known;
  let chosen = null;
  if (action === "a") { // выбран вариант перевода
    chosen = book.find((s.opts || [])[Number(choice)]);
    if (!chosen) return done("Эта карточка уже пройдена");
    known = chosen.id === id;
  } else if (action === "y" || action === "n") {
    known = action === "y";
  } else {
    return done();
  }
  const { more, retry } = recall(state, id, known, today);
  const later = retry ? "Слово вернётся через пару карточек." : "Повторим в следующий раз.";
  if (!known && chosen) { // ошибка: показываем правильный ответ и ждём «Дальше», чтобы успеть прочитать
    s.waiting = true;
    await book.save(env, cq.from.id, state);
    await done("❌ Неверно");
    return editCard(env, cq.message, `${studyBack(word, header)}\n\n❌ Вы выбрали: ${esc(chosen.ru)} — ` +
      `это <b>${esc(chosen.word)}</b>. ${later}`, keyboard([[{ text: "➡️ Дальше", callback_data: `${b}f` }], full(id)]));
  }
  if (!more) state.session = null;
  await book.save(env, cq.from.id, state);
  await done(known && chosen ? "✅ Верно!" : undefined);
  const mark = known ? (chosen ? "✅ Верно!" : "✅ Помню") : `🔁 Не помню. ${later}`;
  await editCard(env, cq.message, `${studyBack(word, header)}\n\n${mark}`, keyboard([full(id)]));
  return more ? sendStudyCard(book, env, chat, userId, state, origin) : finishStudy(book, env, chat, state, s);
}

async function finishStudy(book, env, chat, state, s) {
  const today = dayNumber(new Date(), env.TIMEZONE);
  const { text, button } = book.finish(env, state, await book.words(env), today);
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: `🎉 <b>Готово!</b> ` + (s && s.learned ? `Новых слов: ${s.learned}. ` : "") +
      (s && s.right + s.wrong ? `Верно: ${s.right}, ошибок: ${s.wrong}.` : "") + `\n\n${text}`,
    reply_markup: button ? keyboard([[{ text: button, callback_data: `${book.id}go` }]]) : undefined,
  });
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
      ...(p.due || p.fresh ? [[{ text: "🔁 Повторить слова", callback_data: "cgo" }]] : []),
      [user.noRemind
        ? { text: "🔔 Включить напоминания", callback_data: "on" }
        : { text: "🔕 Не напоминать", callback_data: "off" }],
    ]),
  });
}

// ---------------------------------------------------------------- напоминания

export async function sendReminders(env) {
  const words = await availableWords(env);
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
      [{ text: "🔁 Повторить слова", callback_data: "cgo" }],
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

// Личные колоды есть у автора — его личный чат TELEGRAM_REVIEW_CHAT_ID (ADMIN_CHAT_ID) — и у Гали (GALYA_CHAT_ID).
function isOwner(env, userId) {
  return Boolean(env.ADMIN_CHAT_ID) && String(userId) === String(env.ADMIN_CHAT_ID);
}

// Колода этого человека или null: чужие слова никому не показываем.
function deckBook(env, userId) {
  if (isOwner(env, userId)) return BOOKS.p;
  return env.GALYA_CHAT_ID && String(userId) === String(env.GALYA_CHAT_ID) ? BOOKS.w : null;
}

const perDay = (env) => Number(env.WORDS_PER_DAY) || NEW_PER_DAY;

// Час ближайшей следующей смены сегодня (или 0, если смен больше нет).
function laterShift(env, now = new Date()) {
  const hour = localHour(now, env.TIMEZONE);
  return numbers(env.WORDS_HOURS).find((h) => h > hour) || 0;
}

// Сколько смен «Моих слов» (WORDS_HOURS) уже началось сегодня; до первой — одна, чтобы утром до срока тоже можно было заниматься.
function deckShifts(env, now = new Date()) {
  const hour = localHour(now, env.TIMEZONE);
  return Math.max(1, numbers(env.WORDS_HOURS).filter((h) => h <= hour).length);
}

function deckSummary(p) {
  return `📒 Слов в колоде: ${p.total}\n` +
    `🌱 Учите сейчас: ${p.seen - p.learned}\n` +
    `🏆 Выучено: ${p.learned} — помните неделю и дольше\n` +
    `🆕 Ещё не начинали: ${p.fresh}`;
}

// Каждый день в WORDS_HOURS (утром и вечером): сколько сейчас новых слов и повторений. Если заниматься нечем, молчим;
// о том, что новые слова кончились, говорим один раз (до пополнения колоды).
export async function sendDeckDaily(env, now = new Date()) {
  await sendDeckDailyTo(env, now, env.ADMIN_CHAT_ID, BOOKS.p);
  await sendDeckDailyTo(env, now, env.GALYA_CHAT_ID, BOOKS.w);
}

async function sendDeckDailyTo(env, now, chat, book) {
  const words = await book.words(env);
  if (!chat || !words.length) return;
  const deck = await loadDeck(env, chat);
  const today = dayNumber(new Date(), env.TIMEZONE);
  const p = deckProgress(deck, words, today);
  const shifts = deckShifts(env, now);
  const fresh = Math.min(freshLeft(deck, today, perDay(env), shifts), p.fresh);
  if (!fresh && !p.due) {
    if (p.fresh || deck.toldEmpty === words.length) return;
    deck.toldEmpty = words.length;
    await saveDeck(env, chat, deck);
    return tg(env, "sendMessage", {
      chat_id: chat,
      text: `📒 Все слова из колоды уже в работе, сегодня повторять нечего. ${book.ask} новый список слов.`,
    });
  }
  const minutes = Math.max(3, Math.round(fresh * 1.5 + p.due * 0.3));
  const last = p.fresh && p.fresh === fresh ? `\n\n⚠️ Это последние новые слова в колоде — ${book.ask.toLowerCase()} ещё список.` : "";
  return tg(env, "sendMessage", {
    chat_id: chat,
    parse_mode: "HTML",
    text: `${shifts > 1 ? "🌙" : "☀️"} <b>Мои слова: ${shifts > 1 ? "вечерняя" : "утренняя"} смена</b>\n\n` +
      [fresh && `🆕 Новых слов: ${fresh}`, p.due && `🔁 Повторить: ${p.due}`].filter(Boolean).join("\n") +
      `\n\nЭто примерно ${minutes} мин.${last}`,
    reply_markup: keyboard([[{ text: "▶️ Начать", callback_data: `${book.id}go` }]]),
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
