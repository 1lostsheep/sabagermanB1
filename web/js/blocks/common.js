// Shared pieces for lesson blocks.
import { S } from "../strings.js";
import { choose, h, hint, say, screen, split, steps } from "../ui.js";

/**
 * Ask questions one per screen. `top()` returns the material that stays visible
 * (a text, a note, an audio player). With layout "split" the material is on the left and
 * the question on the right, so everything fits on one screen.
 * Returns the number right on the first try.
 */
export async function askQuestions(root, questions, top = () => [], itemId = "", { layout = "split" } = {}) {
  let score = 0;
  for (let i = 0; i < questions.length; i++) {
    const q = questions[i];
    const task = h("div", { class: "col-task" },
      say(S.answer),
      h("h2", { lang: "de" }, "❓ " + q.q_de),
      h("div", { class: "muted" }, q.q_en, " ", hint(q.hint_am, `${itemId}:q${i + 1}`)));
    const material = top();
    let box;
    if (layout === "split" && material.length) {
      const right = h("div", {}, task);
      screen(root, steps(i + 1, questions.length), split(material, right));
      box = right;
    } else {
      box = screen(root, steps(i + 1, questions.length), ...material, task);
    }
    if (await choose(box, q.options, q.answer)) score++;
  }
  return score;
}

export function paper(title, text, cls = "") {
  return h("div", { class: "paper " + cls, lang: "de" }, title ? h("h3", {}, title) : null, text);
}

export function glossary(items, itemId) {
  if (!items || !items.length) return null;
  return h("div", { class: "gloss" }, ...items.map((g) =>
    h("div", { class: "gloss-item" }, h("b", { lang: "de" }, g.de), " = ", g.en, " ", hint(g.hint_am, `${itemId}:${g.de}`))));
}
