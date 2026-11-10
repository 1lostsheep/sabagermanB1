// 5 new words: picture + audio + German (article colour) + English + Amharic hint on tap.
// Then a quick check and one "build the sentence".
import { api } from "../api.js";
import { player } from "../audio.js";
import { S } from "../strings.js";
import { choose, flaggedPicture, germanWord, h, hint, nextButton, picture, say, screen, shuffle, steps } from "../ui.js";
import { buildSentence } from "./wordorder.js";

export async function run(root, block) {
  const words = block.words;
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const card = h("div", { class: "word-card" },
      flaggedPicture(w.picture, w.en, { item: w.id, label: w.de }), germanWord(w),
      w.plural ? h("div", { class: "muted", lang: "de" }, "➕ " + w.plural) : null,
      h("div", { class: "en" }, "🇬🇧 " + w.en, " ", hint(w.hint_am, w.id)),
      player(w.audio, { autoplay: true, compact: true }));
    const parts = [steps(i + 1, words.length), say(S.newWord), card];
    if (w.example) {
      parts.push(h("div", { class: "phrase" }, h("div", { class: "de", lang: "de" }, w.example.de),
        h("div", { class: "muted" }, w.example.en, " ", hint(w.example.hint_am, w.id + ":ex")),
        player(w.example.audio, { compact: true })));
    }
    const box = screen(root, ...parts);
    await nextButton(box);
  }

  // quick check: listen -> tap the picture (only among today's words)
  let score = 0;
  const order = shuffle(words);
  for (let i = 0; i < order.length; i++) {
    const w = order[i];
    const opts = shuffle([w, ...shuffle(words.filter((o) => o !== w && o.picture !== w.picture)).slice(0, 2)]);
    const box = screen(root, steps(i + 1, order.length), say(S.tapPicture), player(w.audio, { autoplay: true, compact: true }));
    if (await choose(box, opts.map((o) => picture(o.picture, "", { item: o.id, label: o.de })), opts.indexOf(w), { columns: opts.length, cls: "pic" })) score++;
  }

  // one sentence game
  const withBlocks = words.find((w) => w.example && w.example.blocks && w.example.blocks.length > 2);
  let max = order.length;
  if (withBlocks) {
    max++;
    if (await buildSentence(root, withBlocks.example)) score++;
  }
  await api.post("/api/words/learned", { word_ids: words.map((w) => w.id) });
  return { score, max };
}
