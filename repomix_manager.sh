#!/usr/bin/env bash
#
# repomix_manager.sh - Manage Repomix Snapshots
#
# Allows selecting and updating Repomix snapshots for the AI Stem Separator project.
#
# Usage:
#   ./repomix_manager.sh
#

set -euo pipefail

# --- Configuration ---
# PROJECT_ROOT is set dynamically in Main
OUTPUT_SUBDIR="src/outputs"
IGNORE_PATTERNS="_archive/**,**/.git/**,**/build/**,**/*.egg-info/**"

# --- Styling & Colors ---
COLOR_PRIMARY="212"    # Pink/Purple
COLOR_SUCCESS="42"     # Green
COLOR_WARNING="214"    # Orange
COLOR_ERROR="203"      # Red
COLOR_MUTED="241"      # Gray

# --- Helper Functions ---
find_target() {
    local target_name=$1
    # Search for directory, excluding common noise
    local found=$(find "$PROJECT_ROOT" -type d -name "$target_name" -not -path "*/.*" -not -path "*/node_modules/*" -not -path "*/build/*" -print -quit)
    echo "$found"
}

check_dependencies() {
    if ! command -v gum &> /dev/null; then
        echo "❌ Gum is required. Install with 'brew install gum'"
        exit 1
    fi
    if ! command -v repomix &> /dev/null; then
        echo "❌ Repomix is required. Install with 'npm install -g repomix'"
        exit 1
    fi
}

run_repomix() {
    local name=$1
    local input=$2
    local output=$3
    
    if [[ -z "$input" ]]; then
        gum style --foreground "$COLOR_WARNING" "⚠️  Could not locate folder for $name"
        return
    fi
    
    gum spin --spinner dot --title "Updating $name..." --show-output -- \
        repomix "$input" -o "$output" --ignore "$IGNORE_PATTERNS"
        
    if [[ $? -eq 0 ]]; then
        gum style --foreground "$COLOR_SUCCESS" "✅ Updated $name"
    else
        gum style --foreground "$COLOR_ERROR" "❌ Failed $name"
    fi
}

# --- Main ---
check_dependencies

# Determine Project Root (two levels up from src/cli)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root to ensure consistent behavior
cd "$PROJECT_ROOT" || exit 1

clear
gum style \
    --foreground "$COLOR_PRIMARY" \
    --border double \
    --padding "1 2" \
    --margin "1 0" \
    --align center \
    "📦 Repomix Snapshot Manager"

gum spin --spinner minidot --title "Locating project directories..." -- sleep 0.5

# Define Targets Configuration
# We use a simple format "Label|SearchName" to avoid Bash 3 associative arrays
CONFIGS=(
    "Dataset Scaffold|dataset"
    "Phase 1: Separator|phase-1_qscnet"
    "Phase 2: VAE Encoder|phase-2_audio_vae"
    "Phase 3: Guide|phase-3_lilac_guide"
    "Phase 4: Generator|phase-4_dit_generator"
    "Phase 5: VAE Decoder|phase-5_vae_decoder"
)

# Build Options and Paths
# We will store details in parallel arrays or a constructed string list
CHOICES=()
PATHS_LIST=() # Format: "Label|InputPath|OutputPath"

for config in "${CONFIGS[@]}"; do
    IFS='|' read -r label search_name <<< "$config"
    found_path=$(find_target "$search_name")
    
    if [[ -n "$found_path" ]]; then
        CHOICES+=("$label")
        
        # Determine output filename manually
        case "$search_name" in
            "dataset") outfile="repomix_dataset.md" ;;
            "phase-1_qscnet") outfile="repomix_phase1.md" ;;
            "phase-2_audio_vae") outfile="repomix_phase2.md" ;;
            "phase-3_lilac_guide") outfile="repomix_phase3.md" ;;
            "phase-4_dit_generator") outfile="repomix_phase4.md" ;;
            "phase-5_vae_decoder") outfile="repomix_phase5.md" ;;
            *) 
                gum style --foreground "$COLOR_ERROR" "❌ Configuration Error: No output defined for '$search_name'"
                continue 
                ;;
        esac
        
        # Store in list
        PATHS_LIST+=("$label|$found_path|$PROJECT_ROOT/$OUTPUT_SUBDIR/$outfile")
    fi
done

if [[ ${#CHOICES[@]} -eq 0 ]]; then
    gum style --foreground "$COLOR_WARNING" "⚠️  No target folders found in project root."
    gum style --foreground "$COLOR_MUTED" "Scanned: $PROJECT_ROOT"
    exit 0
fi

# Create comma-separated list of all choices for default selection
ALL_SELECTED=$(IFS=, ; echo "${CHOICES[*]}")

# Debug: Ensure we actually have choices
if [[ -z "$ALL_SELECTED" ]]; then
     gum style --foreground "$COLOR_ERROR" "Error: Failed to build selection list."
     exit 1
fi

gum style "Select snapshots to update (Space to toggle, Enter to run)"
SELECTED=$(gum choose --no-limit --cursor.foreground="$COLOR_PRIMARY" --selected.foreground="$COLOR_PRIMARY" --selected "$ALL_SELECTED" "${CHOICES[@]}")

if [[ -z "$SELECTED" ]]; then
    gum style --foreground "$COLOR_WARNING" "No snapshots selected. (Tip: Use Space to toggle items)"
    exit 0
fi

echo ""

# Process Selection
IFS=$'\n'
for item in $SELECTED; do
    # Find the matching path in our list
    for entry in "${PATHS_LIST[@]}"; do
        IFS='|' read -r label input output <<< "$entry"
        if [[ "$item" == "$label" ]]; then
            run_repomix "$item" "$input" "$output"
            break
        fi
    done
done

echo ""
gum style --foreground "$COLOR_SUCCESS" --bold "🎉 All tasks finished!"
