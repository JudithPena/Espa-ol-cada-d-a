// Прогресс сайта курса (espanolcadadia.pages.dev): вход через Telegram и хранение прогресса в KV.
//  • POST /site/login — сайт присылает данные Telegram Login Widget; бот проверяет подпись и выдаёт токен.
//  • GET/PUT /site/progress — прогресс ученика (JSON), токен в заголовке Authorization: Bearer ….
// Ключи в KV — «site:<id в Telegram>», других ключей бота это не касается. Записей мало: сайт отправляет прогресс
// редко (конец урока, закрытие страницы), потому что у бесплатного KV дневной лимит записей общий с ботом.

const enc = new TextEncoder();
const ORIGINS = ["https://espanolcadadia.pages.dev"];
const LOGIN_MAX_AGE = 24 * 3600;       // данные входа от Telegram действуют сутки
const TOKEN_TTL = 180 * 24 * 3600;     // токен сайта — полгода
const MAX_BODY = 256 * 1024;           // прогресс одного ученика — не больше 256 КБ

const toHex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
const b64url = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

async function hmacKey(raw) {
  return crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

async function hmac(keyBytes, text) {
  return crypto.subtle.sign("HMAC", await hmacKey(keyBytes), enc.encode(text));
}

function same(a, b) { // сравнение строк за одно и то же время
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// Подпись входа: hash = HMAC-SHA256(SHA256(токен бота), «поле=значение» через перевод строки, поля по алфавиту).
export async function verifyLogin(data, botToken, now = Date.now()) {
  if (!data || typeof data !== "object" || typeof data.hash !== "string" || !data.id) return false;
  const check = Object.keys(data).filter((k) => k !== "hash").sort().map((k) => `${k}=${data[k]}`).join("\n");
  const secret = await crypto.subtle.digest("SHA-256", enc.encode(botToken));
  const expected = toHex(await hmac(secret, check));
  if (!same(expected, data.hash.toLowerCase())) return false;
  const age = now / 1000 - Number(data.auth_date);
  return Number.isFinite(age) && age >= 0 - 60 && age <= LOGIN_MAX_AGE;
}

async function sessionKey(botToken) { // отдельный ключ для токенов сайта, не тот, что подписывает вход
  return hmac(enc.encode(botToken), "site-session");
}

export async function makeToken(id, botToken, now = Date.now()) {
  const body = `${id}.${Math.floor(now / 1000) + TOKEN_TTL}`;
  return `${b64url(enc.encode(body))}.${b64url(await hmac(await sessionKey(botToken), body))}`;
}

export async function readToken(token, botToken, now = Date.now()) {
  const [payload, sig] = String(token || "").split(".");
  if (!payload || !sig) return null;
  let body;
  try {
    body = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
  } catch (err) {
    return null;
  }
  const expected = b64url(await hmac(await sessionKey(botToken), body));
  if (!same(expected, sig)) return null;
  const [id, exp] = body.split(".");
  return /^\d+$/.test(id) && Number(exp) * 1000 > now ? id : null;
}

function cors(request) {
  const origin = request.headers.get("Origin");
  const headers = { "Vary": "Origin" };
  if (ORIGINS.includes(origin) || /^https:\/\/[a-z0-9-]+\.espanolcadadia\.pages\.dev$/.test(origin || "")) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, OPTIONS";
    headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type";
    headers["Access-Control-Max-Age"] = "86400";
  }
  return headers;
}

const json = (request, data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { ...cors(request), "Content-Type": "application/json" } });

export async function handleSite(request, env) {
  const path = new URL(request.url).pathname;
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(request) });
  try {
    if (path === "/site/login" && request.method === "POST") {
      const data = await request.json();
      if (!(await verifyLogin(data, env.TELEGRAM_BOT_TOKEN))) return json(request, { error: "bad login" }, 401);
      return json(request, { token: await makeToken(String(data.id), env.TELEGRAM_BOT_TOKEN) });
    }
    if (path === "/site/progress") {
      const id = await readToken((request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, ""), env.TELEGRAM_BOT_TOKEN);
      if (!id) return json(request, { error: "unauthorized" }, 401);
      const key = `site:${id}`;
      if (request.method === "GET") return json(request, { progress: await env.SRS.get(key, "json") });
      if (request.method === "PUT") {
        const text = await request.text();
        if (text.length > MAX_BODY) return json(request, { error: "too large" }, 413);
        let progress;
        try {
          progress = JSON.parse(text);
        } catch (err) {
          return json(request, { error: "bad json" }, 400);
        }
        if (!progress || typeof progress !== "object" || Array.isArray(progress)) return json(request, { error: "bad progress" }, 400);
        await env.SRS.put(key, JSON.stringify(progress));
        return json(request, { ok: true });
      }
    }
    return json(request, { error: "not found" }, 404);
  } catch (err) {
    console.error("site failed", err && err.message ? err.message : err); // тело запроса и токены в лог не пишем
    return json(request, { error: "server error" }, 500);
  }
}
