// Speaking with the AI partner comes in Phase 2. Until then: listen and repeat.
import { play } from "../audio.js";
import { S } from "../strings.js";
import { actionBar, button, h, hint, say, screen } from "../ui.js";

function miniPlayer(src) {
  const b = (icon, rate, title) => h("button", { class: "btn speed", title, "aria-label": title, onclick: () => play(src, rate) }, icon);
  return h("div", { class: "mini-player" }, b("🔊", 1, S.listen.en), b("🐢", 0.75, S.slow.en));
}

export async function run(root, block) {
  const phrases = block.phrases || [];
  await new Promise((resolve) => {
    const box = screen(root,
      h("div", { class: "coming" }, h("span", { class: "ico" }, "🎤"), h("b", {}, S.speakingSoon.en), hint(S.speakingSoon.am)),
      phrases.length ? say(S.repeatAfter) : null,
      phrases.length ? h("div", { class: "phrase-grid" }, ...phrases.map((p) => h("div", { class: "phrase" },
        h("div", { class: "txt" }, h("div", { class: "de", lang: "de" }, p.de),
          h("div", { class: "muted" }, p.en, " ", hint(p.hint_am, p.id))),
        miniPlayer(p.audio)))) : null);
    actionBar(box).append(button(S.done, resolve, "primary"));
  });
  return { score: null, max: null };
}
