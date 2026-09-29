// Карточка активной загрузки: процент, этап простыми словами, скорость и остаток. Технику — в «Подробности».
import { moreBlock } from "./more.js";
import { bytes, dur, esc, plural, speed } from "./util.js";

const STEPS = {
  audio: [["download", "Скачивание"], ["mix", "Сведение звука"], ["done", "Готово"]],
  av: [["download", "Скачивание"], ["mix", "Сведение звука"], ["mux", "Сборка видео"], ["done", "Готово"]],
  video: [["download", "Скачивание"], ["mix", "Сведение звука"], ["mux", "Сборка видео"], ["done", "Готово"]],
};

function stageLabel(j) {
  if (j.status === "queued") return "Ждёт очереди";
  if (j.status === "meta") return "Узнаю, из чего состоит запись…";
  if (j.status === "download") return j.eta ? `Скачиваю · осталось ≈ ${dur(j.eta)}` : "Скачиваю…";
  if (j.status === "mix") return `Свожу голоса в одну дорожку · ${dur(j.mix_pos)} из ${dur(j.duration)}`;
  if (j.status === "mux") return j.mux_total > 1 && j.mux_done >= j.mux_total - 1 ? "Собираю общий экран со всеми камерами" : "Собираю видео";
  return "";
}

function subLine(j) {
  const people = j.tracks?.length ? new Set(j.tracks.map(t => t.name)).size : 0;
  const cams = new Set((j.tracks || []).filter(t => t.video).map(t => t.name)).size;  // люди, а не медиасессии
  const s = [];
  if (j.duration) s.push(`запись <span class="num">${dur(j.duration)}</span>`);
  if (people) s.push(plural(people, "участник", "участника", "участников"));
  if (cams) s.push(plural(cams, "камера", "камеры", "камер"));
  return s.join(" · ");
}

function numbers(j) {
  const n = [];
  if (j.status === "download") n.push(["скорость", j.speed ? speed(j.speed) : "—"]);
  if (j.bytes) n.push(["скачано", j.bytes_total_est && j.status === "download" ? `${bytes(j.bytes)} из ≈${bytes(j.bytes_total_est)}` : bytes(j.bytes)]);
  n.push(["прошло", dur(Date.now() / 1000 - (j.started || j.created))]);
  return n.map(([k, v]) => `<div><span>${k}</span><b class="num">${v}</b></div>`).join("");
}

export function activeCard(j) {
  const steps = STEPS[j.mode] || STEPS.audio;
  const cur = steps.findIndex(s => s[0] === j.status);
  const stepHtml = steps.map(([, label], i) => `<li class="${cur < 0 ? "" : i < cur ? "done" : i === cur ? "now" : ""}">${label}</li>`).join("");
  const pct = Math.floor(j.progress * 100);
  return `<article class="card">
    <div class="card-head">
      <div class="t"><div class="title">${esc(j.title || "Новая загрузка")}<span class="mode">${j.mode === "audio" ? "Аудио" : "Видео"}</span></div>
      ${subLine(j) ? `<div class="sub">${subLine(j)}</div>` : `<div class="sub url">${esc(j.url)}</div>`}</div>
      <button class="ghost" data-act="cancel" data-id="${j.id}">Отменить</button>
    </div>
    <div class="pct-row"><span class="pct num">${pct}<small>%</small></span><span class="stage-label">${stageLabel(j)}</span></div>
    <div class="bar${j.status === "meta" || j.status === "queued" ? " wait" : ""}"><i style="width:${Math.max(j.progress * 100, 1)}%"></i></div>
    <div class="card-foot"><ol class="steps">${stepHtml}</ol><div class="numbers">${numbers(j)}</div></div>
    ${moreBlock(j)}
  </article>`;
}
