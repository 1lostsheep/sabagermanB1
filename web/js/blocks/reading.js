// Reading: a real-life text (stays on screen), word help, then questions.
import { S } from "../strings.js";
import { nextButton, say, screen } from "../ui.js";
import { askQuestions, glossary, paper } from "./common.js";

export async function run(root, block) {
  const it = block.item;
  const box = screen(root, say(S.readText), paper(it.title_de, it.text_de), glossary(it.glossary, it.id));
  await nextButton(box);
  const score = await askQuestions(root, it.questions, () => [paper(it.title_de, it.text_de)], it.id);
  return { score, max: it.questions.length, content_id: it.id };
}
