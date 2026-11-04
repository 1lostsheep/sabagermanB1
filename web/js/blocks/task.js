// Small real-life task: read a note, choose a reply, or fill in a form.
import { S } from "../strings.js";
import { h, hint, say, screen, button, wait } from "../ui.js";
import { askQuestions, paper } from "./common.js";

function matches(given, expected) {
  const norm = (s) => (s || "").normalize("NFC").trim().toLowerCase()
    .replace(/ae/g, "ä").replace(/oe/g, "ö").replace(/ue/g, "ü").replace(/ss/g, "ß")
    .replace(/\s+/g, " ").replace(/^[\s.,!?;:]+|[\s.,!?;:]+$/g, "");
  return [].concat(expected).some((e) => norm(e) === norm(given));
}

async function fillForm(root, it) {
  return new Promise((resolve) => {
    let tries = 0;
    const inputs = it.fields.map((f) => h("input", { type: "text", lang: "de", spellcheck: "false", autocomplete: "off" }));
    const msg = h("div", { class: "feedback" });
    const fields = it.fields.map((f, i) => h("div", { class: "field" },
      h("label", {}, h("b", { lang: "de" }, f.label_de), " · ", h("span", { class: "muted" }, f.label_en), " ", hint(f.hint_am, `${it.id}:${f.label_de}`)),
      inputs[i]));
    let firstScore = null;
    const check = button(S.check, async () => {
      tries++;
      let right = 0;
      it.fields.forEach((f, i) => {
        const ok = matches(inputs[i].value, f.answer);
        inputs[i].style.borderColor = ok ? "var(--good)" : "var(--amber)";
        if (ok) right++;
        else if (tries >= 2) { inputs[i].value = [].concat(f.answer)[0]; inputs[i].style.borderColor = "var(--good)"; }
      });
      if (firstScore === null) firstScore = right;
      if (right === it.fields.length || tries >= 2) {
        msg.className = "feedback good";
        msg.textContent = right === it.fields.length ? "🎉 Super!" : "👉 " + S.thisOne.en;
        check.disabled = true;
        await wait(right === it.fields.length ? 1200 : 3000);
        resolve(firstScore);
      } else {
        msg.className = "feedback soft";
        msg.textContent = S.tryAgain.icon + " " + S.tryAgain.en;
      }
    }, "primary");
    screen(root, say(S.fillForm), h("div", { class: "muted" }, it.prompt_en), paper(it.material_title, it.material_de),
      ...fields, msg, check);
  });
}

export async function run(root, block) {
  const it = block.item;
  const intro = { icon: it.kind === "choose_reply" ? "💬" : it.kind === "fill_form" ? "📝" : "📄", en: it.prompt_en, am: it.prompt_hint_am };
  if (it.kind === "fill_form") {
    const score = await fillForm(root, it);
    return { score, max: it.fields.length, content_id: it.id };
  }
  const score = await askQuestions(root, it.questions,
    () => [say(intro, {}, it.id), paper(it.material_title, it.material_de)], it.id);
  return { score, max: it.questions.length, content_id: it.id };
}
