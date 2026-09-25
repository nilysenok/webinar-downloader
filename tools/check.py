"""Валидатор канона: лимиты кода, структура _ctx.md, закон «закрытое только в архиве»."""
import ast
from pathlib import Path

from .canon import LAYERS, SECTIONS, SKIP_DIRS, STATUSES

CODE_EXT = {".py", ".js", ".css", ".html", ".sh", ".command"}
GENERATED = {"dashboard.html", "ROOT.md", "dashboard.json"}
FILE_LIMIT, FUNC_SOFT, FUNC_HARD = 200, 40, 60
CTX_LIMIT, TASK_LIMIT, MODULE_LIMIT = 150, 25, 10
CODE_SKIP = SKIP_DIRS - {"tests", "tools"}  # тесты и сборщик — тоже код, лимиты для них действуют


def code_files(root: Path):
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and p.suffix in CODE_EXT and p.name not in GENERATED \
                and not any(part in CODE_SKIP for part in rel.parts):
            yield p, rel


def check_code(root: Path, errors, warnings):
    for p, rel in code_files(root):
        n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        if n > FILE_LIMIT:
            errors.append(f"{rel}: {n} строк > {FILE_LIMIT}")
        if p.suffix == ".py":
            check_functions(p, rel, errors, warnings)


def check_functions(p: Path, rel, errors, warnings):
    tree = ast.parse(p.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n = node.end_lineno - node.lineno + 1
            if n > FUNC_HARD:
                errors.append(f"{rel}:{node.lineno} {node.name}(): {n} строк > {FUNC_HARD}")
            elif n > FUNC_SOFT:
                warnings.append(f"{rel}:{node.lineno} {node.name}(): {n} строк > ~{FUNC_SOFT}")


def check_module(m: dict, errors, warnings):
    where = f"{m['dir']}/_ctx.md"
    if m["lines"] > CTX_LIMIT:
        errors.append(f"{where}: {m['lines']} строк > {CTX_LIMIT} — пора делить модуль")
    if m["layer"] not in LAYERS:
        errors.append(f"{where}: «Слой:» должен быть {' | '.join(LAYERS)}, а не «{m['layer']}»")
    missing = [s for s in SECTIONS if s not in m["order"]]
    if missing:
        errors.append(f"{where}: нет разделов {', '.join(missing)}")
    elif [s for s in m["order"] if s in SECTIONS] != SECTIONS:
        warnings.append(f"{where}: разделы не в порядке шаблона")
    if m["status"] not in STATUSES:
        errors.append(f"{where}: СТАТУС «{m['status']}» не из {' | '.join(STATUSES)}")
    if len(m["tasks"]) > TASK_LIMIT:
        errors.append(f"{where}: задач {len(m['tasks'])} > {TASK_LIMIT}")
    for t in m["tasks"]:
        if t["red"] and not t["due"]:
            errors.append(f"{where}: 🔴-задача без срока ДД.ММ: {t['text']}")
    errors += [f"{where}: строка ЗАДАЧ не по шаблону «- [ ] 🔴 ДД.ММ …»: {b}" for b in m["bad_tasks"]]
    for key, mark, name in (("seals", "Ъ —", "ПЕЧАТИ"), ("waiting", "⏳", "ЖДУНЫ"), ("open", "❓", "ОТКРЫТО")):
        errors += [f"{where}: в {name} строка должна начинаться с «{mark}»: {x}"
                   for x in m[key] if not x.lstrip("- ").startswith(mark)]


def check_closed(root: Path, modules, errors):
    """Закон 2: в живых файлах нет закрытых (✅ / [x]) строк — они живут только в arhiv.md."""
    living = [root / "CLAUDE.md", root / "spec.md", root / "roadmap.md"] + [root / m["dir"] / "_ctx.md" for m in modules]
    for p in living:
        if not p.exists():
            errors.append(f"{p.name}: файл не найден")
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "✅" in ln or ln.lstrip().startswith("- [x]"):
                errors.append(f"{p.relative_to(root)}:{i}: закрытая строка — перенести в arhiv.md")


def validate(root: Path, modules, roadmap_bad, archive_bad, stages):
    errors, warnings = [], []
    if len(modules) > MODULE_LIMIT:
        errors.append(f"модулей {len(modules)} > {MODULE_LIMIT}")
    for m in modules:
        check_module(m, errors, warnings)
    check_code(root, errors, warnings)
    check_closed(root, modules, errors)
    errors += [f"roadmap.md: строка не по шаблону «N. [готово|сейчас|далее] Название — описание»: {b}" for b in roadmap_bad]
    errors += [f"arhiv.md: строка не по шаблону «ДД.ММ · [модуль] · что»: {b}" for b in archive_bad]
    now = [s for s in stages if s["state"] == "сейчас"]
    if len(now) != 1:
        warnings.append(f"roadmap.md: этапов [сейчас] {len(now)}, ожидается ровно один (одна черепаха)")
    return errors, warnings
