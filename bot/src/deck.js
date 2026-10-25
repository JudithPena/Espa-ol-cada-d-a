// «Мои слова» — личная колода автора: content/mis_palabras/ → bot/data/mywords.json.
// Каждый день — до WORDS_PER_DAY новых карточек-разборов и повторение по интервалам из srs.js:
// слово, которое помните, возвращается через 1, 3, 7, 14, 30, 60, 120 дней — новые чаще, старые реже;
// забытое — через несколько карточек этого же занятия и снова на следующий день.
// Занятие: разборы новых слов («l») → повторение старых → проверка сегодняшних новых («r»).

import { INTERVALS, LEARNED_BOX, RETRY_GAP } from "./srs.js";

export const NEW_PER_DAY = 10;
export const CHOICES = 4; // вариантов перевода на карточке повторения
export const REVIEW_LIMIT = 60; // повторений за одно занятие, не больше

export function newDeck() {
  return { cards: {}, session: null, day: 0, fresh: 0 };
}

// Сколько новых слов ещё можно взять сегодня.
export function freshLeft(deck, today, perDay = NEW_PER_DAY) {
  return Math.max(0, perDay - (deck.day === today ? deck.fresh : 0));
}

export function deckQueue(deck, words, today, perDay = NEW_PER_DAY) {
  const due = words
    .filter((w) => deck.cards[w.id] && deck.cards[w.id][1] <= today)
    .sort((a, b) => deck.cards[a.id][1] - deck.cards[b.id][1] || deck.cards[a.id][0] - deck.cards[b.id][0])
    .slice(0, REVIEW_LIMIT)
    .map((w) => `r:${w.id}`);
  const fresh = words.filter((w) => !deck.cards[w.id]).slice(0, freshLeft(deck, today, perDay)).map((w) => w.id);
  return [...fresh.map((id) => `l:${id}`), ...due, ...fresh.map((id) => `r:${id}`)];
}

export function startDeckSession(deck, words, today, perDay = NEW_PER_DAY) {
  const queue = deckQueue(deck, words, today, perDay);
  deck.session = queue.length ? { queue, pos: 0, retry: [], right: 0, wrong: 0, learned: 0, day: today } : null;
  return deck.session;
}

// Варианты ответа: перевод слова и CHOICES - 1 переводов других слов того же языка, вперемешку.
// Если похожих слов в колоде меньше двух, вариантов нет — тогда карточка «Помню / Не помню».
export function choices(word, words, n = CHOICES, random = Math.random) {
  const seen = new Set([word.ru]);
  const others = shuffle(words.filter((w) => w.id !== word.id && w.lang === word.lang), random)
    .filter((w) => !seen.has(w.ru) && seen.add(w.ru))
    .slice(0, n - 1);
  return others.length ? shuffle([word, ...others], random).map((w) => w.id) : [];
}

function shuffle(list, random) {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Текущая карточка: ["l" | "r", id] или null.
export function currentItem(deck) {
  const s = deck.session;
  if (!s || s.pos >= s.queue.length) return null;
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
