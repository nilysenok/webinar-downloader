"""Сборка производных: dashboard.json → ROOT.md и dashboard.html. Детерминированно: без меток времени."""
import json
from pathlib import Path

from .canon import LAYERS, date_key, find_modules, parse_archive, parse_ctx, parse_roadmap
from .check import validate

TEMPLATE = Path(__file__).with_name("dashboard.tpl.html")


def _clean(x: str) -> str:
    return x[2:].strip() if x.startswith("- ") else x.strip()


def build_data(root: Path) -> dict:
    modules = [parse_ctx(d / "_ctx.md") for d in find_modules(root)]
    stages, roadmap_bad = parse_roadmap(root / "roadmap.md")
    archive, archive_bad = parse_archive(root / "arhiv.md")
    errors, warnings = validate(root, modules, roadmap_bad, archive_bad, stages)
    for m in modules:
        for key in ("seals", "waiting", "open"):
            m[key] = [_clean(x) for x in m[key]]
        for key in ("order", "bad_tasks", "lines"):
            m.pop(key)
    claude = root / "CLAUDE.md"
    title = next((ln[2:].strip() for ln in claude.read_text(encoding="utf-8").splitlines() if ln.startswith("# ")),
                 root.name) if claude.exists() else root.name
    return {"project": title, "stages": stages, "modules": modules, "archive": archive[-12:][::-1],
            "check": {"errors": errors, "warnings": warnings}}


def _section(title, rows):
    return [f"## {title}", *(rows or ["—"]), ""]


def render_root(data: dict) -> str:
    mods = data["modules"]
    out = [f"# ROOT · {data['project']}", "",
           "> Собирается `python xtask.py` из `*/_ctx.md`, `roadmap.md`, `arhiv.md`. **Руками не править** —",
           "> правим `_ctx.md` модуля и пересобираем. При противоречии прав модуль.", ""]
    now = next((s for s in data["stages"] if s["state"] == "сейчас"), None)
    total = len(data["stages"])
    out += _section("Этап", [f"Сейчас: **{now['n']}. {now['title']}** ({now['n']} из {total})" if now else "—"]
                    + [f"- [{s['state']}] {s['n']}. {s['title']}" for s in data["stages"]])
    out += ["## Модули", "", "| Модуль | Слой | Статус | Задач | 🔴 | ❓ | ⏳ |", "|---|---|---|---|---|---|---|"]
    for layer in LAYERS:
        for m in (m for m in mods if m["layer"] == layer):
            red = sum(t["red"] for t in m["tasks"])
            out.append(f"| [{m['name']}]({m['dir']}/_ctx.md) | {m['layer']} | {m['status']} | {len(m['tasks'])} "
                       f"| {red} | {len(m['open'])} | {len(m['waiting'])} |")
    out.append("")
    reds = sorted(((t, m) for m in mods for t in m["tasks"] if t["red"]), key=lambda x: date_key(x[0]["due"]))
    out += _section("🔴 Задачи со сроком", [f"- {t['due']} [{m['dir']}] {t['text']}" for t, m in reds])
    out += _section("❓ Открыто", [f"- [{m['dir']}] {x}" for m in mods for x in m["open"]])
    out += _section("⏳ Ждуны", [f"- [{m['dir']}] {x}" for m in mods for x in m["waiting"]])
    out += _section("Ъ Печати", [f"- [{m['dir']}] {x}" for m in mods for x in m["seals"]])
    out += _section("НЕ ТРОГАТЬ", [f"- [{m['dir']}] {x}" for m in mods for x in m["dont_touch"]])
    out += _section("Техдолг", [f"- [{m['dir']}] {x}" for m in mods for x in m["debt"]])
    chk = data["check"]
    out += _section("Валидатор", [f"- ошибок: {len(chk['errors'])}, предупреждений: {len(chk['warnings'])}"]
                    + [f"- ✖ {e}" for e in chk["errors"]] + [f"- ⚠ {w}" for w in chk["warnings"]])
    return "\n".join(out).rstrip() + "\n"


def render_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def render_html(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
