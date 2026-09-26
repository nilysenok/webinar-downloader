#!/bin/zsh
# whisper.cpp (Metal) over every speech-only track in one process; greedy, Russian.
# Usage: scripts/asr/run_cpp.sh     Output: downloads/asr/speech/cpp/NN.wav.json
set -euo pipefail
SP=~/Desktop/МТС/downloads/asr/speech
mkdir -p $SP/cpp
a=(); for f in $SP/*.wav; do a+=(-f "$f"); done   # zsh: an array, a string would not split
/usr/bin/time -p caffeinate -i whisper-cli -m ~/.cache/whisper.cpp/ggml-large-v3-turbo.bin -l ru -bs 1 -bo 1 -oj "${a[@]}" \
  > $SP/cpp/log.txt 2> $SP/cpp/err.txt || { tail -5 $SP/cpp/err.txt; exit 1; }
mv $SP/*.wav.json $SP/cpp/
tail -3 $SP/cpp/err.txt
