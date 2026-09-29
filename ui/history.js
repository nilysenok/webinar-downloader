// Строка истории: главное действие сразу, файлы и служебное — в раскрытой строке.
import { icon } from "./icons.js";
import { moreBlock } from "./more.js";
import { playable } from "./player.js";
import { bytes, date, dur, esc, fileName } from "./util.js";

export const expanded = new Set();
const STATUS = { done: "Готово", error: "Ошибка", cancelled: "Отменено", interrupted: "Прервано" };
const btn = (j, act, label, extra = "") => `<button data-act="${act}" data-id="${j.id}" ${extra}>${label}</button>`;

function meta(j) {
  const outs = j.outputs || [];
  const m = [`<span>${date(j.created)}</span>`, `<span>${j.mode === "audio" ? "Аудио" : "Видео"}</span>`];
  // статус — первым в строке под названием: в конце длинного названия он обрезался до «Ош…»
  if (j.status !== "done") m.unshift(`<span class="badge ${j.status}">${STATUS[j.status] || j.status}</span>`);
  if (j.duration) m.push(`<span class="num">${dur(j.duration)}</span>`);
  if (j.size) m.push(`<span class="num">${bytes(j.size)}</span>`);
  if (outs.length && !outs.some(o => o.exists)) m.push(`<span class="bad">файлы удалены</span>`);
  return m.join("");
}

function actions(j) {
  const outs = j.outputs || [];
  const main = outs.findIndex(o => o.exists && playable(o.path));
  const a = [];
  if (j.status !== "done") a.push(btn(j, "restart", `${icon("play")}Продолжить`, `class="primary sm" title="Докачает с места остановки"`));
  else if (main >= 0) a.push(btn(j, "play", `${icon("play")}${outs[main].path.endsWith(".mp3") ? "Слушать" : "Смотреть"}`, `class="primary sm" data-n="${main}"`));
  if (outs.some(o => o.exists) || j.folder) a.push(btn(j, "reveal", `${icon("folder")}<span class="lbl">В Finder</span>`, `class="sm reveal" title="Показать файл в Finder"`));
  return a.join("");
}

// Общий экран — первым, отдельные камеры — после
function files(j) {
  const outs = (j.outputs || []).map((o, i) => ({ ...o, i })).sort((a, b) => playable(b.path) - playable(a.path));
  return outs.map(o => `<li><span class="fn" title="${esc(o.path)}">${esc(fileName(o.path))}</span><span class="num sz">${bytes(o.size)}</span>
    ${o.exists ? `${playable(o.path) ? `<button class="ghost sm" data-act="play" data-id="${j.id}" data-n="${o.i}" title="Открыть">${icon("play")}</button>` : ""}<a href="/files/${j.id}/${o.i}?dl=1" title="Сохранить файл">${icon("save")}</a>` : `<span class="bad">нет файла</span>`}</li>`).join("");
}

function detail(j) {
  const list = files(j);
  const tools = [
    j.status === "done" && btn(j, "restart", `${icon("redo")}Скачать заново`, `title="В ту же папку; уже скачанное не качается повторно"`),
    j.work_size && btn(j, "clean", `${icon("trash")}Удалить промежуточные · ${bytes(j.work_size)}`, `title="Кусочки записи для докачки; готовые файлы останутся"`),
    btn(j, "delete", "Убрать из списка", `class="ghost" title="Файлы на диске останутся"`),
  ].filter(Boolean).join("");
  return `<div class="h-detail">
    ${j.error ? `<div class="err">${esc(j.error)}</div>` : ""}
    ${list ? `<ul class="files">${list}</ul>` : ""}
    <div class="tools">${tools}</div>
    ${moreBlock(j, "Журнал и цифры")}
  </div>`;
}

export function historyItem(j) {
  const open = expanded.has(j.id);
  return `<div class="h-item${open ? " open" : ""}">
    <div class="h-row" data-toggle="${j.id}">
      <span class="kind ${j.mode === "audio" ? "a" : "v"}">${icon(j.mode === "audio" ? "music" : "video")}</span>
      <div class="h-main"><div class="h-title">${esc(j.title || j.url)}</div><div class="h-meta">${meta(j)}</div></div>
      <div class="h-actions">${actions(j)}</div>
      <button type="button" class="sm more-btn" aria-expanded="${open}">Подробнее${icon("down", "chev")}</button>
    </div>
    ${open ? detail(j) : ""}
  </div>`;
}
