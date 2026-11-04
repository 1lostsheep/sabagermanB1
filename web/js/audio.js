// Audio player: big Listen button + speed buttons. Can always replay and slow down.
import { h } from "./ui.js";
import { S } from "./strings.js";

let current = null; // only one sound at a time

export function stopAll() {
  if (current) { current.pause(); current = null; }
}

export function play(src, rate = 1) {
  stopAll();
  const a = new Audio(src);
  a.preservesPitch = true;
  a.playbackRate = rate;
  current = a;
  return new Promise((resolve) => {
    a.onended = () => resolve(true);
    a.onerror = () => resolve(false);
    a.play().catch(() => resolve(false));
  });
}

const SPEEDS = [
  { rate: 1, s: S.normal },
  { rate: 0.75, s: S.slow },
  { rate: 0.6, s: S.verySlow },
];

/**
 * player(src, {rate, autoplay, label, compact}) -> element
 * The element has .play() and .setRate(r). The chosen speed is remembered for the session.
 */
export function player(src, opts = {}) {
  let rate = opts.rate ?? Number(sessionStorage.getItem("rate") || 1);
  const playBtn = h("button", { class: "btn big listen", onclick: () => go() },
    h("span", { class: "ico" }, S.listen.icon), h("span", {}, opts.label || S.listen.en));
  const speedBtns = SPEEDS.map((sp) =>
    h("button", {
      class: "btn speed" + (sp.rate === rate ? " on" : ""), title: sp.s.en, "aria-label": sp.s.en,
      onclick: () => { setRate(sp.rate); go(); },
    }, h("span", { class: "ico" }, sp.s.icon), opts.compact ? null : h("span", { class: "lbl" }, sp.s.en)));
  const el = h("div", { class: "player" + (opts.compact ? " compact" : "") }, playBtn, h("div", { class: "speeds" }, ...speedBtns));

  function setRate(r) {
    rate = r;
    try { sessionStorage.setItem("rate", String(r)); } catch {}
    speedBtns.forEach((b, i) => b.classList.toggle("on", SPEEDS[i].rate === r));
  }
  async function go() {
    el.classList.add("playing");
    const ok = await play(src, rate);
    el.classList.remove("playing");
    if (opts.onended) opts.onended(ok);
    return ok;
  }
  el.play = go;
  el.setRate = setRate;
  if (opts.autoplay) setTimeout(go, 300);
  return el;
}
