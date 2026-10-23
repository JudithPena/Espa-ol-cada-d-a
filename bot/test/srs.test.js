import assert from "node:assert/strict";
import { test } from "node:test";
import { answer, buildQueue, dayNumber, localHour, newUser, progress, startSession } from "../src/srs.js";

const words = Array.from({ length: 30 }, (_, i) => ({ id: `w${i}` }));

test("день и час — по Киеву, с переходом на зимнее время", () => {
  // 21:30 UTC 24 октября — уже 25 октября по Киеву (UTC+3)
  assert.equal(dayNumber(new Date("2026-10-24T21:30:00Z"), "Europe/Kyiv") -
    dayNumber(new Date("2026-10-24T12:00:00Z"), "Europe/Kyiv"), 1);
  assert.equal(localHour(new Date("2026-10-23T06:00:00Z"), "Europe/Kyiv"), 9); // летнее UTC+3
  assert.equal(localHour(new Date("2026-10-27T07:00:00Z"), "Europe/Kyiv"), 9); // зимнее UTC+2
});

test("в первом повторении — 5 новых слов по порядку курса", () => {
  assert.deepEqual(buildQueue(newUser(), words, 100), ["w0", "w1", "w2", "w3", "w4"]);
});

test("знакомое слово возвращается всё реже, забытое — в конце повторения и снова сегодня", () => {
  const user = newUser();
  startSession(user, words, 100);
  assert.equal(answer(user, "w0", true, 100), true);
  assert.deepEqual(user.cards.w0, [1, 101]);
  answer(user, "w1", false, 100);
  assert.deepEqual(user.cards.w1, [0, 100]);
  assert.equal(user.session.queue.at(-1), "w1"); // повторим в конце
  for (const id of ["w2", "w3", "w4"]) answer(user, id, true, 100);
  assert.equal(answer(user, "w1", false, 100), false); // второй раз в конец не добавляется
  assert.equal(user.session.wrong, 2);
  // назавтра: w1 (забыто) и слова первой коробки, потом новые
  const next = buildQueue(user, words, 101);
  assert.deepEqual(next.slice(0, 5).sort(), ["w0", "w1", "w2", "w3", "w4"]);
  assert.deepEqual(next.slice(5), ["w5", "w6", "w7", "w8", "w9"]);
  user.cards.w0 = [2, 101];
  answer({ ...user, session: { queue: ["w0"], pos: 0, retry: [], right: 0, wrong: 0 } }, "w0", true, 101);
  assert.deepEqual(user.cards.w0, [3, 108]);
});

test("повторять нечего — повторение не начинается", () => {
  const user = newUser();
  for (const w of words) user.cards[w.id] = [3, 200];
  assert.equal(startSession(user, words, 100), null);
  assert.deepEqual(progress(user, words, 100), { available: 30, seen: 30, learned: 30, due: 0, fresh: 0 });
});
