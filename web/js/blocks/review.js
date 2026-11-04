// Picture flashcards. Mistakes come back at the end of the session (practice only;
// the schedule uses the first answer) and first in tomorrow's review.
import { api } from "../api.js";
import { player, play } from "../audio.js";
import { S } from "../strings.js";
import { choose, germanWord, h, picture, say, screen, shuffle, steps, wait, celebrate } from "../ui.js";

async function card(root, w, n, total, mode) {
  const opts = shuffle([w, ...w.distractors]);
  const answer = opts.indexOf(w);
  if (mode === "listen") {
    const box = screen(root, steps(n, total), say(S.tapPicture), player(w.audio, { autoplay: true, compact: true }));
    return choose(box, opts.map((o) => picture(o.picture, "")), answer, { columns: opts.length, cls: "pic" });
  }
  const box = screen(root, steps(n, total), say(S.tapWord), picture(w.picture, w.en));
  const ok = await choose(box, opts.map((o) => germanWord(o)), answer);
  await play(w.audio);
  return ok;
}

/**
 * cards: words with distractors. record=true sends results to the scheduler.
 */
export async function runCards(root, cards, { record = true, mode = "review" } = {}) {
  if (!cards.length) {
    await celebrate(root, S.noReview, {}, 1500);
    return { score: 0, max: 0 };
  }
  const queue = cards.map((c, i) => ({ c, mode: i % 2 ? "picture" : "listen", retry: false }));
  let score = 0;
  let n = 0;
  const total = queue.length;
  while (queue.length) {
    const q = queue.shift();
    if (!q.retry) n++;
    const ok = await card(root, q.c, Math.min(n, total), total, q.mode);
    if (!q.retry) {
      if (ok) score++;
      if (record) api.post("/api/review", { word_id: q.c.id, correct: ok, mode }).catch(() => {});
      if (!ok) queue.push({ ...q, retry: true, mode: "picture" });
    }
    await wait(200);
  }
  return { score, max: total };
}

export async function run(root) {
  const { cards } = await api.get("/api/review");
  return runCards(root, cards);
}
