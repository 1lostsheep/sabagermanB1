// Speaking with the AI partner comes in Phase 2. Until then: listen and repeat.
import { player } from "../audio.js";
import { S } from "../strings.js";
import { button, h, hint, say, screen } from "../ui.js";

export async function run(root, block) {
  const phrases = block.phrases || [];
  await new Promise((resolve) => screen(root,
    h("div", { class: "coming" }, h("div", { class: "big-ico" }, "🎤"), h("h2", {}, S.speakingSoon.en), hint(S.speakingSoon.am)),
    phrases.length ? say(S.repeatAfter) : null,
    ...phrases.map((p) => h("div", { class: "phrase" },
      h("div", { class: "de", lang: "de" }, p.de), h("div", { class: "muted" }, p.en, " ", hint(p.hint_am, p.id)),
      player(p.audio, { compact: true }))),
    button(S.done, resolve, "primary")));
  return { score: null, max: null };
}
