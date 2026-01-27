#!/bin/bash

# MadSci CLI - A retro-futuristic interface for SmolLM2 & Research Systems

if ! command -v gum &> /dev/null; then
    echo "gum could not be found, please install it with 'brew install gum'"
    exit 1
fi

# -- Styling Constants --
BORDER_COLOR="212"
TEXT_COLOR="212"
ACCENT_COLOR="99"
ERROR_COLOR="196"
SUCCESS_COLOR="04B575"

# Resolve absolute path to this script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Ensure Python CLI is executable
chmod +x madsci_cli.py

clear

# -- Intro Sequence --
gum style \
    --foreground "$TEXT_COLOR" --border-foreground "$BORDER_COLOR" --border double \
    --align center --width 60 --margin "1 2" --padding "2 4" \
    'MAD SCIENTIST TERMINAL' 'v2.1-unified'

echo -e "Initializing secure connection..."
sleep 0.5

# Get User Credentials
echo -e "Please identify yourself, operator."
NAME=$(gum input --placeholder "Enter Class-4 credentials...")

if [ -z "$NAME" ]; then
    NAME="Unknown Entity"
fi

echo -e "Welcome, $(gum style --foreground "$ACCENT_COLOR" "$NAME"). Access Granted."
sleep 1
clear

# -- Main Loop --
while true; do
    # Main Menu
    # Ambient Commentary Logic (The "Psycho Mantis" Module)
    
    # 1. Active App
    OS="$(uname)"
    if [[ "$OS" == "Darwin" ]]; then
        ACTIVE_APP=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null)
    elif [[ "$OS" == "Linux" ]]; then
        if command -v xdotool &> /dev/null; then
            ACTIVE_APP=$(xdotool getwindowfocus getwindowname)
        else
            ACTIVE_APP="Linux System"
        fi
    else
        ACTIVE_APP="Unknown System"
    fi
    
    # 2. Digital Hoarding
    DOWNLOAD_COUNT=$(ls ~/Downloads 2>/dev/null | wc -l | xargs)
    
    # 3. Time
    HOUR=$(date +%H)
    
    HOARDING_NOTE="The user is hoarding $DOWNLOAD_COUNT files in Downloads."
    CONTEXT="User is currently using '$ACTIVE_APP'. $HOARDING_NOTE It is hour $HOUR of the day."
    
    # Generate the commentary
    COMMENTARY=$(gum spin --title "Intercepting Thoughts..." -- python3 madsci_cli.py ambient "$CONTEXT" 2>/dev/null)
    
    clear
    gum style \
        --border normal --margin "1" --padding "1 2" --border-foreground 212 \
        "LOG: $(date +%H:%M:%S)" \
        "OBSERVATION: $COMMENTARY"

    echo " " 

    # -- Glitch Animation --
    glitch_text() {
        PHRASES=(
            "looking to buy that new cat bed that's gonna fetch up to 10,000 on the next auction run"
            "lookin' to snag my first job from the void"
            "I have a car, but never drive much"
            "seeking a bird to bird my return"
            "the cigarette is sold, the dog is commissioned"
        )
        PHRASE=${PHRASES[$RANDOM % ${#PHRASES[@]}]}
        echo -ne "\033[38;5;240m" >&2
        for (( i=0; i<${#PHRASE}; i++ )); do
            echo -ne "${PHRASE:$i:1}" >&2
            sleep 0.01
        done
        echo -ne "\033[0m" >&2
        sleep 0.1
        echo -ne "\r\033[K" >&2
    }

    OPTION=$(gum choose \
        "System Diagnostics" \
        "Research Station" \
        "Snapshot Station" \
        "Pipeline Control" \
        "Workflow Automation" \
        "Commune with Static" \
        "Decrypt Archives" \
        "Exit Terminal" \
        --cursor="> " --header="MADSCI TERMINAL v2.1")
    
    case $OPTION in
        "System Diagnostics")
            glitch_text
            gum spin --spinner dot --title "Checking flux..." -- sleep 1
            python3 madsci_cli.py status
            gum confirm "Return to menu?" && continue || break
            ;;
            
        "Research Station")
            glitch_text
            SUB_OPT=$(gum choose "Bark Dissector" "Dataset Audit" "Research Status" "Init Config" "Back")
            case $SUB_OPT in
                "Bark Dissector")
                    # Python CLI now handles interactive GUM selection if no target provided
                    python3 madsci_cli.py research bark
                    ;;
                "Dataset Audit")
                    python3 madsci_cli.py research audit --help
                    ;;
                "Research Status")
                    python3 madsci_cli.py research status
                    ;;
                "Init Config")
                    python3 madsci_cli.py research init
                    ;;
            esac
            gum confirm "Return to menu?" && continue
            ;;
            
        "Snapshot Station")
            glitch_text
            # Python CLI now handles interactive GUM selection
            python3 madsci_cli.py snapshot
            gum confirm "Return to menu?" && continue
            ;;
            
        "Pipeline Control")
            glitch_text
            INPUT_FILE=$(gum file $(pwd) --height 10)
            if [ -n "$INPUT_FILE" ]; then
                DEVICE=$(gum choose "cuda" "cpu")
                STEMS=$(gum input --placeholder "Num Stems (4)" --value "4")
                python3 madsci_cli.py pipeline "$INPUT_FILE" --device "$DEVICE" --num-stems "$STEMS"
            fi
            gum confirm "Return to menu?" && continue
            ;;
        
        "Workflow Automation")
            glitch_text
            SUB_OPT=$(gum choose "Full Analysis Chain" "Batch Pipeline" "Back")
            case $SUB_OPT in
                "Full Analysis Chain")
                    TARGET=$(gum input --placeholder "Target System (bark)" --value "bark")
                    UPDATE=$(gum choose "Yes" "No")
                    FLAGS=""
                    if [ "$UPDATE" == "Yes" ]; then
                        FLAGS="--update-snapshots"
                    fi
                    python3 madsci_cli.py workflow full-analysis --target "$TARGET" $FLAGS
                    ;;
                "Batch Pipeline")
                    DIR=$(gum file --directory $(pwd))
                    if [ -n "$DIR" ]; then
                         python3 madsci_cli.py workflow pipeline-batch --input-dir "$DIR"
                    fi
                    ;;
            esac
            gum confirm "Return to menu?" && continue
            ;;
            
        "Commune with Static")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "0 1" "VISUALIZING VOID..."
            glitch_text 
            echo "Signal acquired. Type 'exit' to sever connection."
            
            while true; do
                echo ""
                PROMPT=$(gum input --placeholder "Transmit query...")
                
                if [ "$PROMPT" == "exit" ] || [ -z "$PROMPT" ]; then
                    break
                fi
                
                glitch_text
                gum spin --spinner pulse --title "Processing..." -- python3 madsci_cli.py commune "$PROMPT" | gum format
            done
            clear
            ;;
            
        "Decrypt Archives")
            glitch_text
            gum style --foreground 212 "Decrypting..."
            ls -la | gum filter
            ;;
            
        "Exit Terminal")
            gum style --foreground 212 "Reality restoring..."
            exit 0
            ;;
    esac
done

# -- Outro --
clear
gum style \
    --foreground "$TEXT_COLOR" --border double --padding "1 2" \
    "Session Terminated." "Good luck, $(gum style --foreground "$ACCENT_COLOR" "$NAME")."
