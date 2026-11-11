import { api } from "../api.js";
import { go } from "../main.js";
import { S } from "../strings.js";
import { button, ctx, goalBar, h, hint, say, screen, t, updateCounters } from "../ui.js";

export async function render(root) {
  const s = await api.get("/api/state");
  ctx.name = s.name;
  updateCounters(s);

  const hello = h("div", { class: "home-hello" }, "👋 ", t(S.hello), " ", hint(S.hello.am));
  const stats = h("div", { class: "stat-row" },
    h("div", { class: "stat" }, h("div", { class: "num" }, "🔥 " + s.streak), h("div", { class: "lbl" }, S.streakLabel.en)),
    h("div", { class: "stat" }, h("div", { class: "num" }, "⭐ " + s.words_known), h("div", { class: "lbl" }, S.knownLabel.en)));
  const more = h("div", { class: "stat-row" },
    button(S.practiseMore, () => go("practice")),
    button(S.myProgress, () => go("progress")));

  if (s.placement !== "done") {
    screen(root, hello, say(S.placementIntro),
      button(S.start, () => go("placement"), "primary huge"));
    return;
  }
  if (!s.has_content) {
    screen(root, hello, say(S.noContent));
    return;
  }
  const parts = [];
  if (s.plan_kind === "rest") {
    parts.push(say(S.restDay));
    if (s.sittings[1].blocks && s.sittings[1].done < s.sittings[1].blocks)
      parts.push(button(S.practiseMore, () => go("lesson/1"), "primary"));
  } else {
    if (s.plan_kind === "weekly_test") parts.push(say(S.weekTest));
    for (const n of [1, 2]) {
      const st = s.sittings[n];
      if (!st || !st.blocks) continue;
      const finished = st.done >= st.blocks;
      const label = n === 1 ? S.part1 : S.part2;
      const b = button({ ...label, icon: finished ? "✅" : label.icon }, () => go("lesson/" + n),
        finished ? "sit-done" : "primary huge");
      b.append(h("span", { class: "muted" }, ` ${st.done}/${st.blocks}`));
      parts.push(b);
    }
    const all = [1, 2].every((n) => !s.sittings[n].blocks || s.sittings[n].done >= s.sittings[n].blocks);
    if (all) {
      if (s.minutes_today >= s.goal_minutes) parts.unshift(say(S.goalDone));
      else {
        parts.unshift(say(S.partsDone));
        parts.push(button({ ...S.keepGoing, en: t(S.keepGoing, { left: s.goal_minutes - s.minutes_today }) },
          () => go("practice"), "primary huge"));
      }
    }
  }
  screen(root, hello, stats, goalBar(s.minutes_today, s.goal_minutes), ...parts, more);
}
