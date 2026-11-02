// One unit = one Telegram Rich Message. IDs and queue order are permanent.
import { dayNumber, localHour } from "./srs.js";

export const RICH_TEXT_LIMIT = 32768;

export function validateGrammar(posts) {
  if (!Array.isArray(posts)) throw new Error("Grammar queue must be an array");
  const ids = new Set();
  for (const post of posts) {
    if (!post.id || typeof post.id !== "string" || ids.has(post.id)) throw new Error("Invalid/duplicate grammar ID");
    ids.add(post.id);
    if (post.draft) continue;
    // Conservative source-length bound; never split or fall back to ordinary messages.
    if (!post.title || typeof post.rich_html !== "string" || !post.rich_html.trim() ||
        post.rich_html.length > RICH_TEXT_LIMIT || Object.hasOwn(post, "messages")) {
      throw new Error(`Invalid Rich Message grammar post: ${post.id}`);
    }
  }
}

async function send(env, html) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendRichMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: env.ADMIN_CHAT_ID, rich_message: { html } }),
  });
  const result = await response.json();
  if (!result.ok) throw new Error(`Grammar Rich Message delivery failed (${result.error_code})`);
  return result.result;
}

export async function sendGrammarDaily(env, now, posts, sendMessage = send) {
  const zone = env.TIMEZONE || "Europe/Kyiv";
  if (localHour(now, zone) !== Number(env.GRAMMAR_HOUR || "9")) return;
  if (!/^[1-9]\d*$/.test(String(env.ADMIN_CHAT_ID || ""))) return;
  validateGrammar(posts);
  const key = `grammar:queue:${env.ADMIN_CHAT_ID}`;
  const state = (await env.SRS.get(key, "json")) || { sent: [], lastDay: null, current: null };
  const today = dayNumber(now, zone);
  if (state.lastDay !== null && state.lastDay >= today) return;
  const post = state.current
    ? posts.find((p) => p.id === state.current.id)
    : posts.find((p) => !state.sent.includes(p.id));
  if (!post || post.draft) return;
  // Do not replay a partly delivered legacy unit as a complete article automatically.
  if (state.current?.pending || state.current?.next > 0) {
    throw new Error("Grammar delivery uncertain: reconcile pending/legacy message before retry");
  }
  state.current = { id: post.id, pending: true };
  await env.SRS.put(key, JSON.stringify(state));
  // A timeout may mean Telegram accepted the article. Stop for reconciliation rather than duplicate it.
  await sendMessage(env, post.rich_html);
  state.sent.push(post.id);
  state.lastDay = today;
  state.current = null;
  await env.SRS.put(key, JSON.stringify(state));
}

export async function sendGrammarPreview(env, post) {
  if (!env.TELEGRAM_BOT_TOKEN || !/^[1-9]\d*$/.test(String(env.ADMIN_CHAT_ID || ""))) {
    throw new Error("Private grammar preview requires the bot token and author chat ID");
  }
  if (post.draft) throw new Error("Cannot send draft grammar post");
  validateGrammar([post]);
  return send(env, post.rich_html);
}
