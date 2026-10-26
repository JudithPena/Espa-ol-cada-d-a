// Личные повторения: у каждого ученика своё расписание (система Лейтнера).
// Слово, которое вы знаете, возвращается всё реже: через 1, 3, 7, 14, 30, 60, 120 дней.
// Слово, которое вы не вспомнили, возвращается через несколько карточек этого же повторения
// (если они ещё есть), а потом — в следующем повторении. Само занятие — deck.js.

export const INTERVALS = [1, 3, 7, 14, 30, 60, 120]; // дней до следующего показа для коробок 1…7
export const SESSION_SIZE = 10; // слов курса за одно повторение (новые и те, что пора повторить)
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

export function localWeekday(date, timeZone) { // 0 — воскресенье, 3 — среда, 6 — суббота
  const day = new Intl.DateTimeFormat("en-US", { timeZone, weekday: "short" }).format(date);
  return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(day);
}

export function newUser() {
  return { cards: {}, session: null };
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
