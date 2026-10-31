import assert from "node:assert/strict";
import { createHash, createHmac } from "node:crypto";
import { beforeEach, test } from "node:test";
import bot from "../src/index.js";
import { makeToken, readToken, verifyLogin } from "../src/site.js";

const TOKEN = "123:TEST";
const ORIGIN = "https://espanolcadadia.pages.dev";
let env;
let kv;

function signed(fields) { // как подписывает Telegram Login Widget
  const check = Object.keys(fields).sort().map((k) => `${k}=${fields[k]}`).join("\n");
  const hash = createHmac("sha256", createHash("sha256").update(TOKEN).digest()).update(check).digest("hex");
  return { ...fields, hash };
}
const login = () => signed({ id: 42, first_name: "Ана", username: "ana", auth_date: Math.floor(Date.now() / 1000) });
const call = (path, init = {}) => bot.fetch(new Request(`https://bot.example${path}`, init), env, {});
const asJson = (data, method = "POST") => ({ method, headers: { Origin: ORIGIN, "Content-Type": "application/json" }, body: JSON.stringify(data) });

beforeEach(() => {
  kv = new Map();
  env = {
    TELEGRAM_BOT_TOKEN: TOKEN,
    SRS: {
      get: async (k, type) => (kv.has(k) ? (type === "json" ? JSON.parse(kv.get(k)) : kv.get(k)) : null),
      put: async (k, v) => { kv.set(k, v); },
    },
  };
});

test("подпись Telegram: верная проходит, подделка и старые данные нет", async () => {
  assert.equal(await verifyLogin(login(), TOKEN), true);
  assert.equal(await verifyLogin({ ...login(), id: 43 }, TOKEN), false);
  assert.equal(await verifyLogin(login(), "другой токен"), false);
  const old = signed({ id: 42, auth_date: Math.floor(Date.now() / 1000) - 2 * 86400 });
  assert.equal(await verifyLogin(old, TOKEN), false);
  assert.equal(await verifyLogin({ id: 42 }, TOKEN), false);
});

test("токен сайта: проверяется подпись и срок", async () => {
  const token = await makeToken("42", TOKEN);
  assert.equal(await readToken(token, TOKEN), "42");
  assert.equal(await readToken(token, "другой токен"), null);
  assert.equal(await readToken(`${token}x`, TOKEN), null);
  assert.equal(await readToken(token, TOKEN, Date.now() + 200 * 86400 * 1000), null);
  assert.equal(await readToken("", TOKEN), null);
});

test("вход → прогресс сохраняется и читается; без токена нельзя", async () => {
  const resp = await call("/site/login", asJson(login()));
  assert.equal(resp.status, 200);
  assert.equal(resp.headers.get("Access-Control-Allow-Origin"), ORIGIN);
  const { token } = await resp.json();
  const auth = { Authorization: `Bearer ${token}`, Origin: ORIGIN };

  assert.deepEqual(await (await call("/site/progress", { headers: auth })).json(), { progress: null });
  const put = await call("/site/progress", { method: "PUT", headers: auth, body: JSON.stringify({ xp: 5, done: { a: { stars: 3 } } }) });
  assert.equal(put.status, 200);
  assert.ok(kv.has("site:42") && kv.size === 1);
  assert.deepEqual((await (await call("/site/progress", { headers: auth })).json()).progress, { xp: 5, done: { a: { stars: 3 } } });

  assert.equal((await call("/site/progress", { headers: { Origin: ORIGIN } })).status, 401);
  assert.equal((await call("/site/progress", { headers: { Authorization: "Bearer bad-token", Origin: ORIGIN } })).status, 401);
});

test("подделанный вход не получает токен", async () => {
  const bad = { ...login(), id: 7 };
  assert.equal((await call("/site/login", asJson(bad))).status, 401);
});

test("прогресс: только объект и не слишком большой", async () => {
  const { token } = await (await call("/site/login", asJson(login()))).json();
  const auth = { Authorization: `Bearer ${token}`, Origin: ORIGIN };
  assert.equal((await call("/site/progress", { method: "PUT", headers: auth, body: "[1]" })).status, 400);
  assert.equal((await call("/site/progress", { method: "PUT", headers: auth, body: "не json" })).status, 400);
  assert.equal((await call("/site/progress", { method: "PUT", headers: auth, body: JSON.stringify({ x: "я".repeat(300000) }) })).status, 413);
  assert.equal(kv.size, 0);
});

test("CORS: только сайт курса и его предпросмотры", async () => {
  const pre = await call("/site/progress", { method: "OPTIONS", headers: { Origin: ORIGIN } });
  assert.equal(pre.status, 204);
  assert.match(pre.headers.get("Access-Control-Allow-Headers"), /Authorization/);
  assert.match(pre.headers.get("Access-Control-Allow-Methods"), /PUT/);
  const preview = await call("/site/progress", { method: "OPTIONS", headers: { Origin: "https://claude-x.espanolcadadia.pages.dev" } });
  assert.ok(preview.headers.get("Access-Control-Allow-Origin"));
  const other = await call("/site/progress", { method: "OPTIONS", headers: { Origin: "https://evil.example" } });
  assert.equal(other.headers.get("Access-Control-Allow-Origin"), null);
});

test("остальные адреса бота работают как раньше", async () => {
  assert.equal(await (await call("/")).text(), "Español cada día bot");
  assert.equal((await call("/telegram", { method: "POST", body: "{}" })).status, 403);
  assert.equal((await call("/site/что-то", { headers: { Origin: ORIGIN } })).status, 404);
});
