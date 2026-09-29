// Форма новой загрузки: ссылка, режим, короткая сводка о записи. Камеры и число соединений — по умолчанию сервера.
import { icon } from "./icons.js";
import { $, api, dur, esc, launcher, plural, store } from "./util.js";

const state = { mode: "audio", url: "", info: null, busy: false, error: "" };
let timer;

const validUrl = u => /mts-link\.ru\/.*record-new\/\d+/.test(u);

function setMode(m) {
  state.mode = m === "audio" ? "audio" : "av";  // «Только видео» осталось в CLI
  store.set("mode", state.mode);
  document.querySelectorAll("#modes button").forEach(b => {
    const on = b.dataset.mode === state.mode;
    b.classList.toggle("on", on);
    b.setAttribute("aria-checked", on);
  });
  renderPreview();
}

// Сводка о записи — только для глаз: отправка её не ждёт
function onUrl() {
  clearTimeout(timer);
  const u = $("url").value.trim();
  $("formErr").textContent = "";
  if (u === state.url) return;
  Object.assign(state, { url: u, info: null, busy: false, error: "" });
  if (u && !validUrl(u)) state.error = "Нужна ссылка на запись: в ней есть …/record-new/…";
  else if (u) { state.busy = true; timer = setTimeout(() => look(u), 350); }
  renderPreview();
}

async function look(u) {
  try {
    const info = await api("/api/analyze", { method: "POST", body: { url: u } });
    if (state.url === u) Object.assign(state, { info, busy: false });
  } catch (e) {
    if (state.url === u) Object.assign(state, { error: e.message === "Failed to fetch" ? `Сервер недоступен — запустите ${launcher}` : e.message, busy: false });
  }
  renderPreview();
}

function summary(a) {
  const people = new Set(a.tracks.map(t => t.name)).size;
  const cams = new Set(a.tracks.filter(t => t.variants.length).map(t => t.name)).size;
  const parts = [`<span class="num">${dur(a.duration)}</span>`, plural(people, "участник", "участника", "участников")];
  if (state.mode === "av") parts.push(cams ? plural(cams, "камера", "камеры", "камер") : `<span class="bad">камер в записи нет — выберите «Аудио»</span>`);
  return `${icon("check")}<div><b>${esc(a.title)}</b><span>${parts.join(" · ")}</span></div>`;
}

function renderPreview() {
  const p = $("preview");
  p.hidden = !state.busy && !state.info && !state.error;
  p.className = "preview" + (state.error ? " err" : state.busy ? " busy" : "");
  if (state.error) p.innerHTML = `${icon("alert")}<div>${esc(state.error)}</div>`;
  else if (state.busy) p.innerHTML = `<i class="spin"></i><div>Смотрю запись…</div>`;
  else if (state.info) p.innerHTML = summary(state.info);
}

async function submit(e, onCreated) {
  e.preventDefault();
  const url = $("url").value.trim();
  if (!validUrl(url)) {
    $("formErr").textContent = url ? "Это не ссылка на запись MTS Link" : "Вставьте ссылку на запись";
    $("url").focus();
    return;
  }
  $("go").disabled = true;
  try {
    await api("/api/jobs", { method: "POST", body: { url, mode: state.mode } });
    $("url").value = "";
    onUrl();
    onCreated();
  } catch (err) {
    $("formErr").textContent = err.message === "Failed to fetch" ? `Сервер недоступен — запустите ${launcher}` : err.message;
  } finally {
    $("go").disabled = false;
  }
}

export function initForm(onCreated) {
  $("modes").onclick = e => { const b = e.target.closest("button"); if (b) setMode(b.dataset.mode); };
  $("url").addEventListener("input", onUrl);
  $("form").onsubmit = e => submit(e, onCreated);
  setMode(store.get("mode", "audio"));
}
