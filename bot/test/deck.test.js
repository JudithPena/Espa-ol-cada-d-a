import assert from "node:assert/strict";
import { test } from "node:test";
import {
  choices, currentItem, stretchChain, studyQueue, deckProgress, deckQueue, freshLeft, learn, newDeck, recall, startDeckSession,
} from "../src/deck.js";
import { LONG_INTERVALS, learnedBox } from "../src/srs.js";

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
  assert.equal(freshLeft(deck, 100, 10, 2), 10); // вечерняя смена: 20 − 4 = 16, но не больше 10 за смену
  assert.equal(freshLeft(newDeck(), 100, 10, 2), 10); // утром не занимались — вечером 10, не 20
});

test("интервалы: новые слова — чаще, старые — реже; ошибка цепочку не сбрасывает", () => {
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
  const kept = [...deck.cards.w0];
  deck.session.pos = 0;
  recall(deck, "w0", false, day);
  assert.deepEqual(deck.cards.w0, kept, "ошибка ничего не сбрасывает");
});

test("ошибка за ошибкой: слово возвращается в том же занятии, пока не ответят верно", () => {
  const deck = newDeck();
  deck.cards.w0 = [4, 0];
  deck.session = { queue: ["r:w0"], pos: 0, retry: [], right: 0, wrong: 0, learned: 0, day: 0 };
  for (let i = 0; i < 3; i++) {
    const { more, retry } = recall(deck, "w0", false, 1);
    assert.equal(more, true);
    assert.equal(retry, true);
  }
  assert.deepEqual(deck.cards.w0, [4, 0], "коробка и срок не тронуты");
  const last = recall(deck, "w0", true, 1);
  assert.equal(last.more, false);
  assert.equal(deck.cards.w0[0], 5);
  assert.equal(deck.session.wrong, 3);
});

test("растянутая цепочка (колода Гали): каждый шаг по 5 раз", () => {
  assert.equal(LONG_INTERVALS.length, 35);
  assert.deepEqual(LONG_INTERVALS.slice(0, 11), [1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 7]);
  assert.equal(learnedBox(LONG_INTERVALS), 11, "выучено, когда следующий показ — через неделю");
  assert.equal(learnedBox(), 3);
  const deck = newDeck();
  deck.session = { queue: ["r:w0"], pos: 0, retry: [], right: 0, wrong: 0, learned: 0, day: 0 };
  deck.cards.w0 = [0, 0];
  for (let i = 0; i < 6; i++) {
    deck.session.pos = 0;
    recall(deck, "w0", true, 100, LONG_INTERVALS);
  }
  assert.deepEqual(deck.cards.w0, [6, 103], "пять раз через день, потом через 3 дня");
  const p = deckProgress({ cards: { w0: [10, 1], w1: [11, 1] } }, [{ id: "w0" }, { id: "w1" }], 0, LONG_INTERVALS);
  assert.equal(p.learned, 1);
});

test("переход на растянутую цепочку: тот же интервал, пересчёт один раз", () => {
  const deck = newDeck();
  deck.cards = { a: [0, 5], b: [1, 6], c: [3, 9], d: [5, 40] };
  assert.equal(stretchChain(deck), true);
  assert.deepEqual(deck.cards, { a: [0, 5], b: [1, 6], c: [11, 9], d: [21, 40] });
  assert.equal(learnedBox(LONG_INTERVALS), 11, "слово из старой коробки 3 осталось выученным");
  assert.equal(stretchChain(deck), false);
  assert.equal(deck.cards.c[0], 11);
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

test("варианты ответа: перевод слова и переводы других слов того же языка, без повторов", () => {
  const deck = [
    { id: "a", lang: "es", ru: "яд" }, { id: "b", lang: "es", ru: "месть" }, { id: "c", lang: "es", ru: "яд" },
    { id: "d", lang: "es", ru: "могила" }, { id: "e", lang: "es", ru: "убийца" }, { id: "f", lang: "en", ru: "тонкий" },
  ];
  for (let i = 0; i < 20; i++) {
    const opts = choices(deck[0], deck);
    assert.equal(opts.length, 4);
    assert.ok(opts.includes("a") && !opts.includes("c") && !opts.includes("f"));
    assert.equal(new Set(opts).size, 4);
  }
  assert.equal(choices(deck[0], deck, 6).length, 4, "сколько есть разных переводов");
  assert.deepEqual(choices(deck[5], deck), [], "одно английское слово — вариантов нет");
  const close = [{ id: "x", lang: "es", ru: "поведение" }, { id: "y", lang: "es", ru: "отношение, поведение" },
    { id: "z", lang: "es", ru: "ревность (к кому-то)" }];
  for (let i = 0; i < 20; i++) assert.deepEqual(choices(close[0], close).sort(), ["x", "z"], "общее значение — не вариант");
});

test("слова курса: по ссылке из урока — слова урока первыми (новые — карточкой, знакомые — повторением)", () => {
  const state = newDeck();
  state.cards = { w1: [2, 50], w20: [2, 90], w21: [1, 99], w22: [3, 150] }; // w22 — ещё рано
  const own = words.slice(0, 3);
  assert.deepEqual(studyQueue(state, words, 100, { first: own, reviews: 7 }),
    ["l:w0", "l:w2", "r:w1", "r:w20", "r:w21", "r:w0", "r:w2"]);
  assert.deepEqual(studyQueue(newDeck(), words, 100, { fresh: 2 }), ["l:w0", "l:w1", "r:w0", "r:w1"]);
});

test("занятие старого формата не продолжаем", () => {
  const state = newDeck();
  state.session = { queue: ["w0", "w1"], pos: 0, retry: [] };
  assert.equal(currentItem(state), null);
});
