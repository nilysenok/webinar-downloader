// «Подробности» загрузки для тех, кому интересно: дорожки участников на шкале записи, цифры, журнал.
import { icon } from "./icons.js";
import { bytes, clock, dur, esc } from "./util.js";

export const openLogs = new Set();  // ключи открытых <details>: «id:more», «id:log»

function lane(j, name, ts) {
  const D = j.duration;
  const segs = ts.map(t => {
    const left = Math.min(t.start / D, 1) * 100;
    const width = Math.max(Math.min(t.duration / D, 1 - t.start / D), 0) * 100;
    const f = j.status === "done" ? (t.segments ? 1 : 0) : t.segments ? t.done / t.segments : 0;
    const tip = `${name}${t.video ? " · камера" : ""}\n${dur(t.start)}–${dur(t.start + t.duration)}\n${t.segments ? bytes(t.bytes) : "не нужна"}`;
    return `<div class="tl-seg${t.segments ? "" : " skip"}${t.video ? " vid" : ""}" style="left:${left}%;width:${width}%" title="${esc(tip)}"><i style="width:${f * 100}%"></i></div>`;
  }).join("");
  return `<div class="tl-row"><div class="tl-name" title="${esc(name)}">${esc(name)}</div><div class="tl-lane">${segs}</div></div>`;
}

// Одна строка — один участник, внутри — его отрезки на шкале записи
function timeline(j) {
  if (!j.tracks?.length || !j.duration) return "";
  const lanes = new Map();
  for (const t of j.tracks) lanes.set(t.name, [...(lanes.get(t.name) || []), t]);
  const tickN = window.innerWidth < 640 ? 2 : 4;
  const ticks = Array.from({ length: tickN + 1 }, (_, i) => `<span style="left:${i / tickN * 100}%">${dur(j.duration * i / tickN)}</span>`).join("");
  const rows = [...lanes].sort((a, b) => a[1][0].start - b[1][0].start).map(([name, ts]) => lane(j, name, ts)).join("");
  const head = j.status === "mix" ? `<div class="playhead" style="left:calc(var(--nw) + (100% - var(--nw)) * ${Math.min(j.mix_pos / j.duration, 1)})"></div>` : "";
  const cam = j.tracks.some(t => t.video) ? `<span><i class="lg-vid"></i>с камерой</span>` : "";
  return `<div class="timeline">
    <div class="tl-axis"><div></div><div class="ticks">${ticks}</div></div>
    <div class="tl-lanes">${rows}${head}</div>
    <div class="tl-legend"><span><i class="lg-fill"></i>скачано</span><span><i class="lg-track"></i>ещё нет</span>${cam}</div></div>`;
}

function logBlock(j) {
  if (!j.log?.length) return "";
  const key = `${j.id}:log`, w = j.log.filter(l => l.level === "warn").length;
  const lines = j.log.slice().reverse().map(l => `<div class="${l.level}"><time>${clock(l.t)}</time>${esc(l.msg)}</div>`).join("");
  return `<details class="log" data-log="${key}" ${openLogs.has(key) ? "open" : ""}>
    <summary>${icon("right", "chev")}Журнал · ${j.log.length}${w ? ` · <span class="w">предупреждений ${w}</span>` : ""}</summary>
    <div class="log-body">${lines}</div></details>`;
}

function facts(j) {
  const f = [];
  if (j.seg_total) f.push(["Кусочков", `${j.seg_done} / ${j.seg_total}`]);
  if (j.seg_cached) f.push(["Уже были на диске", j.seg_cached]);
  if (j.tracks?.length) f.push(["Дорожек", j.tracks.length]);
  f.push(["Соединений", j.workers]);
  if (j.retries) f.push(["Повторов", j.retries]);
  if (j.folder) f.push(["Папка", `<span class="path">${esc(j.folder)}</span>`]);
  f.push(["Ссылка", `<span class="path">${esc(j.url)}</span>`]);
  return `<dl class="facts">${f.map(([k, v]) => `<div><dt>${k}</dt><dd class="num">${v}</dd></div>`).join("")}</dl>`;
}

// label: «Подробнее» в карточке загрузки; в раскрытой строке истории — «Журнал и цифры» (она сама «Подробнее»)
export function moreBlock(j, label = "Подробнее") {
  const key = `${j.id}:more`;
  return `<details class="more" data-log="${key}" ${openLogs.has(key) ? "open" : ""}>
    <summary>${icon("right", "chev")}${label}</summary>${facts(j)}${timeline(j)}${logBlock(j)}</details>`;
}
