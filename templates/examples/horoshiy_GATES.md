# GATES · тест на мутацию M6 (27.10.2026)

Образец хорошего GATES.md (Ж-004 2.7). Настоящий — агент-кодер по заданию `horoshee_zadanie.md`, 27.10; выводы — фактические.
Каждый гейт — один наблюдаемый результат с командой; EVIDENCE — вывод команды, а не «проверил».

- [x] G1: тест зелёный на текущем коде
CHECK: .venv/bin/python -m unittest tests.test_mutatsii -v
EXPECT: OK
EVIDENCE: test_restart_ignores_new_title ... ok; test_restart_keeps_existing_folder ... ok; Ran 2 tests in 0.002s; OK

- [x] G2: тест красный на мутации M6
CHECK: копия HEAD (`git archive`), в `pipeline.job_folder` удалены строки `if job.folder: return Path(job.folder)`; тот же unittest на копии
EXPECT: FAILED (failures ≥ 1)
EVIDENCE: Ran 17 tests; FAILED (failures=2): «…_1638 Запись (2)') != …_1638 Запись')», «…_1640 Новое название') != …_1638 Старое название')»

- [x] G3: весь набор тестов зелёный
CHECK: .venv/bin/python -m unittest discover -s tests
EXPECT: OK
EVIDENCE: Ran 79 tests in 18.399s; OK

- [x] G4: рабочее дерево не мутировано
CHECK: git diff --stat HEAD -- downloader/
EXPECT: пусто
EVIDENCE: пусто

## Реестр

закрыто 4 из 4 · ABANDON: нет · перепроверено главной сессией 27.10 (тест OK на коде, FAILED (failures=2) на M6)
