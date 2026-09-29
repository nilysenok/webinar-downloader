// Плеер: MP3 — полоса внизу, общий экран — окно поверх. Отдельные камеры (VP9) браузер играет не везде — их только скачать.
import { $ } from "./util.js";

// общий экран собирается в H.264 (gallery.py) — его играет любой браузер
export const playable = p => p.endsWith(".mp3") || p.endsWith("общий экран.mp4");

function closeAudio() {
  $("audio").pause();
  $("audio").removeAttribute("src");
  $("player").classList.remove("on");
  document.body.classList.remove("has-player");
}

function closeVideo() {
  $("video").pause();
  $("video").removeAttribute("src");
  $("viewer").hidden = true;
}

export function play(job, n) {
  const src = `/files/${job.id}/${n}`;
  if (job.outputs[n].path.endsWith(".mp3")) {
    closeVideo();
    $("playerTitle").textContent = job.title || "";
    $("audio").src = src;
    $("audio").play();
    $("player").classList.add("on");
    document.body.classList.add("has-player");
    return;
  }
  closeAudio();
  $("viewerTitle").textContent = job.title || "";
  $("video").src = src;
  $("viewer").hidden = false;
  $("video").play();
}

export function initPlayer() {
  $("playerClose").onclick = closeAudio;
  $("viewerClose").onclick = closeVideo;
  $("viewer").onclick = e => { if (e.target === $("viewer")) closeVideo(); };
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("viewer").hidden) closeVideo(); });
}
