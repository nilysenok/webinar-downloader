#!/bin/zsh
# The whole ASR measurement in one line: tracks → VAD → both engines → transcripts → score.
# Usage: scripts/asr/run_all.sh "<ссылка на запись>"
set -euo pipefail
cd "$(dirname "$0")/../.."
scripts/asr/setup.sh
scripts/asr/tracks.sh "$1"
.venv/bin/python scripts/asr/vad.py
scripts/asr/run_cpp.sh
caffeinate -i .venv-asr/bin/python scripts/asr/run_mlx.py
for e in cpp mlx; do .venv/bin/python scripts/asr/merge.py $e; done
if [ -f ~/Desktop/МТС/downloads/asr/etalon/A.txt ]; then .venv/bin/python scripts/asr/score.py cpp mlx
else .venv/bin/python scripts/asr/etalon.py cpp; fi
