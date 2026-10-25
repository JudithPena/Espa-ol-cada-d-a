import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import DECK from "../data/mywords.json" with { type: "json" };
import WORDS from "../data/words.json" with { type: "json" };
import bot from "../src/index.js";

let calls;
let kv;
const env = {
  TELEGRAM_BOT_TOKEN: "T", WEBHOOK_SECRET: "S", GITHUB_TOKEN: "G", ADMIN_CHAT_ID: "1",
  GITHUB_REPO: "o/r", GITHUB_BRANCH: "main", PUBLISH_WORKFLOW: "publish.yml",
  PUBLISH_HOURS: "9,15", TIMEZONE: "Europe/Kyiv", REMIND_DAYS: "3,6", REMIND_HOUR: "19",
};
const first = WORDS[0];

beforeEach(() => {
  calls = [];
  kv = new Map();
  env.SRS = {
    get: async (k, type) => (kv.has(k) ? (type === "json" ? JSON.parse(kv.get(k)) : kv.get(k)) : null),
    put: async (k, v) => { kv.set(k, v); },
  };
  globalThis.fetch = async (url, init = {}) => {
    url = String(url);
    if (url.includes("raw.githubusercontent.com")) {
      return Response.json({ published: [{ id: first.lesson }] });
    }
    if (url.includes("api.github.com")) {
      calls.push({ method: "dispatch", url, body: JSON.parse(init.body) });
      return new Response(null, { status: 204 });
    }
    const method = url.split("/").pop();
    const body = JSON.parse(init.body);
    calls.push({ method, body });
    const result = method === "sendAudio" ? { audio: { file_id: "F" }, message_id: 7 } : { message_id: 7 };
    return Response.json({ ok: true, result });
  };
});

const post = (update, secret = "S") => bot.fetch(new Request("https://bot.example/telegram", {
  method: "POST", headers: { "X-Telegram-Bot-Api-Secret-Token": secret }, body: JSON.stringify(update),
}), env, {});
const message = (text) => ({ message: { text, chat: { id: 5, type: "private" }, from: { id: 9 } } });
const press = (data, audio = true) => ({
  callback_query: {
    id: "q", data, from: { id: 9 },
    message: audio ? { chat: { id: 5 }, message_id: 7, audio: {}, caption: "…" } : { chat: { id: 5 }, message_id: 7, text: "…" },
  },
});

test("чужие запросы без секрета не принимаются", async () => {
  assert.equal((await post(message("/repaso"), "wrong")).status, 403);
  assert.equal(calls.length, 0);
});

test("повторение: карточка, перевод, ответ и итог — только слова вышедших уроков", async () => {
  await post(message("/repaso"));
  const card = calls.at(-1);
  const lessonWords = WORDS.filter((w) => w.lesson === first.lesson);
  assert.equal(card.method, first.audio ? "sendAudio" : "sendMessage");
  if (first.audio) assert.equal(card.body.title, first.es); // в плеере — слово, а не имя файла
  assert.match(card.body.caption || card.body.text, new RegExp(`1/${Math.min(5, lessonWords.length)}`));
  assert.ok(!(card.body.caption || card.body.text).includes(first.ru), "перевод спрятан");

  await post(press(`s:${first.id}`, !!first.audio));
  const shown = calls.at(-1);
  assert.equal(shown.method, first.audio ? "editMessageCaption" : "editMessageText");
  assert.ok((shown.body.caption || shown.body.text).includes(first.ru));

  for (const w of lessonWords.slice(0, 5)) await post(press(`y:${w.id}`, !!w.audio));
  assert.match(calls.at(-1).body.text, /Готово!/);
  assert.match(calls.at(-1).body.text, new RegExp(`Учите сейчас: ${Math.min(5, lessonWords.length)}`));
  const user = JSON.parse(kv.get("user:9"));
  assert.equal(user.session, null);
  assert.deepEqual(user.cards[first.id][0], 1);
});

test("ссылка из урока: сначала слова урока, потом прошлые слова, которые пора повторить", async () => {
  const lessonId = WORDS[WORDS.length - 1].lesson; // урок ещё не вышел — по ссылке слова всё равно есть
  const own = WORDS.filter((w) => w.lesson === lessonId);
  kv.set("user:9", JSON.stringify({ cards: { [first.id]: [1, 0] }, session: null })); // слово из вышедшего урока, срок подошёл
  await post(message(`/start l-${lessonId.replace(/[^A-Za-z0-9_-]/g, "-")}`));
  const card = calls.at(-1);
  assert.match(card.body.caption || card.body.text, new RegExp(`1/${Math.min(10, own.length + 1)}`));
  assert.ok((card.body.caption || card.body.text).includes(own[0].es.replace(/[<>&]/g, "")));
  assert.equal(JSON.parse(kv.get("user:9")).session.queue.at(-1), first.id);
  await post(message("/start repaso")); // обычная ссылка — обычное повторение
  assert.ok((calls.at(-1).body.caption || calls.at(-1).body.text).includes(first.es));
});

test("старая кнопка не сбивает повторение", async () => {
  await post(message("/repaso"));
  await post(press("y:нет-такого"));
  assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
});

test("публикация запускается только в часы PUBLISH_HOURS по Киеву", async () => {
  const run = async (iso) => {
    const waits = [];
    await bot.scheduled({ scheduledTime: Date.parse(iso) }, env, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
  };
  await run("2026-10-23T05:00:00Z"); // 08:00 по Киеву
  assert.equal(calls.length, 0);
  await run("2026-10-23T06:00:00Z"); // 09:00
  await run("2026-10-27T13:00:00Z"); // 15:00 по зимнему времени
  assert.deepEqual(calls.map((c) => c.method), ["dispatch", "dispatch"]);
  assert.match(calls[0].url, /repos\/o\/r\/actions\/workflows\/publish\.yml\/dispatches$/);
  assert.deepEqual(calls[0].body, { ref: "main" });
});

test("карточка с озвучкой: аудио с названием слова, перевод — в подписи", async () => {
  const saved = first.audio;
  first.audio = "a.mp3"; // те же объекты, что и в боте
  try {
    await post(message("/repaso"));
    const card = calls.at(-1);
    assert.equal(card.method, "sendAudio");
    assert.equal(card.body.audio, "https://bot.example/audio/a.mp3");
    assert.equal(card.body.title, first.es);
    assert.equal(kv.get("audio:a.mp3"), "F"); // дальше Telegram берёт файл из своего кеша
    await post(press(`s:${first.id}`, true));
    assert.equal(calls.at(-1).method, "editMessageCaption");
    assert.ok(calls.at(-1).body.caption.includes(first.ru));
  } finally {
    first.audio = saved;
  }
});

test("по средам и субботам в 19:00 бот сам предлагает повторить слова", async () => {
  await post(message("/start")); // бот запомнил ученика
  kv.set("user:10", JSON.stringify({ cards: {}, session: null, noRemind: true }));
  kv.set("users", JSON.stringify([9, 10]));
  calls = [];
  const run = async (iso) => {
    const waits = [];
    await bot.scheduled({ scheduledTime: Date.parse(iso) }, env, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
  };
  await run("2026-10-27T17:00:00Z"); // вторник, 19:00 по Киеву
  assert.equal(calls.length, 0);
  await run("2026-10-28T17:00:00Z"); // среда, 19:00 (зимнее время)
  assert.equal(calls.length, 1, "только тому, кто не отключал напоминания");
  assert.equal(calls[0].body.chat_id, 9);
  assert.match(calls[0].body.text, /Время повторить слова/);
  await post(press("off"));
  assert.equal(JSON.parse(kv.get("user:9")).noRemind, true);
  calls = [];
  await run("2026-10-31T17:00:00Z"); // суббота — уже не напоминаем
  assert.equal(calls.length, 0);
});

test("/recordatorio присылает пробное напоминание только автору", async () => {
  await post({ message: { text: "/recordatorio", chat: { id: 1, type: "private" }, from: { id: 1 } } }); // ADMIN_CHAT_ID = 1
  assert.match(calls.at(-1).body.text, /Время повторить слова/);
  assert.equal(calls.at(-1).body.chat_id, 1);
  await post(message("/recordatorio")); // другой ученик — обычное приветствие
  assert.doesNotMatch(calls.at(-1).body.text, /Время повторить/);
});

// ---------------------------------------------------------------- «Мои слова»

const owner = (text) => ({ message: { text, chat: { id: 1, type: "private" }, from: { id: 1 } } });
const ownerPress = (data, text = true) => ({
  callback_query: {
    id: "q", data, from: { id: 1 },
    message: text ? { chat: { id: 1 }, message_id: 8, text: "…" } : { chat: { id: 1 }, message_id: 8, audio: {}, caption: "…" },
  },
});

async function withDeck(words, fn) {
  DECK.push(...words);
  try {
    await fn();
  } finally {
    DECK.length = 0;
  }
}

const sample = (id, extra = {}) => ({
  id, word: `palabra ${id}`, lang: "es", ru: `слово ${id}`, ipa: "/paˈlaβɾa/",
  ex: ["Una palabra.", "Одно слово."], card: `<b>palabra ${id}</b> — разбор`, audio: "", ...extra,
});

test("«Мои слова» только у автора: другим — обычное приветствие", async () => {
  await withDeck([sample("a")], async () => {
    await post(message("/palabras"));
    assert.doesNotMatch(calls.at(-1).body.text, /Мои слова/);
    assert.equal(kv.has("deck:9"), false);
    await post(press("pgo"));
    assert.equal(kv.has("deck:9"), false);
  });
});

test("«Мои слова»: разбор нового слова → «Дальше» → проверка → итог", async () => {
  await withDeck([sample("a"), sample("b")], async () => {
    await post(owner("/palabras"));
    assert.match(calls.at(-2).body.text, /Новых слов: 2/);
    const card = calls.at(-1);
    assert.equal(card.method, "sendMessage");
    assert.match(card.body.text, /🆕 1\/4[\s\S]*разбор/);
    assert.equal(card.body.reply_markup.inline_keyboard[0][0].callback_data, "pl:a");

    await post(ownerPress("pl:a"));
    assert.equal(JSON.parse(kv.get("deck:1")).fresh, 1);
    await post(ownerPress("pl:a")); // повторное нажатие ничего не ломает
    assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
    await post(ownerPress("pl:b"));
    const front = calls.at(-1);
    assert.match(front.body.text, /🔁 3\/4[\s\S]*palabra a/);
    assert.ok(!front.body.text.includes("слово a"), "значение спрятано");

    await post(ownerPress("ps:a"));
    assert.equal(calls.at(-1).method, "editMessageText");
    assert.match(calls.at(-1).body.text, /слово a/);
    await post(ownerPress("pc:a")); // весь разбор отдельным сообщением
    assert.match(calls.at(-1).body.text, /разбор/);
    await post(ownerPress("py:a:c"));
    await post(ownerPress("py:b"));
    const end = calls.at(-1);
    assert.match(end.body.text, /Готово![\s\S]*Новых слов: 2[\s\S]*Помню: 2/);
    assert.match(end.body.text, /Новые слова в колоде закончились/);
    const deck = JSON.parse(kv.get("deck:1"));
    assert.equal(deck.session, null);
    assert.equal(deck.cards.a[0], 1);
  });
});

test("«Мои слова»: каждый день в WORDS_HOUR бот сам зовёт заниматься", async () => {
  const run = async (iso) => {
    const waits = [];
    await bot.scheduled({ scheduledTime: Date.parse(iso) }, { ...env, WORDS_HOUR: "8" }, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
  };
  await withDeck([sample("a"), sample("b")], async () => {
    await run("2026-10-27T06:00:00Z"); // 08:00 по Киеву
    assert.equal(calls.length, 1);
    assert.equal(calls[0].body.chat_id, "1");
    assert.match(calls[0].body.text, /Новых слов: 2[\s\S]*последние новые слова/);
    assert.equal(calls[0].body.reply_markup.inline_keyboard[0][0].callback_data, "pgo");
    calls = [];
    await run("2026-10-27T07:00:00Z"); // 09:00 — уже не зовёт (только публикация)
    assert.deepEqual(calls.map((c) => c.method), ["dispatch"]);
  });
});
