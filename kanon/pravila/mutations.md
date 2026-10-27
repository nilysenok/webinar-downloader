---
paths:
  - "tests/**"
  - "downloader/**"
---

# Обязательные мутации

§5.1 канона v23: для каждого PR, меняющего конвейер, тест должен падать на мутации и проходить на правке. Здесь — мутации
по темам этого проекта и какой тест их ловит. Прогон 27.10.2026: каждая мутация на свежей копии HEAD `a8d15e8`, полный набор
`tests/` (77 тестов); скрипт прогона и вывод — `docs/otchety/` (локально).

## Мутации проекта

| № | Тема (откуда) | Мутация | Ловит |
|---|---|---|---|
| M1 | сведение: громкость (НЕ ТРОГАТЬ `media.mix_filter`) | `normalize=0` → `normalize=1` | `test_media.FilterTest.test_normalize_off_and_offsets` |
| M2 | сведение: сдвиг обоих каналов (там же) | убрать `:all=1` у `adelay` | `test_media.FilterTest.test_normalize_off_and_offsets` |
| M3 | смена размера кадра в потоке (НЕ ТРОГАТЬ `gallery.render`) | убрать `-reinit_filter 0` | `test_gallery.RenderTest.test_frame_size_change_inside_stream` |
| M4 | глубина выражения рамки (НЕ ТРОГАТЬ `tiles._any_of`) | дерево → цепочка `a+b+c` | `test_layout.BorderTest.test_hundreds_of_speech_spans_stay_within_ffmpeg_depth` |
| M5 | докачка (НЕ ТРОГАТЬ `pipeline._drain`) | сегмент пишется сразу под финальным именем, без `.part` | **не ловится** |
| M6 | перезапуск в ту же папку (НЕ ТРОГАТЬ `pipeline.job_folder`) | игнорировать заданный `job.folder` | `test_mutatsii.RestartFolderTest` (оба теста; 27.10, агент-кодер, перепроверено) |
| M7 | ключ кэша (§3.5): отрезок общего экрана | граф не входит в хэш имени `seg_NNNN_<хеш>.mp4` | **не ловится** |
| M8 | сдвиг входа (§3.1): слайды | слайд появляется на 5 с позже события | `test_slides.ParseTest.test_slides_until_next_event_or_close` |
| M9 | сдвиг входа: говорящий | `AHEAD = 1.0` → `0.0` (без появления за 1 с до речи) | `test_layout.LayoutTest.test_camera_then_speaker_without_camera` |
| M10 | лимит открытых файлов (НЕ ТРОГАТЬ `limits.raise_open_files`) | лимит не поднимается | `test_limits.OpenFilesLimit.test_terminal_limit_is_raised_for_max_workers` |
| M11 | UTF-8 консоль (НЕ ТРОГАТЬ `osdeps.utf8_console`) | без перенастройки вывода | `test_osdeps.OsDeps.test_console_survives_a_non_utf8_pipe` |
| M12 | слайды мимо VPN (печать 22.10) | только прямой путь | `test_slides.RenderTest.test_slides_past_vpn_when_direct_route_hangs` |
| M13 | видео по init-сегменту (инвариант) | верить RESOLUTION из плейлиста | `test_gallery.ProbeTest.test_drops_audio_only_variant_and_takes_real_size` |

Итог: ловится 11 из 13. M5, M7 — задача в `downloader/_ctx.md`: тест, который падает на мутации. M6 закрыт 27.10
(`tests/test_mutatsii.py`); прежняя проверка `tests/test_downloader.py:84` M6 не ловит — тавтологична, см. `templates/examples/horoshiy_test_mutatsii.md`.

## Мутации из §5.1, которых в проекте нет

Касание уровня, порядок событий в баре, комиссия на границе, N в поправке — торговли и статистического отбора у загрузчика нет.
Сдвиг входа — M8, M9; ключ кэша — M7.

## Как добавлять

Новая правка конвейера → строка сюда: тема, мутация, тест. Мутация, которую ничто не ловит, — задача в `_ctx.md` модуля,
а не пометка «проверено».
