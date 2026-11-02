import test from "node:test";
import assert from "node:assert/strict";
import { sendGrammarDaily, validateGrammar } from "../src/grammar.js";

const posts = [
  { id: "001", title: "Uno", messages: ["rule", "exercise", "<tg-spoiler>answer</tg-spoiler>"] },
  { id: "002", title: "Dos", messages: ["second"] },
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
  assert.equal(s.delivered.length, 3);
  await sendGrammarDaily(s.env, new Date("2026-11-03T07:00:00Z"), posts, s.send);
  assert.equal(s.delivered.at(-1)[1], "second");
  await sendGrammarDaily(s.env, new Date("2026-11-04T07:00:00Z"), posts, s.send);
  assert.equal(s.delivered.length, 4);
  assert.ok(s.delivered.every(([chat]) => chat === "123"));
});
test("summer time and draft barrier", async () => {
  const s = setup();
  await sendGrammarDaily(s.env, new Date("2027-07-01T06:00:00Z"), posts, s.send);
  assert.equal(s.delivered.length, 3);
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
test("uncertain send pauses without duplicates; confirmed messages remain checkpointed", async () => {
  const s = setup();
  let count = 0;
  await assert.rejects(sendGrammarDaily(s.env, new Date("2026-11-02T07:00:00Z"), posts, async () => {
    if (++count === 2) throw new Error("timeout");
  }));
  const state = JSON.parse(s.data.get("grammar:queue:123"));
  assert.equal(state.current.next, 1);
  assert.equal(state.current.pending, 2);
  await assert.rejects(sendGrammarDaily(s.env, new Date("2026-11-03T07:00:00Z"), posts, s.send), /uncertain/);
  assert.equal(s.delivered.length, 0);
});
test("validate before sending", () => {
  assert.throws(() => validateGrammar([...posts, posts[0]]));
  assert.throws(() => validateGrammar([{id:"x",title:"x",messages:["x".repeat(4097)]}]));
  validateGrammar(posts);
});
