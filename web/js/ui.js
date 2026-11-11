// UI kit: big buttons, icon + text instructions, Amharic hints, gentle feedback.
import { api } from "./api.js";
import { S, fill } from "./strings.js";

export const ctx = { name: "Saba" };

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function t(s, vars) {
  return fill(s.en, { name: ctx.name, ...vars });
}

/** Tap-to-show Amharic hint, off by default, with a "this help is not right" flag. */
export function hint(am, itemId) {
  if (!am) return null;
  const box = h("span", { class: "hint-text", hidden: true, lang: "am" }, fill(am, { name: ctx.name }));
  const flag = h("button", {
    class: "flag", hidden: true, title: S.hintWrong.en,
    onclick: async (e) => {
      e.stopPropagation();
      try { await api.post("/api/hint-flag", { item_id: itemId || "ui", hint_text: am }); } catch {}
      flag.replaceWith(h("span", { class: "flag-thanks" }, S.thanksFlag.icon + " " + S.thanksFlag.en));
    },
  }, S.hintWrong.icon, " ", S.hintWrong.en);
  const btn = h("button", {
    class: "hint-btn", "aria-label": "Amharic help", title: "Amharic help",
    onclick: (e) => {
      e.stopPropagation();
      const show = box.hidden;
      box.hidden = !show;
      flag.hidden = !show;
      btn.classList.toggle("on", show);
    },
  }, "💡");
  return h("span", { class: "hint" }, btn, box, flag);
}

/** One instruction line: big icon, short English, optional Amharic hint. */
export function say(s, vars, itemId) {
  return h("div", { class: "instruction" },
    h("span", { class: "ico" }, s.icon),
    h("span", { class: "txt" }, t(s, vars)),
    hint(s.am, itemId || "ui:" + s.en.slice(0, 30)));
}

export function button(s, onclick, cls = "") {
  return h("button", { class: "btn big " + cls, onclick },
    h("span", { class: "ico" }, s.icon), h("span", {}, t(s)));
}

export function screen(root, ...children) {
  root.replaceChildren(h("section", { class: "screen" }, ...children));
  root.classList.toggle("scroll", location.hash.startsWith("#/paz"));  // only Paz's report scrolls
  window.scrollTo(0, 0);
  return root.firstChild;
}

export function steps(n, total) {
  return h("div", { class: "steps", "aria-label": `${n} of ${total}` },
    ...Array.from({ length: total }, (_, i) => h("span", { class: i < n ? "dot on" : "dot" })));
}

/** A picture. With flag = {item, label} it can get a small "picture not clear" button. */
export function picture(src, alt = "", flag = null) {
  return h("img", { class: "picture", src, alt, draggable: "false",
                    "data-flag-item": flag && flag.item, "data-flag-label": flag && flag.label });
}

/** Small 🚩 button: flags a picture as not clear. Paz sees it on his page. */
export function pictureFlag(img, { hidden = false } = {}) {
  if (!img || img.tagName !== "IMG" || !img.dataset.flagItem) return null;
  const btn = h("button", {
    class: "pic-flag", type: "button", title: "This picture is not clear", hidden,
    onclick: async (e) => {
      e.stopPropagation();
      e.preventDefault();
      btn.disabled = true;
      try {
        await api.post("/api/picture-flag", {
          item_id: img.dataset.flagItem, label: img.dataset.flagLabel || "", picture: new URL(img.src).pathname });
      } catch {}
      btn.textContent = S.thanksFlag.icon + " " + S.thanksFlag.en;
    },
  }, "🚩 Picture not clear?");
  return btn;
}

/** A standalone picture with its flag button underneath.
 *  afterAnswer: the flag only shows once the question on this screen is answered. */
export function flaggedPicture(src, alt, flag, { afterAnswer = false } = {}) {
  const img = picture(src, alt, flag);
  return h("div", { class: "pic-wrap" }, img, pictureFlag(img, { hidden: afterAnswer }));
}

/** Wrap a choice button so a picture option gets its flag button below (never inside the button).
 *  Flags under answer options stay hidden until the right answer is found. */
export function choiceCell(btn, opt) {
  const flag = pictureFlag(opt, { hidden: true });
  return flag ? h("div", { class: "pic-opt" }, btn, flag) : btn;
}

/** Show the hidden 🚩 flags on this screen. Returns true if there are any. */
export function revealFlags(el) {
  const scope = (el && el.closest(".screen")) || document;
  const flags = [...scope.querySelectorAll(".pic-flag")];
  flags.forEach((f) => (f.hidden = false));
  return flags.length > 0;
}

/** Two columns on a wide screen: material on the left, the task on the right. */
export function split(left, right) {
  return h("div", { class: "split" },
    h("div", { class: "col col-left" }, ...[].concat(left)),
    h("div", { class: "col col-right" }, ...[].concat(right)));
}

/** The bar at the bottom of the screen that holds Next/Done, so it is always visible. */
export function actionBar(el) {
  const scr = (el && el.closest(".screen")) || el;
  let bar = scr.querySelector(":scope > .actions");
  if (!bar) {
    bar = h("div", { class: "actions" });
    scr.append(bar);
  }
  return bar;
}

/** Article colour class: der blue, die purple, das green. */
export function articleClass(article) {
  return article ? "art-" + article : "";
}

export function germanWord(w) {
  const el = h("span", { class: "de " + articleClass(w.article), lang: "de" });
  if (w.article && w.de.startsWith(w.article + " ")) {
    el.append(h("span", { class: "article" }, w.article), " " + w.de.slice(w.article.length + 1));
  } else el.append(w.de);
  return el;
}

const PRAISE = ["Super!", "Great!", "Wonderful!", "Very good!", "Yes!", "Perfect!"];
export function praiseWord() {
  return PRAISE[Math.floor(Math.random() * PRAISE.length)];
}

export function wait(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Multiple choice. options: array of {el: Node} or strings. Resolves with true if right on first try.
 * Wrong: the button turns soft amber and "Try again". After 2 wrong tries the right one is shown.
 */
export function choose(container, options, answer, { columns = 1, cls = "" } = {}) {
  return new Promise((resolve) => {
    let wrong = 0;
    const msg = h("div", { class: "feedback", "aria-live": "polite" });
    const buttons = options.map((opt, i) =>
      h("button", {
        class: "btn choice " + cls,
        onclick: async () => {
          if (i === answer) {
            buttons.forEach((b) => (b.disabled = true));
            buttons[i].classList.add("right");
            buttons[i].classList.remove("show-right");
            msg.className = "feedback good";
            msg.textContent = (wrong === 0 ? "🎉 " + praiseWord() : "👍 " + "Yes, that's it!");
            if (revealFlags(container)) {
              // pictures on screen: stay here so a picture can be flagged, then tap Next
              await nextButton(container);
            } else {
              await wait(900);
            }
            resolve(wrong === 0);
          } else {
            wrong++;
            buttons[i].classList.add("tryagain");
            buttons[i].disabled = true;
            msg.className = "feedback soft";
            if (wrong >= 2) {
              msg.textContent = S.thisOne.icon + " " + S.thisOne.en;
              buttons[answer].classList.add("show-right");
            } else msg.textContent = S.tryAgain.icon + " " + S.tryAgain.en;
          }
        },
      }, typeof opt === "string" || opt instanceof Node ? opt : opt.el));
    container.append(h("div", { class: `choices cols-${columns}` }, ...buttons.map((b, i) => choiceCell(b, options[i]))), msg);
  });
}

export function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** Big friendly message between steps. */
export async function celebrate(root, s, vars, ms = 1600) {
  screen(root, h("div", { class: "celebrate" },
    h("div", { class: "big-ico" }, s.icon), h("h1", {}, t(s, vars)), hint(s.am)));
  await wait(ms);
}

/** "⏱️ 12 / 30 minutes today" with a bar. */
export function goalBar(minutes, goal) {
  const pct = Math.min(100, Math.round((100 * minutes) / Math.max(goal, 1)));
  return h("div", { class: "goal" },
    h("div", { class: "goal-txt" }, `⏱️ ${minutes} / ${goal} `, S.goalLabel.en, " ", hint(S.goalLabel.am),
      minutes >= goal ? " 🎯" : ""),
    h("div", { class: "goal-track" }, h("div", { class: "goal-fill", style: `width:${pct}%` })));
}

export function updateCounters({ streak, words_known }) {
  if (streak !== undefined) document.querySelector("#streak b").textContent = streak;
  if (words_known !== undefined) document.querySelector("#known b").textContent = words_known;
}

/** Wait for one tap on a big "Next" button (in the screen's bottom action bar). */
export function nextButton(container, s = S.next) {
  return new Promise((resolve) => actionBar(container).append(button(s, () => resolve(), "primary")));
}
