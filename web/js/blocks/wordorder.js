// "Build the sentence" with coloured blocks. The orange block (the action word) is always in place 2.
import { play } from "../audio.js";
import { S } from "../strings.js";
import { h, say, screen, shuffle, wait } from "../ui.js";

export function buildSentence(root, example) {
  return new Promise((resolve) => {
    const target = example.blocks;
    let pos = 0;
    let mistakes = 0;
    const row = h("div", { class: "blocks-row" });
    const slots = target.map((_, i) => {
      const s = h("div", { class: "slot" }, h("span", { class: "slot-num" }, i + 1),
        h("span", { class: "wblock", style: "visibility:hidden" }, "…"));
      row.append(s);
      return s;
    });
    const msg = h("div", { class: "feedback" });
    const pool = h("div", { class: "blocks-row" });
    const order = shuffle(target.map((b, i) => i));
    // make sure the shuffle is not already right
    if (order.every((v, i) => v === i) && order.length > 1) order.push(order.shift());
    for (const i of order) {
      const [text, role] = target[i];
      const b = h("button", {
        class: `wblock r-${role}`, lang: "de",
        onclick: async () => {
          // accept any block with the same text (e.g. two "die")
          if (text === target[pos][0]) {
            slots[pos].replaceChildren(h("span", { class: "slot-num" }, pos + 1),
              h("span", { class: `wblock r-${role} placed`, lang: "de" }, text));
            b.remove();
            pos++;
            msg.textContent = "";
            if (pos === target.length) {
              msg.className = "feedback good";
              msg.textContent = "🎉 " + example.de;
              await play(example.audio);
              await wait(600);
              resolve(mistakes === 0);
            }
          } else {
            mistakes++;
            b.classList.remove("tryagain");
            void b.offsetWidth;
            b.classList.add("tryagain");
            setTimeout(() => b.classList.remove("tryagain"), 400);
            msg.className = "feedback soft";
            msg.textContent = S.tryAgain.icon + " " + S.tryAgain.en +
              (target[pos][1] === "verb" ? " " + S.verbRule.icon + " " + S.verbRule.en : "");
          }
        },
      }, text);
      pool.append(b);
    }
    screen(root, say(S.sentence), target.some((b) => b[1] === "verb") ? say(S.verbRule) : null,
      h("div", { class: "muted center" }, "🇬🇧 " + example.en), row, pool, msg);
  });
}
