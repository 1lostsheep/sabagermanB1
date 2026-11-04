// Placement test (about 45 min). Neutral feedback (it's a test), can pause and resume.
import { api } from "../api.js";
import { player, stopAll } from "../audio.js";
import { go, refreshCounters } from "../main.js";
import { S } from "../strings.js";
import { button, celebrate, h, hint, picture, say, screen, steps, t, wait } from "../ui.js";

const SECTION_TITLE = { words: S.secWords, listening: S.secListening, reading: S.secReading,
                        speaking: S.secSpeaking, writing: S.secWriting };

/** One try, no right/wrong shown. Resolves with the chosen index, or -1 for "I don't know". */
function chooseOnce(container, options, { columns = 1, cls = "" } = {}) {
  return new Promise((resolve) => {
    const pick = async (i, btn) => {
      all.forEach((b) => (b.disabled = true));
      btn.classList.add("right");
      await wait(450);
      resolve(i);
    };
    const all = options.map((opt, i) => {
      const b = h("button", { class: "btn choice " + cls, onclick: () => pick(i, b) },
        typeof opt === "string" ? opt : opt);
      return b;
    });
    const dk = h("button", { class: "btn", onclick: () => pick(-1, dk) }, S.dontKnow.icon + " " + S.dontKnow.en);
    all.push(dk);
    container.append(h("div", { class: `choices cols-${columns}` }, ...all.slice(0, -1)), dk);
  });
}

function pauseButton() {
  return h("button", { class: "btn", onclick: () => { stopAll(); go(""); } }, S.placementPause.icon + " " + S.placementPause.en);
}

export async function render(root) {
  const data = await api.get("/api/placement" + (location.hash.includes("restart") ? "?restart=1" : ""));
  if (data.done) return go("");
  const test = data.test;
  const prog = Object.assign({ section: 0, item: 0, ratings: [] }, data.progress);
  const save = () => api.post("/api/placement/progress", prog).catch(() => {});

  if (prog.section === 0 && prog.item === 0) {
    await new Promise((resolve) => screen(root,
      h("div", { class: "big-ico center" }, "🧭"), say(S.placementIntro),
      say({ icon: "⏱️", en: "It takes about 45 minutes. You can stop and come back.", am: "45 ደቂቃ ያህል ይወስዳል። ማቆም እና መመለስ ትችያለሽ።" }),
      button(S.start, resolve, "primary huge")));
  }

  const sections = test.sections;
  while (prog.section < sections.length) {
    const sec = sections[prog.section];
    if (prog.item === 0) {
      await new Promise((resolve) => screen(root, steps(prog.section + 1, sections.length),
        h("div", { class: "celebrate" }, h("div", { class: "big-ico" }, SECTION_TITLE[sec.id].icon),
          h("h1", {}, t(SECTION_TITLE[sec.id])), hint(SECTION_TITLE[sec.id].am)),
        button(S.start, resolve, "primary")));
    }
    if (sec.id === "words") await words(root, sec, prog, save);
    else if (sec.id === "listening") await questionsSection(root, sec, prog, save, "listening");
    else if (sec.id === "reading") await questionsSection(root, sec, prog, save, "reading");
    else if (sec.id === "speaking") await speaking(root, sec, prog, save);
    else if (sec.id === "writing") {
      const note = await writing(root, sec);
      await api.post("/api/placement/finish", { ratings: prog.ratings, note });
      await celebrate(root, S.placementDone, {}, 2500);
      await refreshCounters();
      return go("");
    }
    prog.section += 1;
    prog.item = 0;
    await save();
  }
}

async function answer(item_id, section, level, chosen, right, prog) {
  await api.post("/api/placement/answer", {
    item_id, section, level, answer: chosen, correct: chosen === right, progress: prog,
  });
}

async function words(root, sec, prog, save) {
  for (; prog.item < sec.items.length; prog.item++) {
    const it = sec.items[prog.item];
    const box = screen(root, steps(prog.item + 1, sec.items.length), say(S.tapPicture),
      player(it.audio, { autoplay: true, compact: true }));
    const pending = chooseOnce(box, it.pictures.map((p) => picture(p)), { columns: 2, cls: "pic" });
    box.append(pauseButton());
    const chosen = await pending;
    await answer(it.id, "words", it.level, chosen, it.answer, { ...prog, item: prog.item + 1 });
  }
}

async function questionsSection(root, sec, prog, save, kind) {
  for (; prog.item < sec.items.length; prog.item++) {
    const it = sec.items[prog.item];
    for (let qi = 0; qi < it.questions.length; qi++) {
      const q = it.questions[qi];
      const parts = [steps(prog.item + 1, sec.items.length)];
      if (kind === "listening") {
        parts.push(say(S.listeningIntro), player(it.audio, { autoplay: qi === 0, rate: 1 }));
      } else {
        parts.push(say(S.readText), h("div", { class: "paper", lang: "de" }, h("h3", {}, it.title_de), it.text_de));
      }
      parts.push(h("h2", { lang: "de" }, "❓ " + q.q_de), h("div", { class: "muted" }, q.q_en));
      const box = screen(root, ...parts);
      const pending = chooseOnce(box, q.options);
      box.append(pauseButton());
      const chosen = await pending;
      const last = qi === it.questions.length - 1;
      await answer(`${it.id}-q${qi + 1}`, kind, it.level, chosen, q.answer,
        { ...prog, item: last ? prog.item + 1 : prog.item });
    }
  }
}

async function speaking(root, sec, prog, save) {
  // item 0 = recording, items 1..n = can-do self ratings
  if (prog.item === 0) {
    await record(root, sec);
    prog.item = 1;
    await save();
  }
  for (; prog.item <= sec.can_do.length; prog.item++) {
    const cd = sec.can_do[prog.item - 1];
    const value = await new Promise((resolve) => {
      screen(root, steps(prog.item, sec.can_do.length), say(S.canYou),
        h("div", { class: "phrase" }, h("div", { class: "de" }, "🙋 " + cd.en, " ", hint(cd.hint_am, cd.id)),
          h("div", { class: "muted" }, "Example:"), h("div", { class: "de", lang: "de" }, cd.example_de),
          player(cd.audio, { compact: true })),
        h("div", { class: "choices cols-3" },
          button(S.rateYes, () => resolve(2)), button(S.rateLittle, () => resolve(1)), button(S.rateNo, () => resolve(0))));
    });
    prog.ratings = prog.ratings.filter((r) => r.id !== cd.id).concat([{ id: cd.id, level: cd.level, value }]);
    await save();
  }
}

async function record(root, sec) {
  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    stream = null;
  }
  return new Promise((resolve) => {
    if (!stream) {
      screen(root, say({ icon: "🎤", en: "No microphone found. That's OK!", am: "ማይክሮፎን አልተገኘም። ችግር የለውም!" }),
        button(S.next, resolve, "primary"));
      return;
    }
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = (e) => chunks.push(e.data);
    let timer = null;
    const clock = h("div", { class: "center", style: "font-size:2rem" }, "0:00");
    const recBtn = button(S.record, () => {
      chunks.length = 0;
      rec.start();
      const t0 = Date.now();
      timer = setInterval(() => {
        const s = Math.floor((Date.now() - t0) / 1000);
        clock.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
        if (s >= 180) stopBtn.click();
      }, 500);
      recBtn.hidden = true;
      stopBtn.hidden = false;
    }, "primary huge");
    const stopBtn = button(S.stop, () => {
      clearInterval(timer);
      rec.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop());
        const fd = new FormData();
        fd.append("audio", new Blob(chunks, { type: rec.mimeType || "audio/webm" }), "about-me.webm");
        fd.append("prompt_id", "about_me");
        try { await api.post("/api/placement/recording", fd); } catch {}
        await celebrate(root, S.recorded, {}, 1200);
        resolve();
      };
      rec.stop();
    }, "huge");
    stopBtn.hidden = true;
    const skip = h("button", { class: "btn", onclick: () => { stream.getTracks().forEach((tr) => tr.stop()); resolve(); } }, "⏭️ Skip");
    screen(root, say(S.recordIntro), h("h2", { class: "center", lang: "de" }, "🗣️ " + sec.prompt_de),
      h("div", { class: "muted center" }, "Name · country · family · city · work · hobbies"),
      clock, recBtn, stopBtn, skip);
  });
}

function writing(root, sec) {
  return new Promise((resolve) => {
    const ta = h("textarea", { lang: "de", spellcheck: "false", placeholder: "Liebe Frau Becker, ..." });
    screen(root, say(S.writeNote),
      h("div", { class: "instruction" }, h("span", { class: "ico" }, "✉️"),
        h("span", { class: "txt" }, sec.task_en, h("br"), h("i", { lang: "de" }, sec.task_de)), hint(sec.hint_am, "placement-writing")),
      ta, button(S.done, () => resolve(ta.value.trim()), "primary"));
    ta.focus();
  });
}
