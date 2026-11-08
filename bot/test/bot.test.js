import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import DECK from "../data/mywords.json" with { type: "json" };
import GALYA from "../data/mywords_galya.json" with { type: "json" };
import PAPA from "../data/mywords_papa.json" with { type: "json" };
import WORDS from "../data/words.json" with { type: "json" };
import GRAMMAR from "../../content/grammar.json" with { type: "json" };
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
  GRAMMAR.length = 0; // Scheduler tests use their own queue, independent of authored posts.
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

test("кнопки старого повторения и чужие кнопки не сбивают занятие", async () => {
  await post(message("/repaso"));
  await post(press("y:нет-такого"));
  assert.match(calls.at(-1).body.text, /Повторение обновилось/);
  await post(press("cl:нет-такого"));
  assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
  await post(press("pgo")); // «Мои слова» — только у автора
  assert.equal(kv.has("deck:9"), false);
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

test("колода папы: в 7:00 по Испании шлёт занятие, кнопки «d», слов автора и Гали не видит", async () => {
  const savedPapa = PAPA.splice(0);
  PAPA.push(...["a", "b", "c", "d", "e", "f", "g"].map((x) => sample(x)));
  env.PAPA_CHAT_ID = "7";
  try {
    const waits = [];
    const run = async (iso) => {
      await bot.scheduled({ scheduledTime: Date.parse(iso) }, { ...env, WORDS_HOURS: "8,19" }, { waitUntil: (p) => waits.push(p) });
      await Promise.all(waits);
    };
    await run("2026-10-27T05:00:00Z"); // 6:00 в Испании: папе ещё рано
    assert.equal(calls.filter((c) => c.body.chat_id === "7").length, 0);
    calls = [];
    await run("2026-10-27T06:00:00Z"); // 7:00 в Испании
    const mine = calls.filter((c) => c.body.chat_id === "7");
    assert.equal(mine.length, 1);
    assert.equal(mine[0].body.reply_markup.inline_keyboard[0][0].callback_data, "dgo");
    assert.match(mine[0].body.text, /💌/, "у папы к словам идёт мотивирующая фраза");
    await post({ message: { text: "/palabras", chat: { id: 7, type: "private" }, from: { id: 7 } } });
    assert.match(calls.at(-2).body.text, /Новых слов: 5/);
    assert.equal(calls.at(-1).body.reply_markup.inline_keyboard[0][0].callback_data.startsWith("dl:"), true);
  } finally {
    delete env.PAPA_CHAT_ID;
    PAPA.length = 0;
    PAPA.push(...savedPapa);
  }
});

test("колода Гали: по 5 новых слов за занятие", async () => {
  saved.push(...GALYA.splice(0));
  GALYA.push(...["a", "b", "c", "d", "e", "f", "g"].map((x) => sample(x)));
  env.GALYA_CHAT_ID = "5";
  try {
    await post(galya("/palabras"));
    assert.match(calls.at(-2).body.text, /Новых слов: 5/);
  } finally {
    delete env.GALYA_CHAT_ID;
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
      assert.match(calls.at(-1).body.text, /Вы выбрали[\s\S]*Слово вернётся через пару карточек/);
      assert.equal(calls.at(-1).body.reply_markup.inline_keyboard[0][0].callback_data, "pf");
      await post(ownerPress("pc:b")); // весь разбор можно открыть и после ответа
      assert.match(calls.at(-1).body.text, /разбор/);
      await post(ownerPress("pf")); // ошибка ничего не сбросила, слово попадается ещё раз в этом же занятии
      assert.match(calls.at(-1).body.text, /Повторение 3\/3[\s\S]*palabra b/);
      const again = calls.at(-1).body.reply_markup.inline_keyboard.map((row) => row[0]);
      await post(ownerPress(again.find((o) => o.text === "слово b").callback_data)); // теперь верно
      const end = calls.at(-1);
      assert.match(end.body.text, /Готово![\s\S]*Новых слов: 2[\s\S]*Верно: 2, ошибок: 1/);
      await post(ownerPress("pf"));
      assert.equal(calls.at(-1).body.text, "Эта карточка уже пройдена");
      const deck = JSON.parse(kv.get("deck:1"));
      assert.equal(deck.session, null);
      assert.equal(deck.cards.a[0], 1);
      assert.equal(deck.cards.b[0], 1, "слово b вспомнили со второй попытки");
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
    assert.match(calls[0].body.text, /💌/, "у Гали к словам идёт мотивирующая фраза");
  } finally {
    GALYA.length = 0;
    GALYA.push(...saved.splice(0));
  }
});

test("папа: фото при изучении и открытии разбора, без фото в вопросе повторения", async () => {
  env.PAPA_CHAT_ID = "9";
  try {
    assert.ok(PAPA[0].image);
    await post(message("/palabras"));
    const photo = calls.find((c) => c.method === "sendPhoto");
    assert.equal(photo.body.photo, `https://bot.example/${PAPA[0].image}`);
    assert.ok(calls.at(-1).body.text.includes(PAPA[0].card));
    for (const word of PAPA.slice(0, 4)) await post(press(`dl:${word.id}`, false));
    calls.length = 0;
    await post(press(`dl:${PAPA[4].id}`, false));
    assert.equal(calls.filter((c) => c.method === "sendPhoto").length, 0);
    assert.match(textOf(calls.at(-1)), /Выберите перевод/);
    await post(press(`dc:${PAPA[0].id}`, false));
    assert.equal(calls.filter((c) => c.method === "sendPhoto").length, 1);
  } finally {
    delete env.PAPA_CHAT_ID;
  }
});

test("личная грамматика: очередь уходит в 09:00 только автору, один юнит в день", async () => {
  GRAMMAR.push(
    { id: "test-1", title: "Первый", rich_html: "<h2>Объяснение</h2><p>Практика</p><details><summary>Ответ</summary><p>Ответ</p></details>" },
    { id: "test-2", title: "Второй", rich_html: "<p>Следующий юнит</p>" },
  );
  const run = async (iso) => {
    const waits = [];
    await bot.scheduled({ scheduledTime: Date.parse(iso) }, env, { waitUntil: (p) => waits.push(p) });
    await Promise.all(waits);
  };
  await run("2026-11-03T06:00:00Z");
  assert.equal(calls.filter((c) => c.method === "sendRichMessage").length, 0);
  await run("2026-11-03T07:00:00Z");
  let sent = calls.filter((c) => c.method === "sendRichMessage");
  assert.deepEqual(sent.map((c) => c.body.rich_message.html), [GRAMMAR[0].rich_html]);
  assert.ok(sent.every((c) => c.body.chat_id === env.ADMIN_CHAT_ID && c.body.rich_message.html));
  await run("2026-11-03T07:10:00Z");
  assert.equal(calls.filter((c) => c.method === "sendRichMessage").length, 1);
  await run("2026-11-04T07:00:00Z");
  sent = calls.filter((c) => c.method === "sendRichMessage");
  assert.equal(sent.length, 2);
  assert.equal(sent.at(-1).body.rich_message.html, "<p>Следующий юнит</p>");
});

test("/progreso: сводка по трём колодам только автору", async () => {
  const savedPapa = PAPA.splice(0);
  PAPA.push(...["a", "b", "c"].map((x) => sample(x)));
  env.PAPA_CHAT_ID = "7";
  env.GALYA_CHAT_ID = "5";
  try {
    calls = [];
    await post({ message: { text: "/progreso", chat: { id: 7, type: "private" }, from: { id: 7 } } });
    assert.doesNotMatch(textOf(calls.at(-1)), /Прогресс/, "папе сводку не показываем");
    calls = [];
    await post({ message: { text: "/progreso", chat: { id: 1, type: "private" }, from: { id: 1 } } });
    const text = textOf(calls.at(-1));
    assert.match(text, /Прогресс/);
    assert.match(text, /Галя/);
    assert.match(text, /Папа.*слов в колоде 3/);
    assert.match(text, /следующее новое слово/);
  } finally {
    delete env.PAPA_CHAT_ID;
    delete env.GALYA_CHAT_ID;
    PAPA.length = 0;
    PAPA.push(...savedPapa);
  }
});

test("кнопка старой колоды курса у папы открывает его личную колоду, а не слова курса", async () => {
  const savedPapa = PAPA.splice(0);
  PAPA.push(...["a", "b", "c"].map((x) => sample(x)));
  env.PAPA_CHAT_ID = "7";
  try {
    calls = [];
    await post({ callback_query: { id: "q", data: "cgo", from: { id: 7 }, message: { chat: { id: 7 }, message_id: 1 } } });
    const text = calls.map((c) => c.body.text || "").join("\n");
    assert.match(text, /Мои слова/);
    assert.doesNotMatch(text, /Повторение слов/);
  } finally {
    delete env.PAPA_CHAT_ID;
    PAPA.length = 0;
    PAPA.push(...savedPapa);
  }
});
