// Private grammar queue. IDs are permanent; array order is publication order.
import { dayNumber, localHour } from "./srs.js";

export function validateGrammar(posts) {
  if (!Array.isArray(posts)) throw new Error("Grammar queue must be an array");
  const ids = new Set();
  for (const post of posts) {
    if (!post.id || typeof post.id !== "string" || ids.has(post.id)) throw new Error("Invalid/duplicate grammar ID");
    ids.add(post.id);
    if (post.draft) continue;
    if (!post.title || !Array.isArray(post.messages) || !post.messages.length ||
        post.messages.some((m) => typeof m !== "string" || !m.trim() || m.length > 4096)) {
      throw new Error(`Invalid grammar post: ${post.id}`);
    }
  }
}

async function send(env, text) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: env.ADMIN_CHAT_ID, text, parse_mode: "HTML",
      link_preview_options: { is_disabled: true },
    }),
  });
  const result = await response.json();
  if (!result.ok) throw new Error(`Grammar delivery failed (${result.error_code})`);
}

export async function sendGrammarDaily(env, now, posts, sendMessage = send) {
  const zone = env.TIMEZONE || "Europe/Kyiv";
  if (localHour(now, zone) !== Number(env.GRAMMAR_HOUR || "9")) return;
  // Never fall back to the public channel or to the last person who messaged the bot.
  if (!/^[1-9]\d*$/.test(String(env.ADMIN_CHAT_ID || ""))) return;
  validateGrammar(posts);
  const key = `grammar:queue:${env.ADMIN_CHAT_ID}`;
  const state = (await env.SRS.get(key, "json")) || { sent: [], lastDay: null, current: null };
  const today = dayNumber(now, zone);
  if (state.lastDay !== null && state.lastDay >= today) return;
  const post = state.current
    ? posts.find((p) => p.id === state.current.id)
    : posts.find((p) => !state.sent.includes(p.id));
  // A draft at the front pauses the queue instead of changing the requested order.
  if (!post || post.draft) return;
  state.current ||= { id: post.id, next: 0 };
  if (state.current.pending) throw new Error("Grammar delivery uncertain: reconcile pending message before retry");
  for (let i = state.current.next; i < post.messages.length; i++) {
    // Persist intent first. A timeout could mean Telegram accepted the message:
    // stop for reconciliation instead of silently sending a duplicate.
    state.current.pending = i + 1;
    await env.SRS.put(key, JSON.stringify(state));
    await sendMessage(env, post.messages[i]);
    state.current.next = i + 1;
    delete state.current.pending;
    await env.SRS.put(key, JSON.stringify(state));
  }
  state.sent.push(post.id);
  state.lastDay = today;
  state.current = null;
  await env.SRS.put(key, JSON.stringify(state));
}
