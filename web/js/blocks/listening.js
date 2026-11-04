// Listening: slow first, then normal speed, then 2-3 exam-style questions.
import { player } from "../audio.js";
import { S } from "../strings.js";
import { h, nextButton, say, screen } from "../ui.js";
import { askQuestions } from "./common.js";

export async function run(root, block) {
  const it = block.item;
  let box = screen(root, say(S.listeningIntro), h("h2", { class: "center" }, "🎧 " + it.title_en),
    say(S.slow), player(it.audio, { autoplay: true, rate: 0.75 }));
  await nextButton(box);
  box = screen(root, say(S.normal), h("h2", { class: "center" }, "🎧 " + it.title_en),
    player(it.audio, { autoplay: true, rate: 1 }));
  await nextButton(box);
  const score = await askQuestions(root, it.questions,
    () => [player(it.audio, { compact: true })], it.id);
  return { score, max: it.questions.length, content_id: it.id };
}
