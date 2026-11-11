// Runs one sitting of today's lesson, block by block.
import { api } from "../api.js";
import { go } from "../main.js";
import { S } from "../strings.js";
import { button, celebrate, ctx, goalBar, h, hint, say, screen, t, updateCounters } from "../ui.js";

const BLOCKS = {
  review: () => import("../blocks/review.js"),
  new_words: () => import("../blocks/newwords.js"),
  listening: () => import("../blocks/listening.js"),
  speaking: () => import("../blocks/speaking.js"),
  reading: () => import("../blocks/reading.js"),
  writing: () => import("../blocks/writing.js"),
  task: () => import("../blocks/task.js"),
  weekly_test: () => import("../blocks/weekly_test.js"),
};
const BLOCK_INTRO = {
  review:      { icon: "🃏", en: "My words: practise", am: "ቃላቶቼ፡ ልምምድ" },
  new_words:   { icon: "✨", en: "New words", am: "አዳዲስ ቃላት" },
  listening:   { icon: "🎧", en: "Listening", am: "ማዳመጥ" },
  speaking:    { icon: "🎤", en: "Speaking", am: "መናገር" },
  reading:     { icon: "📖", en: "Reading", am: "ማንበብ" },
  writing:     { icon: "✉️", en: "Writing a letter", am: "ደብዳቤ መጻፍ" },
  task:        { icon: "🏠", en: "Real life", am: "የዕለት ተዕለት ሕይወት" },
  weekly_test: { icon: "🏅", en: "Mini test", am: "ትንሽ ፈተና" },
};
const MAX_BLOCK_SECONDS = 40 * 60; // ignore time when she walked away

export async function render(root, params) {
  const sitting = Number(params[0] || 1);
  const today = await api.get("/api/today");
  const todo = today.blocks.filter((b) => b.sitting === sitting && !b.done);
  for (const block of todo) {
    const intro = BLOCK_INTRO[block.type];
    await celebrate(root, intro, {}, 1300);
    const mod = await BLOCKS[block.type]();
    const t0 = Date.now();
    const res = (await mod.run(root, block)) || {};
    const seconds = Math.min(MAX_BLOCK_SECONDS, Math.round((Date.now() - t0) / 1000));
    const r = await api.post("/api/block/done", {
      key: block.key, seconds, score: res.score, max: res.max, content_id: res.content_id || block.item_id || null,
    });
    updateCounters(r);
    if (block !== todo[todo.length - 1]) await celebrate(root, S.wellDone, {}, 1300);
  }
  const state = await api.get("/api/state");
  updateCounters(state);
  const s2 = state.sittings && state.sittings[2];
  const rest = sitting === 1 && s2 && s2.blocks && s2.done < s2.blocks;
  const msg = rest ? S.breakTime
    : state.minutes_today >= state.goal_minutes ? S.goalDone : S.partsDone;
  const left = state.goal_minutes - state.minutes_today;
  const box = screen(root, h("div", { class: "celebrate" }, h("div", { class: "big-ico" }, msg.icon),
      h("h1", {}, t(S.wellDone)), h("h2", {}, t(msg)), hint(msg.am)),
    h("div", { class: "stat-row" },
      h("div", { class: "stat" }, h("div", { class: "num" }, "🔥 " + state.streak), h("div", { class: "lbl" }, S.streakLabel.en)),
      h("div", { class: "stat" }, h("div", { class: "num" }, "⭐ " + state.words_known), h("div", { class: "lbl" }, S.knownLabel.en))),
    goalBar(state.minutes_today, state.goal_minutes));
  const bar = h("div", { class: "actions" });
  if (!rest && left > 0) bar.append(button({ ...S.keepGoing, en: t(S.keepGoing, { left }) }, () => go("practice"), "primary"));
  bar.append(button(S.home, () => go(""), !rest && left > 0 ? "" : "primary"));
  box.append(bar);
}
