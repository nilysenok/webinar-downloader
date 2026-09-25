// Точка входа UI: опрос /api/jobs, отрисовка, действия по кнопкам, плеер.
import { activeCard, openLogs } from "./board.js";
import { initForm } from "./form.js";
import { expanded, historyItem } from "./history.js";
import { $, ACTIVE, api } from "./util.js";

let jobs = [], lastHistory = "", pollTimer;

function render() {
  const active = jobs.filter(j => ACTIVE.has(j.status));
  const past = jobs.filter(j => !ACTIVE.has(j.status));
  $("active").innerHTML = active.length
    ? active.map(activeCard).join("")
    : `<div class="empty">Нет активных загрузок — вставьте ссылку на запись выше</div>`;
  // историю перерисовываем только при изменениях, чтобы не сбивать клики и прокрутку журнала
  const h = JSON.stringify([past, [...expanded], [...openLogs]]);
  if (h === lastHistory) return;
  lastHistory = h;
  $("history").innerHTML = past.length ? `<div class="hist">${past.map(historyItem).join("")}</div>` : `<div class="empty">Пока пусто</div>`;
}

async function refresh() {
  clearTimeout(pollTimer);
  try { jobs = await api("/api/jobs"); render(); } catch { /* сервер недоступен — повторим */ }
  pollTimer = setTimeout(refresh, jobs.some(j => ACTIVE.has(j.status)) ? 1000 : 3000);
}

function play(id, n) {
  $("playerTitle").textContent = jobs.find(x => x.id === id)?.title || "";
  $("audio").src = `/files/${id}/${n}`;
  $("audio").play();
  $("player").classList.add("on");
  document.body.classList.add("has-player");
}

async function act(act, id, btn) {
  if (act === "play") return play(id, +btn.dataset.n);
  if (act === "clean" && !confirm("Удалить промежуточные файлы этой загрузки? Готовые файлы останутся, но перезапуск начнёт скачивание с нуля.")) return;
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
  const id = e.target.dataset?.log;
  if (id) e.target.open ? openLogs.add(id) : openLogs.delete(id);
}, true);

$("playerClose").onclick = () => {
  $("audio").pause();
  $("audio").removeAttribute("src");
  $("player").classList.remove("on");
  document.body.classList.remove("has-player");
};
window.addEventListener("resize", () => { lastHistory = ""; render(); });

initForm(refresh);
refresh();
