import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import WORDS from "../data/words.json" with { type: "json" };
import bot from "../src/index.js";

let calls;
let kv;
const env = {
  TELEGRAM_BOT_TOKEN: "T", WEBHOOK_SECRET: "S", GITHUB_TOKEN: "G", ADMIN_CHAT_ID: "1",
  GITHUB_REPO: "o/r", GITHUB_BRANCH: "main", PUBLISH_WORKFLOW: "publish.yml",
  PUBLISH_HOURS: "9,15", TIMEZONE: "Europe/Kyiv",
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
  assert.match(calls.at(-1).body.text, /Повторение закончено/);
  const user = JSON.parse(kv.get("user:9"));
  assert.equal(user.session, null);
  assert.deepEqual(user.cards[first.id][0], 1);
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
