#!/usr/bin/env bash
#
# research.sh - Codex: Deep Research Agent System CLI
#
# This script provides an interactive Gum-based interface for:
# 1. Bark Dissector - Autonomous repository analysis
# 2. Dataset Audit Engine - Cross-reference validation
#
# Dependencies:
#   - gum (https://github.com/charmbracelet/gum)
#   - python3 (3.11+)
#
# Usage:
#   ./research.sh
#   ./research.sh --config        # Launch configuration wizard
#   ./research.sh --bark <repo>   # Direct to Bark mode
#   ./research.sh --audit         # Direct to Audit mode
#

set -euo pipefail

# --- Constants & Configuration ---
CONFIG_DIR="$HOME/.config/deep-research"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
HISTORY_FILE="$CONFIG_DIR/history.log"

# Default paths - can be overridden by config
DEFAULT_OUTPUT_DIR="$HOME/Server/outputs"
DEFAULT_BARK_REPO="$HOME/bark"

# --- Styling & Colors ---
COLOR_PRIMARY="212"    # Pink/Purple
COLOR_SUCCESS="42"     # Green
COLOR_WARNING="214"    # Orange
COLOR_ERROR="203"      # Red
COLOR_MUTED="241"      # Gray

# --- Helper Functions ---

log_message() {
    local type=$1
    local message=$2
    gum style --foreground "$COLOR_MUTED" "[$type] $message"
}

check_dependencies() {
    local missing=0
    
    if ! command -v gum &> /dev/null; then
        echo "❌ Gum is required but not installed."
        echo "Install with: brew install gum (macOS) or go install github.com/charmbracelet/gum@latest"
        missing=1
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed."
        missing=1
    fi
    
    if [[ $missing -eq 1 ]]; then
        exit 1
    fi
}

ensure_config() {
    if [[ ! -d "$CONFIG_DIR" ]]; then
        mkdir -p "$CONFIG_DIR"
    fi
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        gum style --foreground "$COLOR_WARNING" "⚠️  Configuration file not found. Creating default..."
        
        # Create default config using simple key-value for now to avoid yq dependency
        cat > "$CONFIG_FILE" <<EOF
api_xai_api_key=""
api_anthropic_api_key=""
path_bark_repo_default="$DEFAULT_BARK_REPO"
path_output_dir="$DEFAULT_OUTPUT_DIR"
pref_model_backend="xai-sdk"
EOF
    fi
}

read_config() {
    # Simple grep-based config reader to avoid extra dependencies
    # Usage: read_config "key_name"
    local key=$1
    local val
    # Grep the key, cut value, remove quotes, and strip ANY whitespace/newlines
    val=$(grep "^$key=" "$CONFIG_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d '[:space:]')
    echo "$val"
}

update_config() {
    # Usage: update_config "key" "value"
    local key=$1
    local val=$2
    # Escape slashes for sed
    local esc_val=$(echo "$val" | sed 's/\//\\\//g')
    
    if grep -q "^$key=" "$CONFIG_FILE"; then
        sed -i '' "s/^$key=.*/$key=\"$esc_val\"/" "$CONFIG_FILE"
    else
        echo "$key=\"$val\"" >> "$CONFIG_FILE"
    fi
}

configure_wizard() {
    gum style --foreground "$COLOR_PRIMARY" --border double --padding "1 2" "⚙️  Configuration Wizard"
    
    # 1. API Keys
    local current_xai=$(read_config "api_xai_api_key")
    gum style "Enter xAI API Key (Leave blank to keep current):"
    local new_xai=$(gum input --placeholder "xai-..." --password)
    if [[ -n "$new_xai" ]]; then
        update_config "api_xai_api_key" "$new_xai"
    fi

    local current_anthropic=$(read_config "api_anthropic_api_key")
    gum style "Enter Anthropic API Key (Leave blank to keep current):"
    local new_anthropic=$(gum input --placeholder "sk-ant-..." --password)
    if [[ -n "$new_anthropic" ]]; then
        update_config "api_anthropic_api_key" "$new_anthropic"
    fi
    
    # 2. Paths
    local current_out=$(read_config "path_output_dir")
    gum style "Output Directory:"
    local new_out=$(gum input --value "$current_out" --placeholder "/path/to/output")
    update_config "path_output_dir" "$new_out"
    
    # 3. Preferences
    local current_backend=$(read_config "pref_model_backend")
    gum style "Preferred Backend:"
    local new_backend=$(gum choose --selected "$current_backend" "xai-sdk" "xai-http" "anthropic")
    update_config "pref_model_backend" "$new_backend"
    
    gum style --foreground "$COLOR_SUCCESS" "✅ Configuration saved!"
    sleep 1
}

validate_url() {
    if [[ ! "$1" =~ ^https?:// ]]; then
        return 1
    fi
    return 0
}

# --- Workflows ---

run_bark_dissector() {
    gum style --foreground "$COLOR_PRIMARY" --border double --padding "1 2" "🐕 Bark Dissector & Analysis"
    
    # Get directory of this script
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local wrapper_script="$script_dir/bark_CLI_wrapper.py"
    
    if [[ ! -f "$wrapper_script" ]]; then
       gum style --foreground "$COLOR_ERROR" "Wrapper script not found at: $wrapper_script"
       return
    fi

    # Check API keys
    local xai_key=$(read_config "api_xai_api_key")
    if [[ -z "$xai_key" ]]; then
        gum style --foreground "$COLOR_ERROR" "❌ xAI API Key missing!"
        if gum confirm "Configure now?"; then
            configure_wizard
            xai_key=$(read_config "api_xai_api_key")
            [[ -z "$xai_key" ]] && return
        else
            return
        fi
    fi
    
    # Step 1: Repo URL
    local repo_url=""
    while [[ -z "$repo_url" ]]; do
        repo_url=$(gum input --placeholder "https://github.com/suno-ai/bark" --prompt "Repository URL: " --width 60)
        if [[ -z "$repo_url" ]]; then
             if ! gum confirm "No URL entered. Try again?" --affirmative="Retry" --negative="Cancel"; then
                return
             fi
        elif ! validate_url "$repo_url"; then
            gum style --foreground "$COLOR_WARNING" "Invalid URL format. Must start with http:// or https://"
            repo_url=""
        fi
    done
    
    # Step 2: Protocol
    local clone_opt=""
    if gum confirm "Clone/Update repository locally?" --affirmative="Clone/Update" --negative="Skip"; then
        clone_opt="--auto-clone"
    fi
    
    # Step 3: Phases
    gum style "Select Analysis Phases (Space to select, Enter to confirm)"
    local phases=$(gum choose --no-limit --cursor.foreground="$COLOR_PRIMARY" --selected.foreground="$COLOR_PRIMARY" \
        "overview" \
        "c4_context" \
        "c4_container" \
        "models" \
        "generation" \
        "encodec" \
        "training" \
        "inference" \
        "comparison" \
        "synthesis")
        
    if [[ -z "$phases" ]]; then
        gum style --foreground "$COLOR_WARNING" "No phases selected. Aborting."
        return
    fi
    
    # Convert newlines to commas for the python script
    phases=$(echo "$phases" | tr '\n' ',')
    # Remove trailing comma
    phases=${phases%,}
    
    # Step 4: Backend
    local default_backend=$(read_config "pref_model_backend")
    local backend=$(gum choose --header "Select Backend" --selected "$default_backend" "xai-sdk" "xai-http" "anthropic")
    
    # Execute
    local output_dir=$(read_config "path_output_dir")
    
    # Export keys for the python script (wrapper passes them through)
    export XAI_API_KEY="$xai_key"
    export ANTHROPIC_API_KEY=$(read_config "api_anthropic_api_key")
    
    local cmd="python3 \"$wrapper_script\" --repo \"$repo_url\" --phases \"$phases\" --backend \"$backend\" --output \"$output_dir\" $clone_opt"
    
    gum style --foreground "$COLOR_MUTED" "Running command: $cmd"
    
    if gum spin --spinner dot --title "Analyzing repository..." --show-output -- bash -c "$cmd"; then
        gum style --foreground "$COLOR_SUCCESS" --border double "✅ Analysis Complete!"
        gum style "Report saved to: $output_dir/BARK_DISSECTION.md"
    else
        gum style --foreground "$COLOR_ERROR" "❌ Analysis failed."
    fi
    
    echo "$(date -Iseconds)|bark-dissector|$repo_url|done" >> "$HISTORY_FILE"
    
    # Wait for user acknowledgment
    gum confirm "Return to menu?" || exit 0
}

run_dataset_audit() {
    gum style --foreground "$COLOR_PRIMARY" --border double --padding "1 2" "📊 Dataset Audit Engine"
    
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local audit_script="$script_dir/dataseta_deepresearch.py"
    
    if [[ ! -f "$audit_script" ]]; then
       gum style --foreground "$COLOR_ERROR" "Audit script not found at: $audit_script"
       return
    fi
    
    # Step 1: Source
    # Note: dataseta_deepresearch.py seems to work on a fixed set of files unless overwritten.
    # The user can just select passes.
    # We can invoke it differently based on what they want.
    
    # Step 2: Passes
    local passes=$(gum choose --no-limit --header "Select Audit Passes" \
        "Pass 1: Interface Contracts" \
        "Pass 2: Audit Findings" \
        "Pass 3: Full Audit & Fixes")
        
    if [[ -z "$passes" ]]; then
        gum style --foreground "$COLOR_WARNING" "No passes selected. Aborting."
        return
    fi
    
    local pass_flags=""
    if [[ "$passes" == *"Pass 1"* ]] && [[ "$passes" != *"Pass 2"* ]] && [[ "$passes" != *"Pass 3"* ]]; then
        pass_flags="--pass1-only"
    elif [[ "$passes" == *"Pass 2"* ]] && [[ "$passes" != *"Pass 3"* ]]; then
        # If Pass 2 is selected (implies pass 1 run or skipped?), the script has --pass2-only which runs pass1 then pass2.
        pass_flags="--pass2-only"
    else
        # Full run (default)
        pass_flags=""
    fi

    # Step 3: Output
    local default_out=$(read_config "path_output_dir")
    local output_file=$(gum input --value "$default_out/dataset_audit_report.md" --prompt "Output File: ")
    local output_flag="--output \"$output_file\""
    
    # Step 4: Fixes (implied by full run, but we can check if force overwrite is needed)
    local force_flag=""
    if gum confirm "Overwrite existing reports?" --default=no; then
        force_flag="--force"
    fi
    
    local verbose_flag=""
    # Ask for verbose?
    if gum confirm "Enable verbose logging?" --default=no; then
         verbose_flag="--verbose"
    fi

    # Execute
    # We need API KEY for this too
    local xai_key=$(read_config "api_xai_api_key")
    export XAI_API_KEY="$xai_key"
    
    local cmd="python3 \"$audit_script\" $output_flag $pass_flags $force_flag $verbose_flag"
    
    gum style --foreground "$COLOR_MUTED" "Running command: $cmd"
    
    if gum spin --spinner minidot --title "Running Audit..." --show-output -- bash -c "$cmd"; then
        gum style --foreground "$COLOR_SUCCESS" --border double "✅ Audit Complete!"
    else
        gum style --foreground "$COLOR_ERROR" "❌ Audit failed."
    fi
    
    echo "$(date -Iseconds)|dataset-audit|local|done" >> "$HISTORY_FILE"
    
    gum confirm "Return to menu?" || exit 0
}

show_history() {
    if [[ -f "$HISTORY_FILE" ]]; then
        gum style --foreground "$COLOR_PRIMARY" "Recent Activity"
        tail -n 20 "$HISTORY_FILE" | gum table --columns "Date,Tool,Target,Status" --separator="|"
        gum confirm "Back" || exit 0
    else
        gum style --foreground "$COLOR_MUTED" "No history found."
        sleep 1
    fi
}

# --- Main Logic ---

main() {
    check_dependencies
    ensure_config
    
    # Handle args
    if [[ "${1:-}" == "--config" ]]; then
        configure_wizard
        exit 0
    fi

    while true; do
        clear
        gum style \
            --foreground "$COLOR_PRIMARY" \
            --border double \
            --padding "1 2" \
            --margin "1 0" \
            --align center \
            "🔬 Codex: Deep Research Agent System"
            
        CHOICE=$(gum choose \
            --cursor.foreground="$COLOR_PRIMARY" \
            --selected.foreground="$COLOR_PRIMARY" \
            --header "Select Research Mode" \
            "🐕 Bark Dissector (Repository Analysis)" \
            "📊 Dataset Audit Engine" \
            "⚙️  Configuration" \
            "📜 History" \
            "❌ Exit") || exit 0
            
        case "$CHOICE" in
            "🐕 Bark Dissector"*)
                run_bark_dissector
                ;;
            "📊 Dataset Audit"*)
                run_dataset_audit
                ;;
            "⚙️  Configuration")
                configure_wizard
                ;;
            "📜 History")
                show_history
                ;;
            "❌ Exit")
                gum style --foreground "$COLOR_MUTED" "Goodbye."
                exit 0
                ;;
        esac
    done
}

main "$@"
