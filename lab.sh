#!/usr/bin/env bash
#
# lab.sh - Unified Mad Scientist Laboratory CLI
#
# Combines: repomix_manager, dissect, test runner, pipeline control
# Pattern: Uses dissect's cmd_* modular approach + repomix's clean UX
#
# Usage:
#   ./lab.sh [command]
#   ./lab.sh          # Interactive menu
#   ./lab.sh test     # Run tests
#   ./lab.sh snapshot # Run snapshot station
#

set -euo pipefail

# --- Configuration ---
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${ROOT_DIR}/.lab"
CONFIG_FILE="${CONFIG_DIR}/config.json"
GUM_BIN="${GUM_BIN:-gum}"

# --- Styling Constants ---
COLOR_PRIMARY="212"    # Pink/Purple
COLOR_SUCCESS="42"     # Green
COLOR_WARNING="214"    # Orange
COLOR_ERROR="203"      # Red
COLOR_MUTED="241"      # Gray

# --- Dependency Check ---
require_gum() {
    if ! command -v "${GUM_BIN}" &>/dev/null; then
        echo "❌ gum not found. Install with: brew install gum"
        exit 1
    fi
}

# --- Header ---
style_header() {
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "🧪 MAD SCIENTIST LABORATORY" \
        "v1.0 - Where Code Meets Chaos"
}

# --- Utility Functions ---
style_success() {
    "${GUM_BIN}" style --foreground "${COLOR_SUCCESS}" "$1"
}

style_error() {
    "${GUM_BIN}" style --foreground "${COLOR_ERROR}" "$1"
}

style_warning() {
    "${GUM_BIN}" style --foreground "${COLOR_WARNING}" "$1"
}

style_muted() {
    "${GUM_BIN}" style --foreground "${COLOR_MUTED}" "$1"
}

# --- Menu Commands ---

cmd_menu() {
    require_gum
    clear
    style_header

    ACTION="$("${GUM_BIN}" choose --header "Select your workstation:" \
        --cursor.foreground "${COLOR_PRIMARY}" \
        --selected.foreground "${COLOR_PRIMARY}" \
        "📦 Snapshot Station" \
        "🔬 Deep Research Lab" \
        "🧪 Test Chamber" \
        "🎵 Pipeline Control" \
        "📊 Mission Status" \
        "⚙️  Configuration" \
        "📖 Documentation" \
        "🚪 Exit Airlock")"

    case "${ACTION}" in
        "📦 Snapshot Station") cmd_snapshot ;;
        "🔬 Deep Research Lab") cmd_research ;;
        "🧪 Test Chamber") cmd_test ;;
        "🎵 Pipeline Control") cmd_pipeline ;;
        "📊 Mission Status") cmd_status ;;
        "⚙️  Configuration") cmd_config ;;
        "📖 Documentation") cmd_docs ;;
        "🚪 Exit Airlock") exit 0 ;;
    esac
}

cmd_snapshot() {
    require_gum
    clear
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "📦 Snapshot Station" \
        "Generate AI context snapshots"

    # Check for repomix
    if ! command -v repomix &>/dev/null; then
        style_error "❌ repomix not found. Install with: npm install -g repomix"
        "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
        return
    fi

    "${GUM_BIN}" spin --spinner minidot --title "Locating project directories..." -- sleep 0.5

    # Target configuration (Bash 3.x compatible - parallel arrays)
    CONFIGS=(
        "Dataset Scaffold|dataset"
        "Phase 1: Separator|phase-1_qscnet"
        "Phase 2: VAE Encoder|phase-2_audio_vae"
        "Phase 3: Guide|phase-3_lilac_guide"
        "Phase 4: Generator|phase-4_dit_generator"
        "Phase 5: VAE Decoder|phase-5_vae_decoder"
    )

    CHOICES=()
    PATHS_LIST=()
    OUTPUT_DIR="${ROOT_DIR}/src/outputs"
    IGNORE_PATTERNS="_archive/**,**/.git/**,**/build/**,**/*.egg-info/**"

    for config in "${CONFIGS[@]}"; do
        IFS='|' read -r label search_name <<< "$config"
        found_path=$(find "${ROOT_DIR}" -type d -name "$search_name" -not -path "*/.*" -not -path "*/node_modules/*" -print -quit 2>/dev/null || true)

        if [[ -n "$found_path" ]]; then
            CHOICES+=("$label")
            case "$search_name" in
                "dataset") outfile="repomix_dataset.md" ;;
                "phase-1_qscnet") outfile="repomix_phase1.md" ;;
                "phase-2_audio_vae") outfile="repomix_phase2.md" ;;
                "phase-3_lilac_guide") outfile="repomix_phase3.md" ;;
                "phase-4_dit_generator") outfile="repomix_phase4.md" ;;
                "phase-5_vae_decoder") outfile="repomix_phase5.md" ;;
                *) continue ;;
            esac
            PATHS_LIST+=("$label|$found_path|${OUTPUT_DIR}/$outfile")
        fi
    done

    if [[ ${#CHOICES[@]} -eq 0 ]]; then
        style_warning "⚠️  No target folders found in project root."
        "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
        return
    fi

    ALL_SELECTED=$(IFS=, ; echo "${CHOICES[*]}")

    "${GUM_BIN}" style "Select snapshots to update (Space to toggle, Enter to run)"
    SELECTED=$("${GUM_BIN}" choose --no-limit \
        --cursor.foreground="${COLOR_PRIMARY}" \
        --selected.foreground="${COLOR_PRIMARY}" \
        --selected "$ALL_SELECTED" \
        "${CHOICES[@]}")

    if [[ -z "$SELECTED" ]]; then
        style_warning "No snapshots selected."
        "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
        return
    fi

    echo ""
    mkdir -p "${OUTPUT_DIR}"

    IFS=$'\n'
    for item in $SELECTED; do
        for entry in "${PATHS_LIST[@]}"; do
            IFS='|' read -r label input output <<< "$entry"
            if [[ "$item" == "$label" ]]; then
                "${GUM_BIN}" spin --spinner dot --title "Updating $item..." --show-output -- \
                    repomix "$input" -o "$output" --ignore "$IGNORE_PATTERNS" 2>&1 || true

                if [[ -f "$output" ]]; then
                    style_success "✅ Updated $item"
                else
                    style_error "❌ Failed $item"
                fi
                break
            fi
        done
    done

    echo ""
    style_success "🎉 Snapshot station complete!"
    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_research() {
    require_gum
    clear
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "🔬 Deep Research Lab" \
        "AI-powered repository analysis"

    # Delegate to dissect if available
    DISSECT_PATH="${CLI_DIR}/Deep-CLI/dissect"
    if [[ -x "${DISSECT_PATH}" ]]; then
        cd "${CLI_DIR}/Deep-CLI" && ./dissect menu
    else
        style_error "❌ dissect not found at ${DISSECT_PATH}"
    fi

    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_test() {
    require_gum
    clear
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "🧪 Test Chamber" \
        "Execute test suites"

    # Test options
    PHASES=(
        "All Tests"
        "Phase 1: Separator (QSCNet)"
        "Phase 2: VAE Encoder"
        "Phase 3: Guide (LiLAC)"
        "Phase 4: Generator (DiT)"
        "Phase 5: VAE Decoder"
        "Dataset Tests"
        "CLI Tests"
    )

    SELECTED=$("${GUM_BIN}" choose --header "Select test suite:" \
        --cursor.foreground="${COLOR_PRIMARY}" \
        --selected.foreground="${COLOR_PRIMARY}" \
        "${PHASES[@]}")

    cd "${ROOT_DIR}"

    case "${SELECTED}" in
        "All Tests")
            "${GUM_BIN}" spin --spinner dot --title "Running all tests..." --show-output -- \
                make test 2>&1 || true
            ;;
        "Phase 1: Separator (QSCNet)")
            "${GUM_BIN}" spin --spinner dot --title "Running Phase 1 tests..." --show-output -- \
                pytest ml-ops/phase-1_qscnet/tests/ -v 2>&1 || true
            ;;
        "Phase 2: VAE Encoder")
            "${GUM_BIN}" spin --spinner dot --title "Running Phase 2 tests..." --show-output -- \
                pytest ml-ops/phase-2_audio_vae/tests/ -v 2>&1 || true
            ;;
        "Phase 3: Guide (LiLAC)")
            "${GUM_BIN}" spin --spinner dot --title "Running Phase 3 tests..." --show-output -- \
                pytest ml-ops/phase-3_lilac_guide/tests/ -v 2>&1 || true
            ;;
        "Phase 4: Generator (DiT)")
            "${GUM_BIN}" spin --spinner dot --title "Running Phase 4 tests..." --show-output -- \
                pytest ml-ops/phase-4_dit_generator/tests/ -v 2>&1 || true
            ;;
        "Phase 5: VAE Decoder")
            "${GUM_BIN}" spin --spinner dot --title "Running Phase 5 tests..." --show-output -- \
                pytest ml-ops/phase-5_vae_decoder/tests/ -v 2>&1 || true
            ;;
        "Dataset Tests")
            "${GUM_BIN}" spin --spinner dot --title "Running dataset tests..." --show-output -- \
                pytest dataset/tests/ -v 2>&1 || true
            ;;
        "CLI Tests")
            "${GUM_BIN}" spin --spinner dot --title "Running CLI tests..." --show-output -- \
                pytest tests/test_cli.py -v 2>&1 || true
            ;;
    esac

    echo ""
    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_pipeline() {
    require_gum
    clear
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "🎵 Pipeline Control" \
        "Audio stem separation (Phases 1-5)"

    style_warning "⚠️  Pipeline control coming soon..."
    style_muted "This will run the full audio separation pipeline."

    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_status() {
    require_gum
    clear
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "📊 Mission Status" \
        "System overview"

    echo ""

    # Python/PyTorch status
    PYTHON_VER=$(python3 --version 2>&1 | cut -d' ' -f2 || echo "Not found")
    TORCH_STATUS=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "Not installed")
    CUDA_STATUS=$(python3 -c "import torch; print('Available' if torch.cuda.is_available() else 'CPU only')" 2>/dev/null || echo "Unknown")
    MPS_STATUS=$(python3 -c "import torch; print('Available' if torch.backends.mps.is_available() else 'Not available')" 2>/dev/null || echo "Unknown")

    # Snapshot status
    SNAPSHOT_DIR="${ROOT_DIR}/src/outputs"
    SNAPSHOT_COUNT=$(ls -1 "${SNAPSHOT_DIR}"/repomix_*.md 2>/dev/null | wc -l | xargs || echo "0")

    # Test status (check if pytest exists)
    if command -v pytest &>/dev/null; then
        TEST_STATUS="pytest available"
    else
        TEST_STATUS="pytest not found"
    fi

    "${GUM_BIN}" style --border normal --padding "1 2" --margin "1 0" \
        "🖥️  System" \
        "   Python: ${PYTHON_VER}" \
        "   PyTorch: ${TORCH_STATUS}" \
        "   CUDA: ${CUDA_STATUS}" \
        "   MPS (Apple): ${MPS_STATUS}"

    "${GUM_BIN}" style --border normal --padding "1 2" --margin "1 0" \
        "📦 Snapshots" \
        "   Location: ${SNAPSHOT_DIR}" \
        "   Count: ${SNAPSHOT_COUNT} files"

    "${GUM_BIN}" style --border normal --padding "1 2" --margin "1 0" \
        "🧪 Testing" \
        "   Status: ${TEST_STATUS}" \
        "   Project: ${ROOT_DIR}"

    echo ""
    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_config() {
    require_gum
    clear
    "${GUM_BIN}" style \
        --foreground "${COLOR_PRIMARY}" \
        --border double \
        --padding "1 2" \
        --margin "1 0" \
        --align center \
        "⚙️  Configuration" \
        "Laboratory settings"

    style_muted "Configuration options coming soon..."
    style_muted "Project root: ${ROOT_DIR}"

    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_docs() {
    require_gum
    local readme="${ROOT_DIR}/README.md"

    if [[ -f "${readme}" ]]; then
        "${GUM_BIN}" pager < "${readme}"
    else
        style_error "❌ README.md not found"
    fi

    "${GUM_BIN}" confirm "Return to menu?" && cmd_menu
}

cmd_help() {
    cat <<EOF
🧪 Mad Scientist Laboratory CLI

Usage: ./lab.sh [command]

Commands:
  menu      Launch interactive menu (default)
  snapshot  Snapshot Station (Repomix)
  research  Deep Research Lab (Dissect)
  test      Test Chamber
  pipeline  Pipeline Control
  status    Mission Status
  config    Configuration
  docs      Documentation
  help      Show this help

Examples:
  ./lab.sh              # Interactive menu
  ./lab.sh test         # Jump to test chamber
  ./lab.sh snapshot     # Jump to snapshot station
EOF
}

# --- Main ---
COMMAND="${1:-menu}"

case "${COMMAND}" in
    menu) cmd_menu ;;
    snapshot) cmd_snapshot ;;
    research) cmd_research ;;
    test) cmd_test ;;
    pipeline) cmd_pipeline ;;
    status) cmd_status ;;
    config) cmd_config ;;
    docs) cmd_docs ;;
    help|-h|--help) cmd_help ;;
    *) cmd_help; exit 1 ;;
esac
