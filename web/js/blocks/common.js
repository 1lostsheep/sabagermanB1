// Shared pieces for lesson blocks.
import { S } from "../strings.js";
import { choose, h, hint, say, screen, steps } from "../ui.js";

/**
 * Ask questions one per screen. `top()` returns the nodes shown above each question
 * (e.g. the text or an audio player), so the material stays visible.
 * Returns the number right on the first try.
 */
export async function askQuestions(root, questions, top = () => [], itemId = "") {
  let score = 0;
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i];
    const box = screen(root, steps(i + 1, questions.length), ...top(), say(S.answer),
      h("h2", { lang: "de" }, "❓ " + q.q_de),
      h("div", { class: "muted" }, q.q_en, " ", hint(q.hint_am, `${itemId}:q${i + 1}`)));
    if (await choose(box, q.options, q.answer)) score++;
  }
  return score;
}

export function paper(title, text) {
  return h("div", { class: "paper", lang: "de" }, title ? h("h3", {}, title) : null, text);
}

export function glossary(items, itemId) {
  if (!items || !items.length) return null;
  return h("div", { class: "gloss" }, ...items.map((g) =>
    h("div", { class: "gloss-item" }, h("b", { lang: "de" }, g.de), " = ", g.en, " ", hint(g.hint_am, `${itemId}:${g.de}`))));
}
