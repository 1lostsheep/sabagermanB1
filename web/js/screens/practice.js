// Extra practice any time: due cards first, otherwise a mix of words she has met.
// Extra practice does not change the schedule.
import { api } from "../api.js";
import { runCards } from "../blocks/review.js";
import { go } from "../main.js";
import { S } from "../strings.js";
import { button, h, say, screen, t } from "../ui.js";

export async function render(root) {
  const { cards } = await api.get("/api/practice");
  if (!cards.length) {
    screen(root, say({ icon: "🌱", en: "Learn some new words first. Then you can practise here.", am: "መጀመሪያ አዳዲስ ቃላትን ተማሪ። ከዚያ እዚህ መለማመድ ትችያለሽ።" }),
      button(S.home, () => go(""), "primary"));
    return;
  }
  const res = await runCards(root, cards, { record: false });
  screen(root, h("div", { class: "celebrate" }, h("div", { class: "big-ico" }, "🌟"), h("h1", {}, t(S.wellDone)),
      h("h2", {}, `${res.score} / ${res.max}`)),
    button(S.practiseMore, () => render(root)), button(S.home, () => go(""), "primary"));
}
