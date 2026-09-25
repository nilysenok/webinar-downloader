// Форма новой загрузки: режим, качество, число потоков, выбор видеопотоков.
import { $, api, bytes, dur, esc, store } from "./util.js";

const state = { mode: "audio", analysis: null, analyzedUrl: "", analyzing: false, selected: new Set() };
let analyzeTimer;

const validUrl = u => /mts-link\.ru\/.*record-new\/\d+/.test(u);

function setMode(m) {
  state.mode = m;
  store.set("mode", m);
  document.querySelectorAll("#modes button").forEach(b => b.classList.toggle("on", b.dataset.mode === m));
  $("qualityField").hidden = m === "audio";
  maybeAnalyze();
  renderPicker();
}

function maybeAnalyze() {
  clearTimeout(analyzeTimer);
  const u = $("url").value.trim();
  if (state.mode === "audio" || !validUrl(u) || u === state.analyzedUrl) return;
  analyzeTimer = setTimeout(() => analyze(u), 350);
}

async function analyze(u) {
  Object.assign(state, { analyzing: true, analysis: null, analyzedUrl: u });
  $("formErr").textContent = "";
  renderPicker();
  try {
    const a = await api("/api/analyze", { method: "POST", body: { url: u } });
    if ($("url").value.trim() !== u) return;
    state.analysis = a;
    // по умолчанию — все потоки с видео длиннее минуты
    state.selected = new Set(a.tracks.filter(t => t.variants.length && t.duration >= 60).map(t => t.id));
    const heights = [...new Set(a.tracks.flatMap(t => t.variants.map(v => v.height)))].sort((x, y) => y - x);
    $("quality").innerHTML = `<option value="best">Лучшее</option>` + heights.map(h => `<option value="${h}">до ${h}p</option>`).join("");
  } catch (e) {
    state.analyzedUrl = "";
    $("formErr").textContent = e.message;
  } finally {
    state.analyzing = false;
    renderPicker();
  }
}

function variantFor(t) {
  const q = $("quality").value;
  if (q === "best") return t.variants[0];
  return t.variants.find(v => v.height <= +q) || t.variants[t.variants.length - 1];
}

function pickerRow(t) {
  const v = t.variants.length ? variantFor(t) : null;
  return `<label class="s-row ${v ? "" : "off"}">
    <input type="checkbox" data-pick="${t.id}" ${state.selected.has(t.id) ? "checked" : ""} ${v ? "" : "disabled"}>
    <span class="nm" title="${esc(t.name)}">${esc(t.name)}</span>
    <span class="chip ${t.kind}">${t.kind === "screen" ? "экран" : "камера"}</span>
    <span class="tm num hide-sm">${dur(t.start)} – ${dur(t.start + t.duration)}</span>
    <span class="r num hide-sm">${v ? `${v.width}×${v.height}` : "нет видео"}</span>
    <span class="r num">${v ? "≈ " + bytes(v.bandwidth * t.duration / 8) : ""}</span>
  </label>`;
}

function renderPicker() {
  const p = $("picker");
  p.hidden = state.mode === "audio" || (!state.analyzing && !state.analysis);
  if (p.hidden) return;
  if (state.analyzing) { p.innerHTML = `<div class="loading">Анализирую запись: ищу видеопотоки…</div>`; return; }
  const a = state.analysis;
  const sel = a.tracks.filter(t => state.selected.has(t.id));
  const total = sel.reduce((s, t) => s + (t.variants.length ? variantFor(t).bandwidth * t.duration / 8 : 0), 0);
  p.innerHTML = `<div class="picker-head">
      <span><b>${esc(a.title)}</b> · ${dur(a.duration)} · видеопотоков: ${a.tracks.filter(t => t.variants.length).length}</span>
      <span class="spacer"></span>
      <span>выбрано ${sel.length}, ≈ ${bytes(total)} видео</span>
      <button type="button" class="ghost" data-pickall="1">все</button>
      <button type="button" class="ghost" data-pickall="0">ни одного</button>
    </div>${[...a.tracks].sort((x, y) => x.start - y.start).map(pickerRow).join("")}`;
}

async function submit(e, onCreated) {
  e.preventDefault();
  $("formErr").textContent = "";
  const url = $("url").value.trim();
  if (state.mode !== "audio") {
    if (!state.analysis || state.analyzedUrl !== url) { $("formErr").textContent = "Дождитесь анализа записи"; maybeAnalyze(); return; }
    if (!state.selected.size) { $("formErr").textContent = "Выберите хотя бы один видеопоток"; return; }
  }
  $("go").disabled = true;
  try {
    const body = { url, mode: state.mode, quality: $("quality").value, streams: [...state.selected], workers: +$("workers").value || 64 };
    await api("/api/jobs", { method: "POST", body });
    $("url").value = "";
    Object.assign(state, { analysis: null, analyzedUrl: "" });
    renderPicker();
    onCreated();
  } catch (err) {
    $("formErr").textContent = err.message === "Failed to fetch" ? "Сервер недоступен — запустите start.command" : err.message;
  } finally {
    $("go").disabled = false;
  }
}

export function initForm(onCreated) {
  $("modes").onclick = e => { const b = e.target.closest("button"); if (b) setMode(b.dataset.mode); };
  $("url").addEventListener("input", maybeAnalyze);
  $("quality").onchange = renderPicker;
  $("workers").value = store.get("workers", "64");
  $("workers").onchange = () => store.set("workers", $("workers").value);
  $("picker").addEventListener("change", e => {
    const id = +e.target.dataset.pick;
    if (!id) return;
    e.target.checked ? state.selected.add(id) : state.selected.delete(id);
    renderPicker();
  });
  $("picker").addEventListener("click", e => {
    const all = e.target.closest("[data-pickall]");
    if (!all) return;
    state.selected = new Set(all.dataset.pickall === "1" ? state.analysis.tracks.filter(t => t.variants.length).map(t => t.id) : []);
    renderPicker();
  });
  $("form").onsubmit = e => submit(e, onCreated);
  setMode(store.get("mode", "audio"));
}
