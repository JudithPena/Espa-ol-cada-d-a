// Занятие со словами — одно и то же для слов курса (/repaso, все ученики) и «Моих слов» (/palabras, автор):
// разборы новых слов («l») → повторение старых → проверка сегодняшних новых («r») с выбором перевода.
// Интервалы — из srs.js: слово, которое помните, возвращается через 1, 3, 7, 14, 30, 60, 120 дней —
// новые чаще, старые реже; забытое — через несколько карточек этого же занятия и снова на следующий день.
// «Мои слова»: до WORDS_PER_DAY новых в каждую смену (WORDS_HOURS: утро и вечер); слова курса — до NEW_PER_SESSION новых за занятие.

import { INTERVALS, LEARNED_BOX, RETRY_GAP } from "./srs.js";

export const NEW_PER_DAY = 10;
export const CHOICES = 4; // вариантов перевода на карточке повторения
export const REVIEW_LIMIT = 60; // повторений за одно занятие, не больше

export function newDeck() {
  return { cards: {}, session: null, day: 0, fresh: 0 };
}

// Сколько новых слов ещё можно взять сейчас. В день несколько смен (утро, вечер), в каждой до perDay новых:
// пропущенная смена не копится — если утром не занимались, вечером всё равно perDay, а не вдвое больше.
// shifts — сколько смен уже началось сегодня.
export function freshLeft(deck, today, perDay = NEW_PER_DAY, shifts = 1) {
  const done = deck.day === today ? deck.fresh : 0;
  return Math.max(0, Math.min(perDay, perDay * shifts - done));
}

// Очередь занятия. first — слова урока по ссылке: они идут первыми (новые — разбором, знакомые — повторением);
// fresh — сколько ещё новых слов взять по порядку; reviews — сколько слов, которые пора повторить.
export function studyQueue(state, words, today, { first = [], fresh = 0, reviews = REVIEW_LIMIT } = {}) {
  const firstIds = new Set(first.map((w) => w.id));
  const isNew = (w) => !state.cards[w.id];
  const learnNow = [...first.filter(isNew), ...words.filter((w) => !firstIds.has(w.id) && isNew(w)).slice(0, fresh)];
  const due = words
    .filter((w) => !firstIds.has(w.id) && state.cards[w.id] && state.cards[w.id][1] <= today)
    .sort((a, b) => state.cards[a.id][1] - state.cards[b.id][1] || state.cards[a.id][0] - state.cards[b.id][0])
    .slice(0, reviews);
  return [
    ...learnNow.map((w) => `l:${w.id}`),
    ...first.filter((w) => !isNew(w)).map((w) => `r:${w.id}`),
    ...due.map((w) => `r:${w.id}`),
    ...learnNow.map((w) => `r:${w.id}`),
  ];
}

export function deckQueue(deck, words, today, perDay = NEW_PER_DAY, shifts = 1) {
  return studyQueue(deck, words, today, { fresh: freshLeft(deck, today, perDay, shifts) });
}

export function startSession(state, queue, today) {
  state.session = queue.length ? { queue, pos: 0, retry: [], right: 0, wrong: 0, learned: 0, day: today } : null;
  return state.session;
}

export function startDeckSession(deck, words, today, perDay = NEW_PER_DAY, shifts = 1) {
  return startSession(deck, deckQueue(deck, words, today, perDay, shifts), today);
}

// Варианты ответа: перевод слова и CHOICES - 1 переводов других слов того же языка, вперемешку.
// Переводы с общим значением не ставим рядом («поведение» и «отношение, поведение»): верным был бы не один.
// Если похожих слов в колоде меньше двух, вариантов нет — тогда карточка «Помню / Не помню».
export function choices(word, words, n = CHOICES, random = Math.random) {
  const taken = meanings(word.ru);
  const others = [];
  for (const w of shuffle(words.filter((x) => x.id !== word.id && x.lang === word.lang), random)) {
    if (others.length >= n - 1) break;
    const m = meanings(w.ru);
    if ([...m].some((x) => taken.has(x))) continue;
    m.forEach((x) => taken.add(x));
    others.push(w);
  }
  return others.length ? shuffle([word, ...others], random).map((w) => w.id) : [];
}

// «понять, осознать (что-то)» → {понять, осознать}
function meanings(ru) {
  return new Set(String(ru).toLowerCase().replace(/\([^)]*\)/g, "").split(/[,;/]/).map((x) => x.trim()).filter(Boolean));
}

function shuffle(list, random) {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Текущая карточка: ["l" | "r", id] или null. Занятия старого формата (без «l:»/«r:») не продолжаем.
export function currentItem(deck) {
  const s = deck.session;
  if (!s || s.pos >= s.queue.length || !/^[lr]:/.test(s.queue[s.pos])) return null;
  const item = s.queue[s.pos];
  return [item.slice(0, 1), item.slice(2)];
}

// Прочитан разбор нового слова: с сегодняшнего дня оно в колоде, проверка — в конце занятия.
export function learn(deck, id, today) {
  const s = deck.session;
  if (!deck.cards[id]) {
    deck.cards[id] = [0, today];
    if (deck.day !== today) {
      deck.day = today;
      deck.fresh = 0;
    }
    deck.fresh += 1;
    s.learned += 1;
  }
  s.pos += 1;
  return s.pos < s.queue.length;
}

// Ответ «помню / не помню». Возвращает { more: есть ли ещё карточки, retry: вернётся ли слово в этом занятии }.
export function recall(deck, id, known, today) {
  const s = deck.session;
  const [box] = deck.cards[id] || [0, today];
  let retry = false;
  if (known) {
    const next = Math.min(box + 1, INTERVALS.length);
    deck.cards[id] = [next, today + INTERVALS[next - 1]];
    s.right += 1;
  } else {
    deck.cards[id] = [0, today];
    s.wrong += 1;
    if (!s.retry.includes(id) && s.queue.length - s.pos - 1 >= RETRY_GAP) {
      s.retry.push(id);
      s.queue.splice(s.pos + 1 + RETRY_GAP, 0, `r:${id}`);
      retry = true;
    }
  }
  s.pos += 1;
  return { more: s.pos < s.queue.length, retry };
}

export function deckProgress(deck, words, today) {
  const seen = words.filter((w) => deck.cards[w.id]);
  return {
    total: words.length,
    seen: seen.length,
    learned: seen.filter((w) => deck.cards[w.id][0] >= LEARNED_BOX).length,
    due: seen.filter((w) => deck.cards[w.id][1] <= today).length,
    fresh: words.length - seen.length,
  };
}
