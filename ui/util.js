// Общие помощники: DOM, экранирование, форматирование, localStorage, запросы к API.
export const ACTIVE = new Set(["queued", "meta", "download", "mix", "mux"]);

export const $ = id => document.getElementById(id);
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pad = n => String(n).padStart(2, "0");

export function dur(s) {
  s = Math.max(0, Math.round(s || 0));
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sec = s % 60;
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}

const fix = (x, d) => x.toFixed(d).replace(".", ",");

export function bytes(b) {
  if (!b) return "0 МБ";
  if (b >= 1e9) return fix(b / 1e9, 2) + " ГБ";
  if (b >= 1e6) return fix(b / 1e6, b >= 1e8 ? 0 : 1) + " МБ";
  return Math.round(b / 1e3) + " КБ";
}

export const speed = b => b >= 1e6 ? fix(b / 1e6, 1) + " МБ/с" : Math.round(b / 1e3) + " КБ/с";
export const date = t => new Date(t * 1000).toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
export const clock = t => new Date(t * 1000).toLocaleTimeString("ru-RU");
export const fileName = p => String(p).split(/[\\/]/).pop();  // в Windows путь с «\»

// Подписи, зависящие от ОС пользователя: где открыть файл и чем запустить сервер
const OS = /Mac/.test(navigator.platform) ? "mac" : /Win/.test(navigator.platform) ? "win" : "linux";
export const folderLabel = { mac: "В Finder", win: "В проводнике", linux: "Открыть папку" }[OS];
export const launcher = { mac: "start.command", win: "start.bat", linux: "start.sh" }[OS];

// plural(5, "камера", "камеры", "камер") → «5 камер»
export function plural(n, one, few, many) {
  const d = n % 10, h = n % 100;
  return `${n} ${d === 1 && h !== 11 ? one : d >= 2 && d <= 4 && (h < 12 || h > 14) ? few : many}`;
}

// localStorage может быть недоступен (приватное окно) — это только удобство
export const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* не критично */ } },
};

export async function api(path, opts = {}) {
  const init = opts.body
    ? { ...opts, headers: { "Content-Type": "application/json" }, body: JSON.stringify(opts.body) }
    : opts;
  const r = await fetch(path, init);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.error || `HTTP ${r.status}`);
  return data;
}
