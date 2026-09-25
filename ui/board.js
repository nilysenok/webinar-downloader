// Карточка активной загрузки, таймлайн дорожек, журнал.
import { bytes, clock, dur, esc, speed } from "./util.js";

export const openLogs = new Set();

const STEPS = {
  audio: [["meta", "Метаданные"], ["download", "Скачивание"], ["mix", "Сведение"], ["done", "Готово"]],
  av: [["meta", "Метаданные"], ["download", "Скачивание"], ["mix", "Сведение аудио"], ["mux", "Склейка видео"], ["done", "Готово"]],
  video: [["meta", "Метаданные"], ["download", "Скачивание"], ["mux", "Склейка видео"], ["done", "Готово"]],
};

function lane(j, name, ts) {
  const D = j.duration;
  const segs = ts.map(t => {
    const left = Math.min(t.start / D, 1) * 100;
    const width = Math.max(Math.min(t.duration / D, 1 - t.start / D), 0) * 100;
    const f = j.status === "done" ? (t.segments ? 1 : 0) : t.segments ? t.done / t.segments : 0;
    const what = t.segments ? `${t.done}/${t.segments} сегм., ${bytes(t.bytes)}` : "не качается";
    const tip = `${name}${t.video ? ` · видео ${t.height}p` : ""}\n${dur(t.start)}–${dur(t.start + t.duration)}\n${what}`;
    return `<div class="tl-seg${t.segments ? "" : " skip"}${t.video ? " vid" : ""}" style="left:${left}%;width:${width}%" title="${esc(tip)}"><i style="width:${f * 100}%"></i></div>`;
  }).join("");
  const total = ts.reduce((s, t) => s + t.segments, 0), done = ts.reduce((s, t) => s + t.done, 0);
  const pct = total ? Math.floor((j.status === "done" ? 1 : done / total) * 100) : null;
  return `<div class="tl-row"><div class="tl-name" title="${esc(name)}">${esc(name)}</div><div class="tl-lane">${segs}</div>
    <div class="tl-pct num ${pct === 100 ? "full" : ""}">${pct === null ? "—" : pct + "%"}</div></div>`;
}

function legend(j) {
  const item = (style, label) => `<span><i style="${style}"></i>${label}</span>`;
  return `<div class="tl-legend">${item("background:var(--fill)", "скачано")}${item("background:var(--track)", "в очереди")}
    ${j.tracks.some(t => t.video) ? item("box-shadow:inset 0 0 0 2px var(--accent)", "с видео") : ""}
    <span><i class="lg-skip"></i>не качается</span>
    ${j.status === "mix" ? item("background:var(--accent);width:3px", "сведение") : ""}</div>`;
}

// Дорожки сгруппированы по участнику: одна строка — один человек, внутри — его медиасессии на оси записи
export function timeline(j, live) {
  if (!j.tracks?.length || !j.duration) return "";
  const lanes = new Map();
  for (const t of j.tracks) lanes.set(t.name, [...(lanes.get(t.name) || []), t]);
  const tickN = window.innerWidth < 760 ? 3 : 6;
  const ticks = Array.from({ length: tickN + 1 }, (_, i) => `<span style="left:${i / tickN * 100}%">${dur(j.duration * i / tickN)}</span>`).join("");
  const rows = [...lanes].sort((a, b) => a[1][0].start - b[1][0].start).map(([name, ts]) => lane(j, name, ts)).join("");
  const head = j.status === "mix"
    ? `<div class="playhead" style="left:calc(var(--nw) + (100% - var(--nw) - var(--pw)) * ${Math.min(j.mix_pos / j.duration, 1)})"></div>` : "";
  return `<div class="timeline">
    <div class="tl-axis"><div></div><div class="ticks">${ticks}</div><div></div></div>
    <div class="tl-lanes">${rows}${head}</div>${live ? legend(j) : ""}</div>`;
}

export function logBlock(j) {
  if (!j.log?.length) return "";
  const w = j.log.filter(l => l.level === "warn").length, e = j.log.filter(l => l.level === "error").length;
  const lines = j.log.slice().reverse().map(l => `<div class="${l.level}"><time>${clock(l.t)}</time>${esc(l.msg)}</div>`).join("");
  return `<details class="log" data-log="${j.id}" ${openLogs.has(j.id) ? "open" : ""}>
    <summary>Журнал · ${j.log.length}${w ? ` · <span class="w">предупреждений ${w}</span>` : ""}${e ? ` · <span class="e">ошибок ${e}</span>` : ""}</summary>
    <div class="log-body">${lines}</div></details>`;
}

function stageLabel(j) {
  if (j.status === "meta") return "Получаю информацию о записи и плейлисты";
  if (j.status === "download") return `Скачиваю ${j.tracks.filter(t => t.segments).length} дорожек${j.seg_cached ? `, ${j.seg_cached} сегм. уже были на диске` : ""}`;
  if (j.status === "mix") return `Свожу аудио: ${dur(j.mix_pos)} из ${dur(j.duration)}`;
  if (j.status === "mux") return `Склеиваю видео: ${j.mux_done} из ${j.mux_total}`;
  return "В очереди…";
}

function stats(j) {
  const stat = (k, v, cls = "") => `<div class="stat"><div class="k">${k}</div><div class="v num ${cls}">${v}</div></div>`;
  return [
    stat("Скачано", j.bytes_total_est ? `${bytes(j.bytes)} / ≈${bytes(j.bytes_total_est)}` : bytes(j.bytes)),
    stat("Скорость", j.status === "download" ? speed(j.speed) : "—"),
    stat("Сегменты", j.seg_total ? `${j.seg_done} / ${j.seg_total}` : "—"),
    stat("Осталось", j.status === "download" && j.eta ? "≈" + dur(j.eta) : "—"),
    stat("Прошло", dur(Date.now() / 1000 - (j.started || j.created))),
    stat("Повторы", j.retries, j.retries ? "warn" : ""),
  ].join("");
}

export function activeCard(j) {
  const steps = STEPS[j.mode] || STEPS.audio;
  const cur = j.status === "queued" ? -1 : steps.findIndex(s => s[0] === j.status);
  const stepHtml = steps.map(([, label], i) => `<span class="step ${i < cur ? "done" : i === cur ? "now" : ""}">${label}</span>`).join("");
  return `<div class="card">
    <div class="card-head">
      <div class="t"><div class="title">${esc(j.title || "Новая загрузка")}<span class="mode">${esc(j.mode_label)}</span></div>
      <div class="sub">${j.duration ? `Запись ${dur(j.duration)} · ` : ""}${j.workers} потоков · ${esc(j.url)}</div></div>
      <button data-act="cancel" data-id="${j.id}">Отменить</button>
    </div>
    <div class="steps">${stepHtml}</div>
    <div class="pct-row"><span class="pct num">${Math.floor(j.progress * 100)}%</span><span class="stage-label">${stageLabel(j)}</span></div>
    <div class="bar"><i style="width:${j.progress * 100}%"></i></div>
    <div class="stats">${stats(j)}</div>
    ${timeline(j, true)}
    ${logBlock(j)}
  </div>`;
}
