#!/bin/zsh
# Per-track audio for ASR: webinarip --multicam into downloads/asr, then 16 kHz mono wav per track.
# Usage: scripts/asr/tracks.sh "<ссылка на запись>"
set -euo pipefail
R=~/Desktop/МТС/downloads/asr
mkdir -p $R/wav
caffeinate -i ~/Desktop/webinarip/target/release/webinarip "$1" --multicam --out $R
D=$(ls -td $R/*/ | grep -v -E '/(wav|speech|etalon|diff)/$' | head -1)
for f in "$D"tracks/*.m4a; do ffmpeg -v error -y -i "$f" -ac 1 -ar 16000 -c:a pcm_s16le "$R/wav/$(basename "$f" | cut -c1-2).wav"; done
ls $R/wav
