import assert from "node:assert/strict";
import { test } from "node:test";
import { dayNumber, localHour, localWeekday, newUser, progress } from "../src/srs.js";

const words = Array.from({ length: 30 }, (_, i) => ({ id: `w${i}` }));

test("день и час — по Киеву, с переходом на зимнее время", () => {
  // 21:30 UTC 24 октября — уже 25 октября по Киеву (UTC+3)
  assert.equal(dayNumber(new Date("2026-10-24T21:30:00Z"), "Europe/Kyiv") -
    dayNumber(new Date("2026-10-24T12:00:00Z"), "Europe/Kyiv"), 1);
  assert.equal(localHour(new Date("2026-10-23T06:00:00Z"), "Europe/Kyiv"), 9); // летнее UTC+3
  assert.equal(localHour(new Date("2026-10-27T07:00:00Z"), "Europe/Kyiv"), 9); // зимнее UTC+2
  assert.equal(localWeekday(new Date("2026-10-28T17:00:00Z"), "Europe/Kyiv"), 3); // среда
});

test("прогресс: выучено — с третьей коробки, пора повторить — срок подошёл", () => {
  const user = newUser();
  user.cards = { w0: [3, 200], w1: [1, 100], w2: [0, 90] };
  assert.deepEqual(progress(user, words, 100), { available: 30, seen: 3, learned: 1, due: 2, fresh: 27 });
});
