// Saturday mini test: this week's words as flashcards (results go to the scheduler).
import { S } from "../strings.js";
import { celebrate } from "../ui.js";
import { runCards } from "./review.js";

export async function run(root, block) {
  await celebrate(root, S.weekTest, {}, 1800);
  return runCards(root, block.words, { record: true, mode: "weekly" });
}
