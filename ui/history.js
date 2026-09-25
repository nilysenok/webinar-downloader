// Строка истории прошлых загрузок с раскрывающимися подробностями.
import { logBlock, timeline } from "./board.js";
import { bytes, date, dur, esc } from "./util.js";

export const expanded = new Set();
const STATUS = { done: "Готово", error: "Ошибка", cancelled: "Отменено", interrupted: "Прервано" };

function meta(j) {
  const outs = j.outputs || [];
  const m = [`<span>${date(j.created)}</span>`, `<span>${esc(j.mode_label)}</span>`];
  if (j.duration) m.push(`<span class="num">${dur(j.duration)}</span>`);
  if (j.size) m.push(`<span class="num">${bytes(j.size)}${outs.length > 1 ? ` · ${outs.length} файла` : ""}</span>`);
  if (j.finished && j.started) m.push(`<span>заняло <span class="num">${dur(j.finished - j.started)}</span></span>`);
  if (outs.length && !outs.some(o => o.exists)) m.push(`<span class="bad">файл удалён</span>`);
  if (j.work_size) m.push(`<span>промежуточные <span class="num">${bytes(j.work_size)}</span></span>`);
  return m.join("");
}

function actions(j) {
  const outs = j.outputs || [];
  const btn = (act, label, extra = "") => `<button data-act="${act}" data-id="${j.id}" ${extra}>${label}</button>`;
  const mp3 = outs.findIndex(o => o.exists && o.path.endsWith(".mp3"));
  return [
    mp3 >= 0 && btn("play", "▶ Слушать", `data-n="${mp3}"`),
    (outs.some(o => o.exists) || j.work_size) && btn("reveal", "Показать в Finder"),
    btn("restart", j.status === "done" ? "Скачать заново" : "Продолжить", `title="Перезапуск в ту же папку: скачанные сегменты не качаются повторно"`),
    j.work_size && btn("clean", "Удалить промежуточные"),
    `<button class="ghost" data-act="delete" data-id="${j.id}" title="Убрать из истории (файлы останутся)">✕</button>`,
  ].filter(Boolean).join("");
}

function detail(j) {
  const outs = j.outputs || [];
  const files = outs.map((o, i) => `<li><span class="p">${esc(o.path)}</span><span class="num">${bytes(o.size)}</span>${
    o.exists ? `<a href="/files/${j.id}/${i}?dl=1">скачать</a>` : `<span class="bad">нет файла</span>`}</li>`).join("");
  return `<div class="h-detail">
    ${j.error ? `<div class="err">${esc(j.error)}</div>` : ""}
    ${files ? `<ul class="files">${files}</ul>` : ""}
    <div class="kv">${esc(j.url)}</div>
    ${j.folder ? `<div class="kv">папка: ${esc(j.folder)}</div>` : ""}
    ${timeline(j, false)}
    ${logBlock(j)}
  </div>`;
}

export function historyItem(j) {
  const badge = j.status !== "done" ? ` <span class="badge ${j.status}">${STATUS[j.status] || j.status}</span>` : "";
  return `<div class="h-item">
    <div class="h-row" data-toggle="${j.id}">
      <span class="dot ${j.status}"></span>
      <div class="h-main"><div class="h-title">${esc(j.title || j.url)}${badge}</div><div class="h-meta">${meta(j)}</div></div>
      <div class="h-actions">${actions(j)}</div>
    </div>
    ${expanded.has(j.id) ? detail(j) : ""}
  </div>`;
}
