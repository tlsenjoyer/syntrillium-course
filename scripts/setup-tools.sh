#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
root="$PWD"
export UV_CACHE_DIR="$root/recovered/tools/uv-cache"
export UV_PYTHON_INSTALL_DIR="$root/recovered/tools/python"
uv=uv
if [[ -x "$root/recovered/tools/uv" ]]; then
    uv="$root/recovered/tools/uv"
fi

"$uv" python install --no-bin 3.12.16
"$uv" venv --clear --python 3.12.16 "$root/recovered/tools/whisper-env"
python="$root/recovered/tools/whisper-env/bin/python"
"$uv" pip sync --python "$python" requirements-tools.txt
"$python" -m mypy --version
"$python" tools/smoke_transcription.py
