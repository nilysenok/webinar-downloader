"""Задача загрузки и дорожка: состояние, прогресс, сериализация в history.json."""
import time
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from .config import DEFAULT_WORKERS, MODES, WEIGHTS, WORK_DIR


@dataclass
class Track:
    """Одна медиасессия записи (камера или экран участника)."""
    id: int
    name: str
    start: float  # relativeTime — сдвиг от начала записи, с
    duration: float
    kind: str = "camera"  # camera | screen
    has_audio: bool = False
    audio_uri: str = ""
    variants: list = field(default_factory=list)  # [{width, height, bandwidth, uri}], лучшее первым
    video: bool = False  # выбрана для скачивания видео
    height: int = 0  # выбранное качество видео
    segments: int = 0
    done: int = 0
    bytes: int = 0


@dataclass
class Job:
    url: str
    mode: str = "audio"
    quality: str = "best"
    streams: list = field(default_factory=list)  # id медиасессий, чьё видео качать
    workers: int = DEFAULT_WORKERS
    gallery: bool = True  # в режимах с видео — ещё общий экран всех камер (gallery.py)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "queued"  # queued|meta|download|mix|mux|done|error|cancelled|interrupted
    title: str = ""
    rec_date: str = ""
    duration: float = 0.0
    created: float = field(default_factory=time.time)  # момент загрузки — от него имя папки
    started: float = 0.0
    finished: float = 0.0
    folder: str = ""  # downloads/ГГГГ-ММ-ДД_ЧЧММ <название>
    tracks: list = field(default_factory=list)
    seg_total: int = 0
    seg_done: int = 0
    seg_cached: int = 0
    bytes: int = 0
    retries: int = 0
    mix_pos: float = 0.0
    mux_done: int = 0
    mux_total: int = 0
    outputs: list = field(default_factory=list)  # [{path, size}]
    size: int = 0
    error: str = ""
    log: list = field(default_factory=list)  # [{t, level, msg}]

    def __post_init__(self):
        self.cancel = False
        self._samples = []  # (monotonic, net_bytes, net_segs) за последние 10 с — для скорости и ETA
        self._net_bytes = self._net_segs = 0
        self.tracks = [t if isinstance(t, Track) else Track(**t) for t in self.tracks]

    @classmethod
    def from_dict(cls, d):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    @property
    def work(self) -> Path | None:
        return Path(self.folder) / WORK_DIR if self.folder else None

    def wants(self):
        """(качать ли аудио, качать ли видео). Общему экрану нужен общий звук — и в «Только видео»."""
        video = self.mode in ("av", "video")
        return self.mode in ("audio", "av") or (video and self.gallery), video

    def add_log(self, level, msg):
        self.log.append({"t": time.time(), "level": level, "msg": msg})
        del self.log[:-300]

    def reset(self):
        """Подготовка к (пере)запуску: прогресс с нуля, папка и сегменты на диске сохраняются."""
        self.status, self.error, self.cancel = "queued", "", False
        self.tracks, self.outputs = [], []
        self.seg_total = self.seg_done = self.seg_cached = self.bytes = self.retries = 0
        self.mix_pos, self.mux_done, self.mux_total, self.size, self.finished = 0.0, 0, 0, 0, 0.0
        self._samples, self._net_bytes, self._net_segs = [], 0, 0

    def got_segment(self, track, n, cached=False):
        track.done += 1
        track.bytes += n
        self.seg_done += 1
        self.bytes += n
        if cached:
            self.seg_cached += 1
            return
        self._net_bytes += n
        self._net_segs += 1
        now = time.monotonic()
        self._samples.append((now, self._net_bytes, self._net_segs))
        while now - self._samples[0][0] > 10:
            self._samples.pop(0)

    def progress(self):
        if self.status == "done":
            return 1.0
        frac = {
            "download": self.seg_done / self.seg_total if self.seg_total else 0,
            "mix": min(self.mix_pos / self.duration, 1) if self.duration else 0,
            "mux": self.mux_done / self.mux_total if self.mux_total else 0,
        }.get(self.status)
        weights = WEIGHTS.get(self.mode, WEIGHTS["audio"])
        if frac is None or self.status not in weights:
            return 0.01 if self.status == "meta" else 0.0
        start, weight = weights[self.status]
        return start + weight * frac

    def speed_eta(self):
        """Скорость (Б/с) и оставшееся время (с) по скачанному за последние секунды."""
        samples = list(self._samples)
        if self.status != "download" or not samples:
            return 0.0, 0.0
        t0, b0, s0 = samples[0]
        _, b1, s1 = samples[-1]
        dt = time.monotonic() - t0  # до «сейчас», чтобы при зависании скорость падала к нулю
        if dt <= 0.5:
            return 0.0, 0.0
        rate = (s1 - s0) / dt
        eta = (self.seg_total - self.seg_done) / rate if rate > 0 else 0.0
        return (b1 - b0) / dt, eta

    def to_dict(self):
        d = asdict(self)
        speed, eta = self.speed_eta()
        est = self.bytes / self.seg_done * self.seg_total if self.seg_done else 0
        d.update(speed=speed, eta=eta, bytes_total_est=est, progress=self.progress(),
                 mode_label=MODES.get(self.mode, self.mode), work=str(self.work or ""))
        return d
