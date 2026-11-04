// Router: #/ home · #/placement · #/lesson/1 · #/lesson/2 · #/practice · #/progress · #/paz
import { api } from "./api.js";
import { stopAll } from "./audio.js";
import { ctx, updateCounters } from "./ui.js";

const routes = {
  "": () => import("./screens/home.js"),
  placement: () => import("./screens/placement.js"),
  lesson: () => import("./screens/lesson.js"),
  practice: () => import("./screens/practice.js"),
  progress: () => import("./screens/progress.js"),
  paz: () => import("./screens/paz.js"),
};

const root = document.getElementById("app");

export function go(path) {
  if (location.hash === "#/" + path) render();
  else location.hash = "#/" + path;
}

async function render() {
  stopAll();
  const [name, ...params] = location.hash.replace(/^#\/?/, "").split("/");
  const load = routes[name] || routes[""];
  try {
    const mod = await load();
    await mod.render(root, params);
  } catch (e) {
    console.error(e);
    root.replaceChildren(Object.assign(document.createElement("p"), {
      className: "center", textContent: "😕 Something went wrong. Tap 🏠 to go home.",
    }));
  }
}

export async function refreshCounters() {
  try {
    const s = await api.get("/api/state");
    ctx.name = s.name;
    updateCounters(s);
    return s;
  } catch { return null; }
}

document.getElementById("home-btn").onclick = () => go("");
document.getElementById("paz-btn").onclick = () => go("paz");
window.addEventListener("hashchange", render);
refreshCounters().then(render);
