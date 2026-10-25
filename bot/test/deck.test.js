import assert from "node:assert/strict";
import { test } from "node:test";
import {
  currentItem, deckProgress, deckQueue, freshLeft, learn, newDeck, recall, startDeckSession,
} from "../src/deck.js";

const words = Array.from({ length: 25 }, (_, i) => ({ id: `w${i}` }));

test("за день — 10 новых: сначала разборы, потом повторение, в конце проверка новых", () => {
  const deck = newDeck();
  deck.cards = { w20: [2, 5], w21: [1, 9] }; // w20 пора повторить, w21 — ещё нет
  const queue = deckQueue(deck, words, 5);
  assert.deepEqual(queue.slice(0, 10), words.filter((w) => !["w20", "w21"].includes(w.id)).slice(0, 10).map((w) => `l:${w.id}`));
  assert.equal(queue[10], "r:w20");
  assert.deepEqual(queue.slice(11), queue.slice(0, 10).map((q) => q.replace("l:", "r:")));
});

test("новые слова не копятся: в тот же день больше 10 не дают", () => {
  const deck = newDeck();
  startDeckSession(deck, words, 100);
  for (let i = 0; i < 4; i++) learn(deck, currentItem(deck)[1], 100);
  assert.equal(freshLeft(deck, 100), 6);
  startDeckSession(deck, words, 100); // занятие начали заново — новых осталось 6
  assert.equal(deck.session.queue.filter((q) => q.startsWith("l:")).length, 6);
  assert.equal(freshLeft(deck, 101), 10); // завтра снова 10
});

test("интервалы: новые слова — чаще, старые — реже; забытое начинается сначала", () => {
  const deck = newDeck();
  deck.session = { queue: ["r:w0", "r:w0"], pos: 0, retry: [], right: 0, wrong: 0, learned: 0, day: 0 };
  deck.cards.w0 = [0, 0];
  const days = [];
  let day = 0;
  for (let i = 0; i < 5; i++) {
    deck.session.pos = 0;
    recall(deck, "w0", true, day);
    day = deck.cards.w0[1];
    days.push(day);
  }
  assert.deepEqual(days, [1, 4, 11, 25, 55]); // через 1, 3, 7, 14, 30 дней
  deck.session.pos = 0;
  recall(deck, "w0", false, day);
  assert.deepEqual(deck.cards.w0, [0, day]);
});

test("забытое слово возвращается через несколько карточек этого же занятия", () => {
  const deck = newDeck();
  for (const w of words.slice(0, 6)) deck.cards[w.id] = [1, 0];
  startDeckSession(deck, words.slice(0, 6), 3);
  const { retry } = recall(deck, "w0", false, 3);
  assert.equal(retry, true);
  assert.equal(deck.session.queue[4], "r:w0");
  assert.deepEqual(deckProgress(deck, words.slice(0, 6), 3), { total: 6, seen: 6, learned: 0, due: 6, fresh: 0 });
});
