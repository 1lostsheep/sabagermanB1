// Paz's page: weekly summary, placement levels (with override), recordings, hint flags, API usage.
import { api } from "../api.js";
import { go } from "../main.js";
import { h, screen } from "../ui.js";

const LEVEL_NAME = { below_a2: "below A2", a2: "A2", b1: "B1" };
const AREAS = [["speaking", "Speaking"], ["writing", "Writing"], ["listening_reading", "Listening + Reading (DTZ area)"],
               ["listening", "Listening"], ["reading", "Reading"], ["vocabulary", "Vocabulary (info)"]];

async function login(root) {
  return new Promise((resolve) => {
    const pin = h("input", { type: "password", inputmode: "numeric", maxlength: "8", placeholder: "PIN" });
    const msg = h("div", { class: "muted" });
    const tryLogin = async () => {
      try { await api.post("/api/paz/login", { pin: pin.value }); resolve(); }
      catch { msg.textContent = "Wrong PIN. It is PAZ_PIN in the .env file (default 1234). Number pad: check Num Lock is on."; pin.value = ""; }
    };
    pin.addEventListener("keydown", (e) => e.key === "Enter" && tryLogin());
    screen(root, h("div", { class: "paz" }, h("h1", {}, "🔒 Paz"), pin, msg,
      h("div", { class: "stat-row" }, h("button", { class: "btn", onclick: tryLogin }, "Open"),
        h("button", { class: "btn", onclick: () => go("") }, "Back to Saba"))));
    pin.focus();
  });
}

export async function render(root) {
  let d;
  try { d = await api.get("/api/paz/summary"); }
  catch (e) {
    if (e.status !== 401) throw e;
    await login(root);
    d = await api.get("/api/paz/summary");
  }
  const maxMin = Math.max(30, ...d.days.map((x) => x.minutes));
  const kpi = (n, l) => h("div", { class: "card" }, h("div", { class: "kpi" }, n ?? "–"), h("div", { class: "muted" }, l));

  const levels = d.placement ? h("table", {},
    h("tr", {}, h("th", {}, "Area"), h("th", {}, "Auto"), h("th", {}, "Your override")),
    ...AREAS.map(([key, label]) => {
      const sel = h("select", {
        onchange: async () => { await api.post("/api/paz/override", { area: key, level: sel.value }); render(root); },
      }, h("option", { value: "" }, "—"), ...Object.entries(LEVEL_NAME).map(([v, n]) =>
        h("option", { value: v, selected: d.placement.override && d.placement.override[key] === v }, n)));
      return h("tr", {}, h("td", {}, label), h("td", {}, LEVEL_NAME[d.placement.auto?.[key]] || "–"),
        h("td", {}, key === "vocabulary" ? "" : sel));
    })) : h("p", {}, "Placement test not done yet.");

  screen(root, h("div", { class: "paz", style: "display:flex;flex-direction:column;gap:16px" },
    h("h1", {}, "Weekly summary"),
    h("div", { class: "muted" }, `7 days up to ${d.today}`),
    h("div", { class: "grid" },
      kpi(d.minutes_week + " min", "studied this week"),
      kpi(d.streak, "day streak"),
      kpi(d.words_learned_week, "new words this week"),
      kpi(`${d.words_known} / ${d.words_total}`, `words known / met (of ${d.words_available} available)`),
      kpi(d.review_accuracy === null ? "–" : d.review_accuracy + "%", `flashcards right first time (${d.reviews} answers)`),
      kpi(d.letters_week, "letters practised")),
    h("div", { class: "card" }, h("h2", {}, "Minutes per day"),
      h("table", {}, ...d.days.map((x) => h("tr", {},
        h("td", { style: "width:110px" }, new Date(x.day + "T12:00").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })),
        h("td", {}, h("div", { class: "bar", style: `width:${Math.round(100 * x.minutes / maxMin)}%` })),
        h("td", { style: "width:120px" }, `${x.minutes} min · ${x.blocks} blocks`))))),
    h("div", { class: "card" }, h("h2", {}, "Weak spots"),
      h("p", {}, h("b", {}, "Block scores this week (lowest first): "),
        d.weak_blocks.filter((b) => b.percent !== null).map((b) => `${b.block} ${b.percent}%`).join(" · ") || "no data yet"),
      h("p", {}, h("b", {}, "Words she misses most: "),
        d.weak_words.map((w) => `${w.de} (${w.en}) ×${w.lapses}`).join(" · ") || "none yet")),
    h("div", { class: "card" }, h("h2", {}, "Levels"),
      d.placement && d.placement.finished ? h("div", { class: "muted" }, `Placement finished ${d.placement.finished.slice(0, 10)}. ` +
        (d.placement.outlook_pass ? "✅ These levels would pass the DTZ (B1 rule since 1 Nov 2026)." :
          "Not yet at the DTZ pass rule: B1 speaking + B1 in one other area + A2 in the third.")) : null,
      levels,
      d.recordings.length ? h("div", {}, h("h3", {}, "Her recordings"), ...d.recordings.map((r) =>
        h("div", {}, r.created_at.replace("T", " "), " ", h("audio", { controls: true, src: `/api/paz/recording/${r.id}` })))) : null,
      d.writings.length ? h("div", {}, h("h3", {}, "Latest writing"), ...d.writings.filter((w) => w.text).map((w) =>
        h("p", {}, h("b", {}, `${w.day} · ${w.kind}: `), h("span", { lang: "de" }, w.text)))) : null),
    h("div", { class: "card" }, h("h2", {}, `Pictures flagged as not clear (${d.picture_flags.length})`),
      d.picture_flags.length ? h("div", { class: "grid" }, ...d.picture_flags.map((f) =>
        h("div", { class: "card", style: "text-align:center" },
          h("img", { src: f.picture, style: "width:110px;height:110px;object-fit:contain" }),
          h("div", {}, h("b", { lang: "de" }, f.label || f.item_id)),
          h("div", { class: "muted" }, `${f.item_id} · flagged ${f.n}× · ${f.last.slice(0, 10)}`)))) :
        h("p", { class: "muted" }, "None."),
      h("p", { class: "muted" }, "To swap one: ask Claude Code, or find a better picture with " +
        "tools/arasaac.py and change \"picture\" in the batch's words.json. The flag disappears once the picture changes.")),
    h("div", { class: "card" }, h("h2", {}, `Amharic hints flagged by Saba (${d.hint_flags.length})`),
      d.hint_flags.length ? h("table", {}, ...d.hint_flags.map((f) => h("tr", {},
        h("td", {}, f.ts.slice(0, 10)), h("td", {}, f.item_id), h("td", { lang: "am" }, f.hint_text)))) :
        h("p", { class: "muted" }, "None. Fix flagged hints in the next /new-month batch.")),
    h("div", { class: "card" }, h("h2", {}, "Claude API this month"),
      h("p", {}, `${d.api_usage.calls} calls · ${d.api_usage.input_tokens + d.api_usage.output_tokens} tokens · ` +
        `≈ €${d.api_usage.est_cost_eur.toFixed(2)} of €${d.api_budget_eur} budget`),
      h("p", { class: "muted" }, "Used from Phase 2 (speaking, letter marking, monthly check).")),
    h("div", { class: "card muted" }, "Pictures: ARASAAC (arasaac.org) by Sergio Palao, Government of Aragón, CC BY-NC-SA. Voices: Google Cloud Text-to-Speech or Piper (see LICENSES.md)."),
    h("button", { class: "btn", onclick: () => go("") }, "← Back to Saba's app")));
}
