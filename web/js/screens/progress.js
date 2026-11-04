// Saba's progress: streak calendar, words I know, minutes. Only praise.
import { api } from "../api.js";
import { S } from "../strings.js";
import { h, hint, say, screen } from "../ui.js";

const DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

export async function render(root) {
  const p = await api.get("/api/progress");
  const active = new Set(p.active_days);
  const today = new Date(p.today + "T12:00");  // the server's date
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  // last 4 weeks, starting on a Monday
  const start = new Date(today);
  start.setDate(today.getDate() - ((today.getDay() + 6) % 7) - 21);
  const cells = DAYS.map((d) => h("div", { class: "hd" }, d));
  for (let i = 0; i < 28; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const k = iso(d);
    const future = iso(d) > iso(today);
    const on = active.has(k);
    cells.push(h("div", { class: "d" + (on ? " on" : "") + (k === iso(today) ? " today" : "") },
      future ? "" : on ? "⭐" : d.getDay() === 0 ? "😴" : String(d.getDate())));
  }
  const stat = (num, s) => h("div", { class: "stat" }, h("div", { class: "num" }, `${s.icon} ${num}`),
    h("div", { class: "lbl" }, s.en, " ", hint(s.am)));
  screen(root, h("h1", {}, "📈 ", S.myProgress.en),
    h("div", { class: "stat-row" }, stat(p.streak, S.streakLabel), stat(p.words_known, S.knownLabel)),
    h("div", { class: "stat-row" }, stat(p.words_learned, S.learnedLabel), stat(p.minutes_today, S.minutesToday)),
    h("div", { class: "cal" }, ...cells),
    say({ icon: "💛", en: `This week you studied for ${p.minutes_week} minutes. Every day counts!`,
          am: `በዚህ ሳምንት ${p.minutes_week} ደቂቃ ተምረሻል። እያንዳንዱ ቀን ይቆጠራል!` }));
}
