// Личные повторения: у каждого ученика своё расписание (система Лейтнера).
// Слово, которое вы знаете, возвращается всё реже: через 1, 3, 7, 14, 30, 60, 120 дней.
// Слово, которое вы не вспомнили, возвращается через несколько карточек этого же повторения
// (если они ещё есть), а потом — в следующем повторении.

export const INTERVALS = [1, 3, 7, 14, 30, 60, 120]; // дней до следующего показа для коробок 1…7
export const SESSION_SIZE = 10; // карточек за одно повторение
export const NEW_PER_SESSION = 5; // новых слов за одно повторение, не больше
export const LEARNED_BOX = 3; // с этой коробки слово считается выученным (интервал — неделя)
export const RETRY_GAP = 3; // забытое слово возвращается через столько карточек, не сразу

// Номер дня по местному времени: дни меняются в полночь по Киеву, а не по UTC.
export function dayNumber(date, timeZone) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date);
  const get = (type) => Number(parts.find((p) => p.type === type).value);
  return Math.floor(Date.UTC(get("year"), get("month") - 1, get("day")) / 86400000);
}

export function localHour(date, timeZone) {
  const hour = new Intl.DateTimeFormat("en-GB", { timeZone, hour: "2-digit", hourCycle: "h23" }).format(date);
  return Number(hour);
}

export function newUser() {
  return { cards: {}, session: null };
}

// Что повторять сейчас: сначала слова, срок которых подошёл (самые давние первыми),
// потом новые слова из вышедших уроков в порядке курса.
export function buildQueue(user, words, today) {
  const due = words
    .filter((w) => user.cards[w.id] && user.cards[w.id][1] <= today)
    .sort((a, b) => user.cards[a.id][1] - user.cards[b.id][1]);
  const queue = due.slice(0, SESSION_SIZE).map((w) => w.id);
  const room = Math.min(NEW_PER_SESSION, SESSION_SIZE - queue.length);
  if (room > 0) {
    queue.push(...words.filter((w) => !user.cards[w.id]).slice(0, room).map((w) => w.id));
  }
  return queue;
}

export function startSession(user, words, today) {
  const queue = buildQueue(user, words, today);
  user.session = queue.length ? { queue, pos: 0, retry: [], right: 0, wrong: 0, msg: null } : null;
  return user.session;
}

export function currentId(user) {
  const s = user.session;
  return s && s.pos < s.queue.length ? s.queue[s.pos] : null;
}

// Ответ на карточку. Возвращает { more: есть ли ещё карточки, retry: вернётся ли слово в этом повторении }.
export function answer(user, id, known, today) {
  const s = user.session;
  const [box] = user.cards[id] || [0, today];
  let retry = false;
  if (known) {
    const next = Math.min(box + 1, INTERVALS.length);
    user.cards[id] = [next, today + INTERVALS[next - 1]];
    s.right += 1;
  } else {
    user.cards[id] = [0, today]; // начинаем сначала: слово снова в очереди уже сегодня
    s.wrong += 1;
    // Один раз повторяем в этом же повторении, но не сразу: через RETRY_GAP карточек.
    // Если столько карточек уже не осталось, слово подождёт следующего повторения.
    if (!s.retry.includes(id) && s.queue.length - s.pos - 1 >= RETRY_GAP) {
      s.retry.push(id);
      s.queue.splice(s.pos + 1 + RETRY_GAP, 0, id);
      retry = true;
    }
  }
  s.pos += 1;
  return { more: s.pos < s.queue.length, retry };
}

export function progress(user, words, today) {
  const seen = words.filter((w) => user.cards[w.id]);
  return {
    available: words.length,
    seen: seen.length,
    learned: seen.filter((w) => user.cards[w.id][0] >= LEARNED_BOX).length,
    due: seen.filter((w) => user.cards[w.id][1] <= today).length,
    fresh: words.length - seen.length,
  };
}
