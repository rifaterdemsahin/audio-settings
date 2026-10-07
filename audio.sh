#!/usr/bin/env bash
# Quick entrypoint wrapper for audio_settings.py
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
python3 "$DIR/audio_settings.py" "$@"
