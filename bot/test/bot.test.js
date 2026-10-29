import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import DECK from "../data/mywords.json" with { type: "json" };
import GALYA from "../data/mywords_galya.json" with { type: "json" };
import WORDS from "../data/words.json" with { type: "json" };
import bot, { publishVideos } from "../src/index.js";

let calls;
let kv;
const env = {
  TELEGRAM_BOT_TOKEN: "T", WEBHOOK_SECRET: "S", GITHUB_TOKEN: "G", ADMIN_CHAT_ID: "1",
  GITHUB_REPO: "o/r", GITHUB_BRANCH: "main", PUBLISH_WORKFLOW: "publish.yml",
  PUBLISH_HOURS: "9,15", TIMEZONE: "Europe/Kyiv", REMIND_DAYS: "3,6", REMIND_HOUR: "19",
};
const first = WORDS[0];
let published; // уроки, которые «вышли в канал»

beforeEach(() => {
  published = [first.lesson, "start/vowels"];
  calls = [];
  kv = new Map();
  env.SRS = {
    get: async (k, type) => (kv.has(k) ? (type === "json" ? JSON.parse(kv.get(k)) : kv.get(k)) : null),
    put: async (k, v) => { kv.set(k, v); },
  };
  globalThis.fetch = async (url, init = {}) => {
    url = String(url);
    if (url.includes("raw.githubusercontent.com")) {
      return Response.json({ published: published.map((id) => ({ id })) });
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

const buttons = (call) => call.body.reply_markup.inline_keyboard.map((row) => row[0]);
const textOf = (call) => call.body.caption || call.body.text;

test("/repaso: карточка нового слова → «Дальше» → выбор перевода → итог; только слова вышедших уроков", async () => {
  const available = WORDS.filter((w) => published.includes(w.lesson));
  const fresh = available.slice(0, 5);
  await post(message("/repaso"));
  assert.match(calls.find((c) => /Повторение слов/.test(c.body.text || "")).body.text, /Новых слов: 5/);
  const card = calls.at(-1);
  assert.equal(card.method, "sendMessage");
  assert.match(card.body.text, /🆕 Новое слово 1\/5/);
  assert.ok(card.body.text.includes(first.card), "карточка слова целиком");
  assert.equal(buttons(card)[0].callback_data, `cl:${first.id}`);

  for (const w of fresh) await post(press(`cl:${w.id}`, false));
  const front = calls.at(-1);
  assert.match(textOf(front), /🔁 Повторение 1\/5/);
  const options = buttons(front);
  assert.equal(options.length, 4, "перевод и ещё 3 перевода слов вышедших уроков");
  assert.ok(options.every((o) => available.some((w) => w.ru === o.text)));
  for (const w of fresh) {
    const opts = buttons(calls.filter((c) => /Выберите перевод/.test(textOf(c) || "")).at(-1));
    await post(press(opts.find((o) => o.text === w.ru).callback_data, !!w.audio));
  }
  const end = calls.at(-1);
  assert.match(end.body.text, /Готово![\s\S]*Новых слов: 5[\s\S]*Верно: 5[\s\S]*Слов в вышедших уроках: 8/);
  const user = JSON.parse(kv.get("user:9"));
  assert.equal(user.session, null);
  assert.equal(user.cards[first.id][0], 1);
  assert.equal(end.body.reply_markup.inline_keyboard[0][0].callback_data, "cgo", "можно взять ещё новых слов");
});

test("ссылка из урока: сначала слова урока, потом прошлые слова, которые пора повторить", async () => {
  const lessonId = WORDS[WORDS.length - 1].lesson; // урок ещё не вышел — по ссылке слова всё равно есть
  const own = WORDS.filter((w) => w.lesson === lessonId);
  kv.set("user:9", JSON.stringify({ cards: { [first.id]: [1, 0] }, session: null })); // слово из вышедшего урока, срок подошёл
  await post(message(`/start l-${lessonId.replace(/[^A-Za-z0-9_-]/g, "-")}`));
  assert.match(textOf(calls.at(-1)), new RegExp(`🆕 Новое слово 1/${own.length}`));
  assert.ok(textOf(calls.at(-1)).includes(own[0].card));
  const queue = JSON.parse(kv.get("user:9")).session.queue;
  assert.deepEqual(queue, [...own.map((w) => `l:${w.id}`), `r:${first.id}`, ...own.map((w) => `r:${w.id}`)]);
  await post(message("/start repaso")); // обычная ссылка — продолжаем то же занятие
  assert.ok(textOf(calls.at(-1)).includes(own[0].card));
});

test("кнопки старого повторения и чужие кнопки не сбивают занятие", async () => {
  await post(message("/repaso"));
  await post(press("y:нет-такого"));
  assert.match(calls.at(-1).body.text, /Повторение обновилось/);
  await post(press("cl:нет-такого"));
  assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
  await post(press("pgo")); // «Мои слова» — только у автора
  assert.equal(kv.has("deck:9"), false);
});

test("карточка с озвучкой: сначала аудио с названием слова, потом карточка; на повторении — аудио с вариантами", async () => {
  const saved = first.audio;
  first.audio = "a.mp3"; // те же объекты, что и в боте
  try {
    await post(message("/repaso"));
    const audio = calls.at(-2);
    assert.equal(audio.method, "sendAudio");
    assert.equal(audio.body.audio, "https://bot.example/audio/a.mp3");
    assert.equal(audio.body.title, first.es);
    assert.equal(kv.get("audio:a.mp3"), "F"); // дальше Telegram берёт файл из своего кеша
    const fresh = WORDS.filter((w) => published.includes(w.lesson)).slice(0, 5);
    for (const w of fresh) await post(press(`cl:${w.id}`, false));
    const front = calls.at(-1);
    assert.equal(front.method, "sendAudio");
    assert.equal(front.body.audio, "F");
    assert.match(front.body.caption, /Выберите перевод/);
  } finally {
    first.audio = saved;
  }
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

test("разбор видео выходит в канал в час publish_at, один раз; пропущенный час — не позже чем через 3 часа", async () => {
  const videos = [{ number: 6, title: "Обувной магазин", at: "2026-10-30T16:00:00Z" }]; // 18:00 по Киеву
  const run = (iso) => publishVideos(env, new Date(iso), videos);
  await run("2026-10-30T15:00:00Z");
  assert.equal(calls.length, 0, "раньше срока — ничего");
  await run("2026-10-30T16:00:00Z");
  assert.deepEqual(calls.map((c) => c.method), ["dispatch", "sendMessage"]);
  assert.match(calls[0].url, /workflows\/video\.yml\/dispatches$/);
  assert.deepEqual(calls[0].body, { ref: "main", inputs: { video: "6", target: "канал" } });
  assert.match(calls[1].body.text, /№6 «Обувной магазин»/);
  calls = [];
  await run("2026-10-30T17:00:00Z");
  assert.equal(calls.length, 0, "второй раз не выпускает");

  kv.clear();
  await run("2026-10-30T19:00:00Z");
  assert.equal(calls.length, 0, "на 3 часа позже — уже не выпускает");
  await run("2026-10-30T18:00:00Z");
  assert.equal(calls[0].method, "dispatch", "через 2 часа после срока — ещё выпускает");
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

const saved = []; // настоящая колода Гали (её выгружает bot-data) на время теста убираем
const galya = (text) => ({ message: { text, chat: { id: 5, type: "private" }, from: { id: 5 } } });

test("колода Гали: свои слова и свой прогресс, слов автора она не видит", async () => {
  DECK.push(sample("a", { word: "secreto" }));
  saved.push(...GALYA.splice(0));
  GALYA.push(sample("g", { word: "hola" }));
  env.GALYA_CHAT_ID = "5";
  try {
    await post(galya("/palabras"));
    assert.match(calls.at(-1).body.text, /🆕 Новое слово 1\/1[\s\S]*palabra g/);
    assert.equal(calls.at(-1).body.reply_markup.inline_keyboard[0][0].callback_data, "wl:g");
    await post({ callback_query: { id: "q", data: "wl:g", from: { id: 5 }, message: { chat: { id: 5 }, message_id: 8, text: "…" } } });
    assert.equal(JSON.parse(kv.get("deck:5")).cards.g[0], 0);
    assert.equal(kv.has("deck:1"), false, "прогресс автора не затронут");
    await post({ callback_query: { id: "q", data: "pl:a", from: { id: 5 }, message: { chat: { id: 5 }, message_id: 8, text: "…" } } });
    assert.equal(JSON.parse(kv.get("deck:5")).cards.a, undefined, "кнопки колоды автора Гале не подходят");
  } finally {
    delete env.GALYA_CHAT_ID;
    DECK.length = 0;
    GALYA.length = 0;
    GALYA.push(...saved.splice(0));
  }
});

test("колода Гали: без GALYA_CHAT_ID /palabras никому, кроме автора, не открывается", async () => {
  saved.push(...GALYA.splice(0));
  GALYA.push(sample("g"));
  try {
    await post(galya("/palabras"));
    assert.doesNotMatch(calls.at(-1).body.text, /Мои слова/);
    assert.equal(kv.has("deck:5"), false);
  } finally {
    GALYA.length = 0;
    GALYA.push(...saved.splice(0));
  }
});

test("«Мои слова»: разбор нового слова → «Дальше» → проверка с вариантами перевода → итог", async () => {
  await withDeck([sample("a"), sample("b"), sample("c"), sample("d"), sample("e", { lang: "en" })], async () => {
    env.WORDS_PER_DAY = "2";
    try {
      await post(owner("/palabras"));
      assert.match(calls.at(-2).body.text, /Новых слов: 2/);
      const card = calls.at(-1);
      assert.equal(card.method, "sendMessage");
      assert.match(card.body.text, /🆕 Новое слово 1\/2[\s\S]*разбор/);
      assert.equal(card.body.reply_markup.inline_keyboard[0][0].callback_data, "pl:a");

      await post(ownerPress("pl:a"));
      assert.equal(JSON.parse(kv.get("deck:1")).fresh, 1);
      await post(ownerPress("pl:a")); // повторное нажатие ничего не ломает
      assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
      await post(ownerPress("pl:b"));
      const front = calls.at(-1);
      assert.match(front.body.text, /🔁 Повторение 1\/2[\s\S]*palabra a[\s\S]*Выберите перевод/);
      const options = front.body.reply_markup.inline_keyboard.map((row) => row[0]);
      assert.equal(options.length, 4, "4 варианта: перевод и 3 перевода других испанских слов");
      assert.ok(options.some((o) => o.text === "слово a") && !options.some((o) => o.text === "слово e"));

      await post(ownerPress(options.find((o) => o.text === "слово a").callback_data)); // верно
      assert.match(calls.find((c) => c.method === "editMessageText" && /Верно/.test(c.body.text)).body.text, /слово a/);
      assert.match(calls.at(-1).body.text, /Повторение 2\/2[\s\S]*palabra b/);

      const wrong = calls.at(-1).body.reply_markup.inline_keyboard.map((row) => row[0]).find((o) => o.text !== "слово b");
      await post(ownerPress(wrong.callback_data)); // ошибка — правильный ответ и «Дальше»
      assert.match(calls.at(-1).body.text, /Вы выбрали[\s\S]*Повторим в следующий раз/);
      assert.equal(calls.at(-1).body.reply_markup.inline_keyboard[0][0].callback_data, "pf");
      await post(ownerPress("pc:b")); // весь разбор можно открыть и после ответа
      assert.match(calls.at(-1).body.text, /разбор/);
      await post(ownerPress("pf"));
      const end = calls.at(-1);
      assert.match(end.body.text, /Готово![\s\S]*Новых слов: 2[\s\S]*Верно: 1, ошибок: 1/);
      await post(ownerPress("pf"));
      assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
      const deck = JSON.parse(kv.get("deck:1"));
      assert.equal(deck.session, null);
      assert.equal(deck.cards.a[0], 1);
      assert.equal(deck.cards.b[0], 0);
    } finally {
      delete env.WORDS_PER_DAY;
    }
  });
});

test("«Мои слова»: если вариантов нет — карточка «Помню / Не помню»", async () => {
  await withDeck([sample("a")], async () => {
    await post(owner("/palabras"));
    await post(ownerPress("pl:a"));
    assert.equal(calls.at(-1).body.reply_markup.inline_keyboard[0][0].callback_data, "ps:a");
    await post(ownerPress("ps:a"));
    assert.match(calls.at(-1).body.text, /слово a/);
    await post(ownerPress("py:a"));
    assert.match(calls.at(-1).body.text, /Готово![\s\S]*Верно: 1/);
  });
});

test("«Мои слова»: утром и вечером (WORDS_HOURS) бот сам зовёт заниматься", async () => {
  const run = async (iso) => {
    const waits = [];
    await bot.scheduled({ scheduledTime: Date.parse(iso) }, { ...env, WORDS_HOURS: "8,19" }, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
  };
  await withDeck([sample("a"), sample("b")], async () => {
    await run("2026-10-27T06:00:00Z"); // 08:00 по Киеву
    assert.equal(calls.length, 1);
    assert.equal(calls[0].body.chat_id, "1");
    assert.match(calls[0].body.text, /Новых слов: 2[\s\S]*последние новые слова/);
    assert.equal(calls[0].body.reply_markup.inline_keyboard[0][0].callback_data, "pgo");
    assert.match(calls[0].body.text, /утренняя смена/);
    calls = [];
    await run("2026-10-27T07:00:00Z"); // 09:00 — уже не зовёт (только публикация)
    assert.deepEqual(calls.map((c) => c.method), ["dispatch"]);
    calls = [];
    await run("2026-10-27T17:00:00Z"); // 19:00 — утром не занимались: вечерняя смена, те же 2 слова, а не вдвое больше
    assert.equal(calls.length, 1);
    assert.match(calls[0].body.text, /вечерняя смена[\s\S]*Новых слов: 2/);
  });
});

test("колода Гали: смены приходят и ей, со своими кнопками", async () => {
  saved.push(...GALYA.splice(0));
  GALYA.push(sample("g"));
  const waits = [];
  try {
    const run = async (iso) => {
      await bot.scheduled({ scheduledTime: Date.parse(iso) },
        { ...env, GALYA_CHAT_ID: "5", WORDS_HOURS: "8,19" }, { waitUntil: (p) => waits.push(p) });
      await Promise.all(waits);
    };
    await run("2026-10-27T06:00:00Z"); // 8:00 по Киеву — у Гали занятия ещё нет
    assert.deepEqual(calls.map((c) => c.method), []);
    await run("2026-10-27T15:00:00Z"); // 16:00 в Испании
    assert.equal(calls.length, 1);
    assert.match(calls[0].body.text, /занятие на сегодня/);
    assert.equal(calls[0].body.chat_id, "5");
    assert.equal(calls[0].body.reply_markup.inline_keyboard[0][0].callback_data, "wgo");
  } finally {
    GALYA.length = 0;
    GALYA.push(...saved.splice(0));
  }
});
