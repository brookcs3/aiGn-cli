#!/bin/bash

# MadSci Smoke Test CLI - Phase 1 -> Phase 2 -> Phase 5 wiring check

if ! command -v gum &> /dev/null; then
    echo "gum could not be found, please install it with 'brew install gum'"
    exit 1
fi

BORDER_COLOR="212"
TEXT_COLOR="212"
ACCENT_COLOR="99"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

clear

gum style \
    --foreground "$TEXT_COLOR" --border-foreground "$BORDER_COLOR" --border double \
    --align center --width 60 --margin "1 2" --padding "2 4" \
    'MAD SCIENTIST SMOKE TEST' 'Phase 1 -> Phase 2 -> Phase 5'

gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
    "This runs a random-weights pipeline to verify audio I/O wiring."

OPTION=$(gum choose \
    "Start smoke test" \
    "Exit" \
    --cursor="> " --header="SMOKE TEST MENU")

if [ "$OPTION" = "Exit" ]; then
    exit 0
fi

SECONDS=$(gum input --placeholder "Seconds (default 5)")
if [ -z "$SECONDS" ]; then
    SECONDS=5
fi

MIXTURE="/Users/cameronbrooks/Soulseek Downloads/complete/hatebot/The Prodigy v4.0/! Albums/1997 - The Fat Of The Land/02 - Breathe_01.wav"
QUERY="/Users/cameronbrooks/Soulseek Downloads/complete/hatebot/The Prodigy v4.0/! Samples/theprodigy.com/BGAT/prodigy-loop06.wav"
OUTPUT="/Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/ml-ops/phase-3_lilac_guide/stable-audio-controlnet/data/smoke_test/phase1_2_5_random.wav"

PYTHON_BIN=${PYTHON_BIN:-python}

export DYLD_LIBRARY_PATH="/opt/homebrew/lib:${DYLD_LIBRARY_PATH}"

$PYTHON_BIN \
  /Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/ml-ops/phase-3_lilac_guide/stable-audio-controlnet/cli.py \
  quick-smoke --use-gum --seconds "$SECONDS" --output "$OUTPUT"

