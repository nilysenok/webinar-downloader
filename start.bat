@echo off
rem Windows: двойной клик — поднимает локальный сервер и открывает дашборд в браузере.
chcp 65001 >nul
rem Python в режиме UTF-8: иначе в Windows вывод и файлы по умолчанию в cp1252/cp1251 — кириллица роняет программу
set PYTHONUTF8=1
cd /d "%~dp0"
if "%PORT%"=="" set PORT=8765
set URL=http://127.0.0.1:%PORT%

curl -s -o nul --max-time 1 %URL%/api/jobs && (
  echo Сервер уже запущен: %URL%
  start "" %URL%
  exit /b 0
)

where ffmpeg >nul 2>nul || (
  echo Не найден ffmpeg. Установите: winget install Gyan.FFmpeg  ^(и откройте это окно заново^)
  pause
  exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo Создаю окружение…
  py -3 -m venv .venv 2>nul || python -m venv .venv || (
    echo Не найден Python 3.10+. Установите: winget install Python.Python.3.12
    pause
    exit /b 1
  )
)

echo Проверяю зависимости…
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt || (pause & exit /b 1)

rem браузер — через пару секунд, когда сервер поднимется
start "" /min powershell -NoProfile -Command "Start-Sleep 3; Start-Process '%URL%'"
echo Дашборд: %URL% — не закрывайте это окно, пока идут загрузки.
.venv\Scripts\python.exe -m server.app
pause
