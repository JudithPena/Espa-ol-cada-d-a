import test from "node:test";
import assert from "node:assert/strict";
import { sendGrammarDaily, sendGrammarPreview, validateGrammar } from "../src/grammar.js";

const posts = [
  { id: "001", title: "Uno", rich_html: "<h2>Rule</h2><p>Exercise</p><details><summary>Answer</summary><p>Answer</p></details>" },
  { id: "002", title: "Dos", rich_html: "<p>second</p>" },
];
function setup() {
  const data = new Map();
  const delivered = [];
  return {
    data, delivered,
    env: { ADMIN_CHAT_ID: "123", TIMEZONE: "Europe/Kyiv", GRAMMAR_HOUR: "9",
      SRS: { get: async (k) => data.has(k) ? JSON.parse(data.get(k)) : null,
        put: async (k, v) => { data.set(k, v); } } },
    send: async (env, text) => { delivered.push([env.ADMIN_CHAT_ID, text]); },
  };
}
test("one unit a day, in order, only at 9 Kyiv; no repeat after redeploy", async () => {
  const s = setup();
  await sendGrammarDaily(s.env, new Date("2026-11-02T06:00:00Z"), posts, s.send);
  assert.equal(s.delivered.length, 0);
  await sendGrammarDaily(s.env, new Date("2026-11-02T07:00:00Z"), posts, s.send);
  await sendGrammarDaily(s.env, new Date("2026-11-02T07:30:00Z"), posts, s.send);
  assert.equal(s.delivered.length, 1);
  await sendGrammarDaily(s.env, new Date("2026-11-03T07:00:00Z"), posts, s.send);
  assert.equal(s.delivered.at(-1)[1], "<p>second</p>");
  await sendGrammarDaily(s.env, new Date("2026-11-04T07:00:00Z"), posts, s.send);
  assert.equal(s.delivered.length, 2);
  assert.ok(s.delivered.every(([chat]) => chat === "123"));
});
test("summer time and draft barrier", async () => {
  const s = setup();
  await sendGrammarDaily(s.env, new Date("2027-07-01T06:00:00Z"), posts, s.send);
  assert.equal(s.delivered.length, 1);
  const d = setup();
  await sendGrammarDaily(d.env, new Date("2026-11-02T07:00:00Z"), [{id:"draft",draft:true}, ...posts], d.send);
  assert.equal(d.delivered.length, 0);
});
test("empty queue and missing/private recipient guard", async () => {
  const s = setup();
  for (const chat of [undefined, "-100123", "@channel"]) {
    await sendGrammarDaily({...s.env, ADMIN_CHAT_ID:chat}, new Date("2026-11-02T07:00:00Z"), posts, s.send);
  }
  await sendGrammarDaily(s.env, new Date("2026-11-02T07:00:00Z"), [], s.send);
  assert.equal(s.delivered.length, 0);
});
test("uncertain rich send pauses without duplicates", async () => {
  const s = setup();
  let count = 0;
  await assert.rejects(sendGrammarDaily(s.env, new Date("2026-11-02T07:00:00Z"), posts, async () => {
    ++count; throw new Error("timeout");
  }));
  const state = JSON.parse(s.data.get("grammar:queue:123"));
  assert.equal(count, 1);
  assert.equal(state.current.pending, true);
  await assert.rejects(sendGrammarDaily(s.env, new Date("2026-11-03T07:00:00Z"), posts, s.send), /uncertain/);
  assert.equal(s.delivered.length, 0);
});
test("validate before sending", () => {
  assert.throws(() => validateGrammar([...posts, posts[0]]));
  assert.throws(() => validateGrammar([{id:"x",title:"x",rich_html:"x".repeat(32769)}]));
  validateGrammar(posts);
});

test("long unit uses exactly one sendRichMessage request with details", async () => {
  const s = setup();
  const html = "<h2>Title</h2><p>" + "x".repeat(5000) + "</p><details><summary>Answers</summary><p>Hidden</p></details>";
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({url, body:JSON.parse(init.body)});
    return Response.json({ok:true,result:{message_id:1}});
  };
  try {
    await sendGrammarDaily({...s.env,TELEGRAM_BOT_TOKEN:"test"}, new Date("2026-11-02T07:00:00Z"), [{id:"long",title:"Long",rich_html:html}]);
    assert.equal(calls.length, 1);
    assert.match(calls[0].url, /\/sendRichMessage$/);
    assert.deepEqual(calls[0].body, {chat_id:"123",rich_message:{html}});
    assert.throws(() => validateGrammar([{id:"legacy",title:"Legacy",messages:["split"]}]));
  } finally { globalThis.fetch = original; }
});

test("preview is one rich request and does not touch queue progress", async () => {
  const s = setup();
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({url,body:JSON.parse(init.body)});
    return Response.json({ok:true,result:{message_id:42}});
  };
  try {
    const result = await sendGrammarPreview({...s.env,TELEGRAM_BOT_TOKEN:"test"}, posts[0]);
    assert.equal(result.message_id,42);
    assert.equal(calls.length,1);
    assert.match(calls[0].url, /\/sendRichMessage$/);
    assert.equal(calls[0].body.rich_message.html,posts[0].rich_html);
    assert.equal(s.data.size,0);
    await assert.rejects(sendGrammarPreview({...s.env,TELEGRAM_BOT_TOKEN:"test",ADMIN_CHAT_ID:"-100"},posts[0]), /author chat/);
    assert.equal(calls.length,1);
  } finally { globalThis.fetch=original; }
});
