// Точка входа UI: опрос /api/jobs, отрисовка, действия по кнопкам.
import { activeCard } from "./board.js";
import { initForm } from "./form.js";
import { expanded, historyItem } from "./history.js";
import { openLogs } from "./more.js";
import { initPlayer, play } from "./player.js";
import { $, ACTIVE, api } from "./util.js";

let jobs = [], lastHistory = "", pollTimer, loaded = false;

const EMPTY = `<div class="empty"><b>Пока ничего не скачано</b>Вставьте ссылку на запись выше — файл появится здесь.</div>`;

function render() {
  const active = jobs.filter(j => ACTIVE.has(j.status));
  const past = jobs.filter(j => !ACTIVE.has(j.status));
  $("activeSec").hidden = !active.length;
  $("active").innerHTML = active.map(activeCard).join("");
  // историю перерисовываем только при изменениях, чтобы не сбивать клики и прокрутку журнала
  const h = JSON.stringify([past, [...expanded], [...openLogs]]);
  if (h === lastHistory) return;
  lastHistory = h;
  $("history").innerHTML = past.length ? `<div class="hist">${past.map(historyItem).join("")}</div>` : loaded ? EMPTY : "";
}

async function refresh() {
  clearTimeout(pollTimer);
  try { jobs = await api("/api/jobs"); loaded = true; render(); } catch { /* сервер недоступен — повторим */ }
  pollTimer = setTimeout(refresh, jobs.some(j => ACTIVE.has(j.status)) ? 1000 : 3000);
}

async function act(act, id, btn) {
  const job = jobs.find(x => x.id === id);
  if (act === "play") return job && play(job, +btn.dataset.n);
  if (act === "clean" && !confirm("Удалить промежуточные файлы? Готовые файлы останутся, но «Скачать заново» начнёт с нуля.")) return;
  if (act === "cancel" && !confirm("Отменить загрузку? Скачанное сохранится — «Продолжить» докачает с этого места.")) return;
  try {
    if (act === "delete") {
      await api(`/api/jobs/${id}`, { method: "DELETE" });
      expanded.delete(id);
    } else {
      await api(`/api/jobs/${id}/${act}`, { method: "POST" });
    }
  } catch (e) { alert(e.message); }
  refresh();
}

document.addEventListener("click", e => {
  const btn = e.target.closest("[data-act]");
  if (btn) return act(btn.dataset.act, btn.dataset.id, btn);
  const row = e.target.closest("[data-toggle]");
  if (!row || e.target.closest("a, details")) return;
  const id = row.dataset.toggle;
  expanded.has(id) ? expanded.delete(id) : expanded.add(id);
  render();
});
// toggle не всплывает — ловим на фазе перехвата, чтобы открытый журнал не закрывался при перерисовке
document.addEventListener("toggle", e => {
  const key = e.target.dataset?.log;
  if (key) e.target.open ? openLogs.add(key) : openLogs.delete(key);
}, true);
window.addEventListener("resize", () => { lastHistory = ""; render(); });

initPlayer();
initForm(refresh);
refresh();
