#!/bin/zsh
# ASR measurement environment. Models go to ~/.cache (the session temp folder is wiped by macOS updates).
# Usage: scripts/asr/setup.sh     (idempotent: downloads resume with curl -C -)
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v whisper-cli >/dev/null || brew install whisper-cpp
[ -x .venv-asr/bin/python ] || { .venv/bin/python -m venv .venv-asr && .venv-asr/bin/pip install -q mlx-whisper; }
fetch() {  # url file sha256|-  — resume until complete; the HF Python client stalled on 26.09
  for i in 1 2 3 4 5; do curl -sSL -C - --max-time 600 -o "$2" "$1" && break || echo "retry $i"; done
  [ "$3" = "-" ] || [ "$(shasum -a 256 "$2" | cut -c1-64)" = "$3" ] || { echo "bad checksum: $2"; exit 1; }
}
HF=https://huggingface.co
mkdir -p ~/.cache/whisper.cpp ~/.cache/mlx-whisper/whisper-large-v3-turbo
fetch $HF/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin ~/.cache/whisper.cpp/ggml-large-v3-turbo.bin -
fetch $HF/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin ~/.cache/whisper.cpp/ggml-silero-v5.1.2.bin -
M=~/.cache/mlx-whisper/whisper-large-v3-turbo
fetch $HF/mlx-community/whisper-large-v3-turbo/resolve/main/config.json $M/config.json -
fetch $HF/mlx-community/whisper-large-v3-turbo/resolve/main/weights.safetensors $M/weights.safetensors \
  951ed3fc1203e6a62467abb2144a96ce7eafca8fa77e3704fdb8635ff3e7f8a6
ls -l ~/.cache/whisper.cpp $M
