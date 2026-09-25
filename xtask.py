"""Сборщик и валидатор канона (аналог `cargo xtask`).

    python xtask.py           собрать ROOT.md + dashboard.json + dashboard.html из md
    python xtask.py --check   ничего не писать: валидатор + тесты + «производные свежие» (CI)

Код возврата 0 — зелёный, 1 — есть ошибки.
"""
import subprocess
import sys
from pathlib import Path

from tools.render import build_data, render_html, render_json, render_root

ROOT = Path(__file__).resolve().parent


def outputs(data):
    return {
        ROOT / "ROOT.md": render_root(data),
        ROOT / "dashboard.json": render_json(data),
        ROOT / "dashboard.html": render_html(data),
    }


def run_tests() -> bool:
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                       cwd=ROOT, capture_output=True, text=True)
    tail = (r.stderr or r.stdout).strip().splitlines()
    print(f"тесты: {tail[-1] if tail else 'нет вывода'}")
    if r.returncode:
        print(r.stderr)
    return r.returncode == 0


def report(data):
    chk = data["check"]
    for e in chk["errors"]:
        print(f"✖ {e}")
    for w in chk["warnings"]:
        print(f"⚠ {w}")
    mods = data["modules"]
    tasks = sum(len(m["tasks"]) for m in mods)
    print(f"модулей {len(mods)}, задач {tasks}, ошибок {len(chk['errors'])}, предупреждений {len(chk['warnings'])}")


def main(argv):
    check = "--check" in argv
    data = build_data(ROOT)
    report(data)
    ok = not data["check"]["errors"]
    if check:
        stale = [p.name for p, text in outputs(data).items()
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print(f"✖ устарели: {', '.join(stale)} — запустите python xtask.py")
        ok = run_tests() and ok and not stale
    else:
        for p, text in outputs(data).items():
            p.write_text(text, encoding="utf-8")
        print("собрано: ROOT.md, dashboard.json, dashboard.html")
    print("ЗЕЛЁНЫЙ" if ok else "КРАСНЫЙ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
