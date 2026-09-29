// Один набор иконок на весь интерфейс: сетка 24×24, линия 2, скруглённые концы (по мотивам Lucide, ISC).
// Никаких текстовых символов ▶ ↓ ✕ › — они в каждом шрифте разной толщины и высоты.
const P = {
  download: '<path d="M12 15V3"/><path d="m7 10 5 5 5-5"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>',
  save: '<path d="M12 17V3"/><path d="m6 11 6 6 6-6"/><path d="M19 21H5"/>',
  music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
  video: '<path d="m16 13 5.2 3.5a.5.5 0 0 0 .8-.4V7.9a.5.5 0 0 0-.8-.4L16 11"/><rect x="2" y="6" width="14" height="12" rx="2"/>',
  play: '<path d="M7 4.9v14.2a1 1 0 0 0 1.5.9l11.4-7.1a1 1 0 0 0 0-1.8L8.5 4a1 1 0 0 0-1.5.9Z"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
  redo: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  right: '<path d="m9 18 6-6-6-6"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
};
const FILLED = new Set(["play"]);

export const icon = (name, cls = "") =>
  `<svg class="i${FILLED.has(name) ? " fill" : ""}${cls ? " " + cls : ""}" viewBox="0 0 24 24" aria-hidden="true">${P[name]}</svg>`;

// Статичные места в index.html помечены <i data-icon="…"> — подставляем те же рисунки
export function hydrate(root = document) {
  root.querySelectorAll("i[data-icon]").forEach(el => { el.outerHTML = icon(el.dataset.icon, el.className); });
}
