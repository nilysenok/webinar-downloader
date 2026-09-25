"""Разбор md-файлов канона: <модуль>/_ctx.md, roadmap.md, arhiv.md."""
import re
from pathlib import Path

SECTIONS = ["НАЗНАЧЕНИЕ", "КОНТРАКТ", "ИНВАРИАНТЫ", "СТАТУС", "ЗАДАЧИ", "ТЕХДОЛГ",
            "ПЕЧАТИ", "ЖДУНЫ", "ОТКРЫТО", "НЕ ТРОГАТЬ"]
LAYERS = ["ФРОНТЕНД", "БЭКЕНД"]
STATUSES = ["стабильно", "в работе", "чинится", "заморожен"]
STAGES = ["готово", "сейчас", "далее"]
SKIP_DIRS = {".venv", ".git", "downloads", "__pycache__", "node_modules", "tests", "tools"}

TASK_RE = re.compile(r"^- \[ \] (?:(🔴) )?(?:(\d\d\.\d\d) )?(.+)$")
STAGE_RE = re.compile(r"^(\d+)\. \[(\w+)\] (.+?)(?: — (.+))?$")
ARCH_RE = re.compile(r"^(\d\d\.\d\d) · \[([\w-]+)\] · (.+)$")


def find_modules(root: Path):
    """Модули — папки первого уровня с _ctx.md."""
    return sorted(p.parent for p in root.glob("*/_ctx.md") if p.parent.name not in SKIP_DIRS)


def _split_sections(lines):
    sections, current = {}, None
    for ln in lines:
        m = re.match(r"^## (.+?)\s*$", ln)
        if m:
            current = m.group(1)
            sections[current] = []
        elif current is not None:
            sections[current].append(ln.rstrip())
    # «—» — явная пометка «пусто»
    return {k: [x for x in v if x.strip() and x.strip() not in ("—", "-")] for k, v in sections.items()}


def _bullets(lines, prefix="- "):
    return [ln[len(prefix):].strip() for ln in lines if ln.startswith(prefix)]


def parse_ctx(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = next((ln[2:].strip() for ln in lines if ln.startswith("# ")), path.parent.name)
    layer = next((ln.split(":", 1)[1].strip() for ln in lines if ln.startswith("Слой:")), "")
    sec = _split_sections(lines)
    tasks, bad_tasks = [], []
    for ln in sec.get("ЗАДАЧИ", []):
        m = TASK_RE.match(ln)
        if m:
            tasks.append({"red": bool(m[1]), "due": m[2] or "", "text": m[3].strip()})
        else:
            bad_tasks.append(ln)
    return {
        "name": title, "dir": path.parent.name, "layer": layer, "lines": len(lines),
        "order": [k for k in sec],
        "purpose": " ".join(sec.get("НАЗНАЧЕНИЕ", [])),
        "contract": sec.get("КОНТРАКТ", []),
        "status": (sec.get("СТАТУС") or [""])[0].strip(),
        "invariants": _bullets(sec.get("ИНВАРИАНТЫ", [])),
        "tasks": tasks, "bad_tasks": bad_tasks,
        "debt": _bullets(sec.get("ТЕХДОЛГ", [])),
        "seals": [ln for ln in sec.get("ПЕЧАТИ", []) if ln.strip()],
        "waiting": [ln for ln in sec.get("ЖДУНЫ", []) if ln.strip()],
        "open": [ln for ln in sec.get("ОТКРЫТО", []) if ln.strip()],
        "dont_touch": _bullets(sec.get("НЕ ТРОГАТЬ", [])),
    }


def parse_roadmap(path: Path):
    stages, bad = [], []
    if not path.exists():
        return stages, ["roadmap.md не найден"]
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\d+\.", ln):
            continue
        m = STAGE_RE.match(ln.strip())
        if m and m[2] in STAGES:
            stages.append({"n": int(m[1]), "state": m[2], "title": m[3].strip(), "desc": (m[4] or "").strip()})
        else:
            bad.append(ln)
    return stages, bad


def parse_archive(path: Path):
    entries, bad = [], []
    if not path.exists():
        return entries, ["arhiv.md не найден"]
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\d", ln):
            continue
        m = ARCH_RE.match(ln.strip())
        if m:
            entries.append({"date": m[1], "module": m[2], "text": m[3]})
        else:
            bad.append(ln)
    return entries, bad


def date_key(ddmm: str):
    """ДД.ММ → (ММ, ДД) для сортировки; без даты — в конец."""
    if not ddmm:
        return (99, 99)
    d, m = ddmm.split(".")
    return (int(m), int(d))
