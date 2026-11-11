// Extra practice any time, counted towards today's time goal.
// A round: flashcards of her words, one sentence to build, and one listening/reading/task she has done before.
// Extra practice does not change the flashcard schedule.
import { api } from "../api.js";
import { runCards } from "../blocks/review.js";
import { buildSentence } from "../blocks/wordorder.js";
import { go } from "../main.js";
import { S } from "../strings.js";
import { actionBar, button, celebrate, goalBar, h, say, screen, t, updateCounters } from "../ui.js";

const EXTRA = {
  listening: () => import("../blocks/listening.js"),
  reading: () => import("../blocks/reading.js"),
  task: () => import("../blocks/task.js"),
};
const MAX_STEP_SECONDS = 20 * 60; // ignore time when she walked away

async function timed(fn) {
  const t0 = Date.now();
  const res = await fn();
  const seconds = Math.min(MAX_STEP_SECONDS, Math.round((Date.now() - t0) / 1000));
  const state = await api.post("/api/time", { seconds }).catch(() => null);
  if (state) updateCounters(state);
  return [res, state];
}

export async function render(root) {
  const data = await api.get("/api/practice");
  if (!data.cards.length) {
    const box = screen(root, say({ icon: "🌱", en: "Learn some new words first. Then you can practise here.", am: "መጀመሪያ አዳዲስ ቃላትን ተማሪ። ከዚያ እዚህ መለማመድ ትችያለሽ።" }));
    actionBar(box).append(button(S.home, () => go(""), "primary"));
    return;
  }
  const before = await api.get("/api/state");
  let [res, state] = await timed(() => runCards(root, data.cards, { record: false }));
  if (data.sentence) [, state] = await timed(() => buildSentence(root, data.sentence));
  if (data.extra && EXTRA[data.extra.type]) {
    const mod = await EXTRA[data.extra.type]();
    [, state] = await timed(() => mod.run(root, { item: data.extra.item }));
  }
  state = state || (await api.get("/api/state"));
  if (before.minutes_today < before.goal_minutes && state.minutes_today >= state.goal_minutes) {
    await celebrate(root, S.goalDone, {}, 2200);
  }
  const left = state.goal_minutes - state.minutes_today;
  const box = screen(root, h("div", { class: "celebrate" }, h("div", { class: "big-ico" }, "🌟"), h("h1", {}, t(S.wellDone)),
      h("h2", {}, `🃏 ${res.score} / ${res.max}`)),
    goalBar(state.minutes_today, state.goal_minutes));
  const bar = actionBar(box);
  bar.append(button(left > 0 ? { ...S.keepGoing, en: t(S.keepGoing, { left }) } : S.practiseMore, () => render(root), left > 0 ? "primary" : ""));
  bar.append(button(S.home, () => go(""), left > 0 ? "" : "primary"));
}
