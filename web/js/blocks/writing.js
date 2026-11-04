// Letters: learn the "recipe" with a model letter, then fill the gaps.
// Free writing with AI help comes in Phase 2 (she can already try; it is saved).
import { api } from "../api.js";
import { player } from "../audio.js";
import { S } from "../strings.js";
import { button, choose, h, hint, nextButton, say, screen, steps } from "../ui.js";

const ROLE_LABEL = { greeting: "👋 Hello", reason: "❓ Why", point: "📌 Point", closing: "🙏 Goodbye", name: "✍️ Name" };

function letterView(it, { gaps = [], filled = new Set(), showEn = true, current = -1 } = {}) {
  let pointNo = 0;
  return h("div", { class: "paper" }, ...it.lines.map((ln, i) => {
    const label = ln.role === "point" ? `📌 ${++pointNo}` : ROLE_LABEL[ln.role];
    let text = ln.de;
    const gap = gaps.find((g) => g.line === i);
    let content = [text];
    if (gap) {
      const at = text.indexOf(gap.word);
      const done = filled.has(i);
      content = [text.slice(0, at), h("span", { class: "gap" + (done ? " filled" : i === current ? " current" : "") }, done ? gap.word : "  ?  "),
                 text.slice(at + gap.word.length)];
    }
    return h("div", { class: "letter-line" }, h("span", { class: `role-tag role-${ln.role}` }, label),
      h("div", {}, h("div", { lang: "de" }, ...content), showEn && ln.en ? h("div", { class: "letter-en" }, ln.en) : null));
  }));
}

export async function run(root, block) {
  const it = block.item;
  // 1. the task and the recipe
  let box = screen(root, say(S.letterRecipe),
    h("div", { class: "instruction" }, h("span", { class: "ico" }, "✉️"),
      h("span", { class: "txt" }, it.task_en, h("br"), h("i", { lang: "de" }, it.task_de)), hint(it.task_hint_am, it.id)),
    h("div", { class: "gloss" }, ...it.points.map((p, i) =>
      h("div", { class: "gloss-item" }, `📌 ${i + 1}`, h("b", { lang: "de" }, p.de), " = ", p.en))));
  await nextButton(box);
  // 2. the model letter with audio
  box = screen(root, say({ icon: "👀", en: "Look at the letter. Listen.", am: "ደብዳቤውን ተመልከቺ። አዳምጪ።" }),
    player(it.audio, { compact: true }), letterView(it));
  await nextButton(box);
  // 3. fill the gaps
  let score = 0;
  const filled = new Set();
  for (let i = 0; i < it.gaps.length; i++) {
    const g = it.gaps[i];
    box = screen(root, steps(i + 1, it.gaps.length), say(S.fillGaps),
      letterView(it, { gaps: it.gaps, filled, showEn: false, current: g.line }));
    if (await choose(box, g.options, g.options.indexOf(g.word), { columns: Math.min(3, g.options.length) })) score++;
    filled.add(g.line);
  }
  api.post("/api/writing", { kind: "fill_in", prompt_id: it.id, auto_score: score }).catch(() => {});
  // 4. free writing: optional now, marked by AI in Phase 2
  await new Promise((resolve) => {
    const ta = h("textarea", { lang: "de", spellcheck: "false", placeholder: it.lines[0].de });
    screen(root, letterView(it, { gaps: it.gaps, filled, showEn: false }), say(S.writingSoon),
      say({ icon: "✍️", en: "Want to try? Write the letter again here.", am: "መሞከር ትፈልጊያለሽ? ደብዳቤውን እዚህ እንደገና ጻፊ።" }),
      ta,
      button(S.done, () => {
        if (ta.value.trim()) api.post("/api/writing", { kind: "free", prompt_id: it.id, text: ta.value.trim() }).catch(() => {});
        resolve();
      }, "primary"));
  });
  return { score, max: it.gaps.length, content_id: it.id };
}
