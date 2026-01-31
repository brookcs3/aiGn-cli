#!/bin/bash

# CareerAI CLI - GenAI Agent for Career Task Automation
# CS 462 Career Preparation Activity
#
# Real backend powered by:
# - SmolLM2 (local LLM)
# - JobSpy (job search)
# - PyMuPDF/python-docx (document parsing)

# -- Dependency Check --
if ! command -v gum &> /dev/null; then
    echo "gum could not be found, please install it with 'brew install gum' or './install.sh'"
    exit 1
fi

if ! command -v magic &> /dev/null; then
    echo "magic (modular) could not be found. Please run './install.sh' first."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install it with 'brew install jq' or './install.sh'"
    exit 1
fi

# -- Styling Constants --
BORDER_COLOR="39"
TEXT_COLOR="231"
ACCENT_COLOR="208"
SUCCESS_COLOR="82"
WARNING_COLOR="220"
ERROR_COLOR="196"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SRC_DIR="$SCRIPT_DIR/src"
AGENT_DIR="$SRC_DIR/agent"
JOBS_DIR="$SRC_DIR/jobs"
UTILS_DIR="$SRC_DIR/utils"
PROMPTS_DIR="$SRC_DIR/prompts"
BIN_DIR="$SCRIPT_DIR/bin"

cd "$SCRIPT_DIR" || exit 1

# -- Helper Functions --
run_python() {
    magic run python "$@"
}

call_agent() {
    local script="$1"
    shift
    run_python "$AGENT_DIR/$script" "$@" 2>/dev/null
}

call_jobs() {
    local script="$1"
    shift
    run_python "$JOBS_DIR/$script" "$@" 2>/dev/null
}

call_utils() {
    local script="$1"
    shift
    run_python "$UTILS_DIR/$script" "$@" 2>/dev/null
}

clear

# -- Intro Sequence --
gum style \
    --foreground "$TEXT_COLOR" --border-foreground "$BORDER_COLOR" --border double \
    --align center --width 60 --margin "1 2" --padding "2 4" \
    'CAREER AI AGENT' 'Resume Analyzer & Job Match System' 'v2.0 - Real Backend'

sleep 0.5

# Get User Name
echo ""
NAME=$(gum input --placeholder "Enter your name..." --header "Welcome! Let's optimize your career.")

if [ -z "$NAME" ]; then
    NAME="User"
fi

echo ""
gum style --foreground "$ACCENT_COLOR" "Hello, $NAME! I'm your AI career assistant."
sleep 1
clear

# -- Main Loop --
while true; do
    clear
    gum style \
        --foreground "$TEXT_COLOR" --border-foreground "$BORDER_COLOR" --border normal \
        --align center --width 50 --padding "1 2" \
        "CareerAI Agent" "Logged in as: $NAME"

    echo ""

    OPTION=$(gum choose \
        "Resume Analyzer" \
        "Match Jobs to Skills" \
        "Generate Cover Letter" \
        "Interview Prep Questions" \
        "Technical Assessment Feedback" \
        "Exit" \
        --cursor="> " --header="Select a career task:")

    case $OPTION in
        "Resume Analyzer")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\360\237\223\204') RESUME ANALYZER" "Upload your resume for AI-powered feedback"
            echo ""

            # File picker - filter to resume formats only
            gum style --foreground "$TEXT_COLOR" "Supported formats: PDF, DOCX, TXT"
            echo ""

            while true; do
                FILE_METHOD=$(gum choose "Browse for file" "Paste file path")

                if [ "$FILE_METHOD" = "Paste file path" ]; then
                    RESUME_FILE=$(gum input --placeholder "Enter full path to resume...")
                else
                    if [ -x "$BIN_DIR/fuzzy-picker" ]; then
                         RESUME_FILE=$("$BIN_DIR/fuzzy-picker" < /dev/tty 2>&1)
                    else
                         RESUME_FILE=$(gum file --file)
                    fi
                fi

                if [ -z "$RESUME_FILE" ]; then
                    gum style --foreground "$ERROR_COLOR" "No file selected."
                    sleep 1
                    continue 2
                fi

                # Check file exists if path was pasted
                if [ ! -f "$RESUME_FILE" ]; then
                    gum style --foreground "$ERROR_COLOR" "File not found: $RESUME_FILE"
                    sleep 1
                    continue
                fi

                # Validate file extension
                EXT="${RESUME_FILE##*.}"
                EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')

                if [[ "$EXT_LOWER" == "pdf" || "$EXT_LOWER" == "docx" || "$EXT_LOWER" == "doc" || "$EXT_LOWER" == "txt" ]]; then
                    break
                else
                    gum style --foreground "$ERROR_COLOR" "Invalid file type: .$EXT"
                    gum style --foreground "$WARNING_COLOR" "Please select a PDF, DOCX, or TXT file."
                    sleep 1
                fi
            done

            gum style --foreground "$TEXT_COLOR" "Selected: $(basename "$RESUME_FILE")"
            echo ""

            # Run analysis pipeline: resume_parser.py -> llm_inference.py
            # Save prompt to temp file
            PROMPT_TEMP=$(mktemp)
            call_utils "resume_parser.py" --input-file "$RESUME_FILE" --output "$PROMPT_TEMP"

            # Run AI with spinner
            RESULT=$(cat "$PROMPT_TEMP" | gum spin --spinner pulse --title "Analyzing with AI..." -- magic run python "$AGENT_DIR/llm_inference.py" --chat 2>/dev/null)
            rm -f "$PROMPT_TEMP"

            # Extract and flatten JSON from response with pandas
            # Note: We need to use magic run python for this inline script too if it uses pandas
            JSON_RESULT=$(echo "$RESULT" | magic run python -c "
import sys, json, re
import pandas as pd

text = sys.stdin.read()
text = re.sub(r'\`\`\`json\s*', '', text)
text = re.sub(r'\`\`\`\s*', '', text)

match = re.search(r'\{.*\}', text, re.DOTALL)
if match:
    obj = json.loads(match.group())
    df = pd.json_normalize(obj)
    flat = df.to_dict(orient='records')[0]
    print(json.dumps(flat))
" 2>/dev/null)

            if [ -z "$JSON_RESULT" ] || ! echo "$JSON_RESULT" | jq . >/dev/null 2>&1; then
                gum style --foreground "$WARNING_COLOR" --border normal --padding "1 2" \
                    "AI Response (raw):" "" "$RESULT"
                gum confirm "Return to menu?" && continue || break
            fi

            echo ""
            gum style --foreground "$SUCCESS_COLOR" --border double --padding "1 2" \
                "$(printf '\342\234\205') ANALYSIS COMPLETE"
            echo ""

            # Extract fields from flattened JSON (pandas uses dot notation as keys)
            CANDIDATE_PROFILE=$(echo "$JSON_RESULT" | jq -r '.["variable_name.candidate_profile"] // .candidate_profile // "N/A"')
            TARGET_ROLE=$(echo "$JSON_RESULT" | jq -r '.["variable_name.target_role"] // .target_role // "N/A"')
            CONTENT_TYPE=$(echo "$JSON_RESULT" | jq -r '.["variable_name.content_type"] // .content_type // "N/A"')
            SUMMARY=$(echo "$JSON_RESULT" | jq -r '.["variable_name.summary"] // .summary // "N/A"')

            # Build key points display
            KEY_POINTS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && KEY_POINTS_TEXT="$KEY_POINTS_TEXT
  $(printf '\342\200\242') $line"
            done < <(echo "$JSON_RESULT" | jq -r '.["variable_name.key_points"][]? // .key_points[]?' 2>/dev/null)

            # Build strengths display
            STRENGTHS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && STRENGTHS_TEXT="$STRENGTHS_TEXT
  $(printf '\342\234\223') $line"
            done < <(echo "$JSON_RESULT" | jq -r '.["variable_name.strengths"][]? // .strengths[]?' 2>/dev/null)

            # Build gaps display
            GAPS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && GAPS_TEXT="$GAPS_TEXT
  $(printf '\342\200\242') $line"
            done < <(echo "$JSON_RESULT" | jq -r '.["variable_name.gaps_or_risks"][]? // .gaps_or_risks[]?' 2>/dev/null)

            # Build markdown analysis display
            ANALYSIS_MD="# Resume Analysis

## Candidate Profile
$CANDIDATE_PROFILE

**Target Role:** $TARGET_ROLE
**Type:** $CONTENT_TYPE

## Summary
$SUMMARY

## Key Points
$KEY_POINTS_TEXT

## Strengths
$STRENGTHS_TEXT

## Areas to Improve
$GAPS_TEXT"

            # Display with glow (renders markdown, auto-scales to terminal)
            echo "$ANALYSIS_MD" | glow -

            echo ""

            gum confirm "Save this analysis to a file?" && {
                OUTFILE="resume_analysis_$(date +%Y%m%d_%H%M%S).txt"
                {
                    echo "Resume Analysis for $NAME - $(date)"
                    echo "File: $(basename "$RESUME_FILE")"
                    echo ""
                    echo "CANDIDATE PROFILE: $CANDIDATE_PROFILE"
                    echo "TARGET ROLE: $TARGET_ROLE"
                    echo "TYPE: $CONTENT_TYPE"
                    echo ""
                    echo "SUMMARY:"
                    echo "$SUMMARY"
                    echo ""
                    echo "KEY POINTS:$KEY_POINTS_TEXT"
                    echo ""
                    echo "STRENGTHS:$STRENGTHS_TEXT"
                    echo ""
                    echo "AREAS TO IMPROVE:$GAPS_TEXT"
                    echo ""
                    echo "--- RAW JSON ---"
                    echo "$JSON_RESULT" | jq .
                } > "$OUTFILE"
                gum style --foreground "$SUCCESS_COLOR" "Saved to: $OUTFILE"
            }

            gum confirm "Return to menu?" && continue || break
            ;;

        "Match Jobs to Skills")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\360\237\222\274') JOB MATCHER" "Find roles that match your skillset"
            echo ""

            # Get skills input
            SKILLS=$(gum input --placeholder "Enter your skills (comma-separated)..." \
                --header "What are your top skills?" \
                --value "Python, JavaScript, React, SQL")

            if [ -z "$SKILLS" ]; then
                SKILLS="Python, JavaScript, React, SQL"
            fi

            echo ""
            LOCATION=$(gum input --placeholder "Preferred location..." \
                --header "Where do you want to work?" \
                --value "Remote")

            echo ""
            gum spin --spinner dot --title "Searching job databases..." -- sleep 0.5

            RESULT=$(call_jobs "job_matcher.py" "$SKILLS" "$LOCATION")

            gum spin --spinner pulse --title "AI matching algorithm running..." -- sleep 0.5

            # Check if demo mode
            IS_DEMO=$(echo "$RESULT" | jq -r '.is_demo // false')

            if [ "$IS_DEMO" = "true" ]; then
                echo ""
                DEMO_WARNING=$(echo "$RESULT" | jq -r '.demo_warning')
                HOW_TO_FIX=$(echo "$RESULT" | jq -r '.how_to_fix')
                gum style --foreground "$WARNING_COLOR" --border normal --padding "1 2" \
                    "WARNING: $DEMO_WARNING" \
                    "" \
                    "To enable real job searches:" \
                    "  $HOW_TO_FIX"
                echo ""
            fi

            # Get job count
            TOTAL=$(echo "$RESULT" | jq -r '.total_found')

            if [ "$IS_DEMO" != "true" ]; then
                echo ""
                gum style --foreground "$SUCCESS_COLOR" "$(printf '\342\234\205') Found $TOTAL matching positions!"
            else
                echo ""
                gum style --foreground "$WARNING_COLOR" "$(printf '\342\232\240\357\270\217') Showing $TOTAL sample jobs (demo mode)"
            fi
            echo ""

            # Build formatted job list for display
            JOB_OUTPUT=$(echo "$RESULT" | jq -r '
                .jobs[:5] | to_entries[] |
                "\(.key + 1). \(.value.title) @ \(.value.company) (\(.value.match_score)% match)\n   $(printf '\360\237\222\260') $\(.value.salary_min // "N/A")-$\(.value.salary_max // "N/A")k | $(printf '\360\237\223\215') \(.value.location) | $(printf '\360\237\217\267\357\270\217')\(.value.industry // "Tech")"
            ' 2>/dev/null)

            # Format with proper emojis using printf
            JOB_DISPLAY=""
            COUNT=1
            while IFS= read -r job; do
                TITLE=$(echo "$job" | jq -r '.title')
                COMPANY=$(echo "$job" | jq -r '.company')
                SCORE=$(echo "$job" | jq -r '.match_score')
                SAL_MIN=$(echo "$job" | jq -r '.salary_min // "N/A"')
                SAL_MAX=$(echo "$job" | jq -r '.salary_max // "N/A"')
                LOCATION=$(echo "$job" | jq -r '.location')
                INDUSTRY=$(echo "$job" | jq -r '.industry // "Tech"')

                # Format salary (convert floats to ints first)
                if [ "$SAL_MIN" != "null" ] && [ "$SAL_MIN" != "N/A" ]; then
                    SAL_MIN_INT=${SAL_MIN%.*}
                    SAL_MAX_INT=${SAL_MAX%.*}
                    SAL_MIN_K=$((SAL_MIN_INT / 1000))
                    SAL_MAX_K=$((SAL_MAX_INT / 1000))
                    SALARY="\$${SAL_MIN_K}-${SAL_MAX_K}k"
                else
                    SALARY="Salary N/A"
                fi

                URL=$(echo "$job" | jq -r '.url // "N/A"')

                JOB_DISPLAY="$JOB_DISPLAY
$COUNT. $TITLE @ $COMPANY (${SCORE}% match)
   $(printf '\360\237\222\260') $SALARY | $(printf '\360\237\223\215') $LOCATION | $(printf '\360\237\217\267\357\270\217')$INDUSTRY
   $(printf '\360\237\224\227') $URL
"
                COUNT=$((COUNT + 1))
            done < <(echo "$RESULT" | jq -c '.jobs[:10][]')

            # Display in scrollable pager (using custom gum with auto-fit height)
            GUM_CUSTOM="$SCRIPT_DIR/tools/gum/gum-custom"
            if [ -x "$GUM_CUSTOM" ]; then
                echo "$(printf '\360\237\216\257') TOP JOB MATCHES (Based on: $SKILLS)

$JOB_DISPLAY" | "$GUM_CUSTOM" pager --viewport-height=-1 --show-line-numbers=false
            else
                gum pager "$(printf '\360\237\216\257') TOP JOB MATCHES (Based on: $SKILLS)

$JOB_DISPLAY"
            fi

            echo ""
            gum style --border normal --border-foreground "$ACCENT_COLOR" --padding "1 2" \
                "$(printf '\360\237\223\213') Found $TOTAL jobs for: $SKILLS" \
                "$(printf '\360\237\223\215') Location: $LOCATION" \
                "" \
                "Tip: Copy a URL above to apply directly"

            FROM_CACHE=$(echo "$RESULT" | jq -r '.from_cache // false')
            if [ "$FROM_CACHE" = "true" ]; then
                CACHE_AGE=$(echo "$RESULT" | jq -r '.cache_age_minutes')
                echo ""
                gum style --foreground "$TEXT_COLOR" --italic "Results from cache ($CACHE_AGE minutes ago)"
            fi

            echo ""
            gum confirm "Save job list to file?" && {
                OUTFILE="job_matches_$(date +%Y%m%d_%H%M%S).txt"
                echo "Job Matches for: $SKILLS" > "$OUTFILE"
                echo "Location: $LOCATION" >> "$OUTFILE"
                echo "Generated: $(date)" >> "$OUTFILE"
                echo "" >> "$OUTFILE"
                echo "$RESULT" | jq -r '.jobs[] | "\(.title) @ \(.company)\nMatch: \(.match_score)%\nLocation: \(.location)\nSalary: \(.salary_min // "N/A") - \(.salary_max // "N/A")\nURL: \(.url // "N/A")\n"' >> "$OUTFILE"
                gum style --foreground "$SUCCESS_COLOR" "Saved to: $OUTFILE"
            }

            echo ""
            gum confirm "Return to menu?" && continue || break
            ;;

        "Generate Cover Letter")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\342\234\215\357\270\217') JOB APPLICATION PIPELINE" "AI-powered resume & cover letter generation"
            echo ""

            # Run the job application pipeline directly
            # It handles everything: job search, selection, Q&A, generation, saving
            call_jobs "job_application_pipeline.py" </dev/tty

            echo ""
            gum confirm "Return to menu?" && continue || break
            ;;

        "Interview Prep Questions")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\360\237\222\254') INTERVIEW PREP" "AI-personalized interview questions"
            echo ""

            # Get user context for personalization
            TARGET_ROLE=$(gum input --placeholder "e.g., Senior Software Engineer, Product Manager..." \
                --header "What role are you interviewing for?" \
                --value "Software Engineer")

            if [ -z "$TARGET_ROLE" ]; then
                TARGET_ROLE="Software Engineer"
            fi

            echo ""
            SKILLS=$(gum input --placeholder "e.g., Python, React, System Design..." \
                --header "What are your key skills?" \
                --value "Python, JavaScript, React, SQL")

            if [ -z "$SKILLS" ]; then
                SKILLS="Python, JavaScript, React, SQL"
            fi

            # Category descriptions to help user choose
            echo ""
            gum style --foreground "$TEXT_COLOR" "Select interview type:"
            echo ""
            gum style --foreground "$TEXT_COLOR" --italic \
                "Behavioral - Past experiences and soft skills" \
                "Technical - Coding problems and algorithms" \
                "System Design - Architecture and scaling" \
                "Culture Fit - Values and work style"
            echo ""

            TYPE=$(gum choose "Behavioral" "Technical" "System Design" "Culture Fit" \
                --cursor="> ")

            echo ""
            gum spin --spinner dot --title "Analyzing your profile..." -- sleep 0.3

            # Build personalized prompt from template
            PROMPT_TEMP=$(mktemp)
            sed "s/{{INTERVIEW_TYPE}}/$TYPE/g; s/{{TARGET_ROLE}}/$TARGET_ROLE/g; s/{{SKILLS}}/$SKILLS/g" \
                "$PROMPTS_DIR/interview_prep_prompt.txt" > "$PROMPT_TEMP"

            # Generate with AI
            RESULT=$(cat "$PROMPT_TEMP" | gum spin --spinner pulse --title "Generating personalized questions..." -- magic run python "$AGENT_DIR/llm_inference.py" --chat 2>/dev/null)
            rm -f "$PROMPT_TEMP"

            # Strip markdown code block wrappers if present
            RESULT=$(echo "$RESULT" | magic run python -c "
import sys, re
text = sys.stdin.read()
text = re.sub(r'\`\`\`markdown\s*', '', text)
text = re.sub(r'\`\`\`\s*', '', text)
print(text.strip())
" 2>/dev/null)

            if [ -z "$RESULT" ]; then
                gum style --foreground "$ERROR_COLOR" "Error: Failed to generate questions"
                gum confirm "Return to menu?" && continue || break
            fi

            echo ""
            gum style --foreground "$SUCCESS_COLOR" "$(printf '\342\234\205') Interview prep guide generated!"
            echo ""

            # Display with glow (built-in TUI with scrolling)
            echo "$RESULT" | glow -

            echo ""
            gum confirm "Save this guide to a file?" && {
                OUTFILE="interview_prep_$(echo "$TYPE" | tr ' ' '_' | tr '[:upper:]' '[:lower:]')_$(date +%Y%m%d_%H%M%S).md"
                echo "$RESULT" > "$OUTFILE"
                gum style --foreground "$SUCCESS_COLOR" "Saved to: $OUTFILE"
            }

            echo ""
            gum confirm "Return to menu?" && continue || break
            ;;

        "Technical Assessment Feedback")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\360\237\223\212') TECHNICAL ASSESSMENT ANALYZER" "Get feedback on coding challenges"
            echo ""

            gum style --foreground "$TEXT_COLOR" "Select your code file for analysis:"
            gum style --foreground "$TEXT_COLOR" --italic "(Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, etc.)"
            echo ""

            while true; do
                FILE_METHOD=$(gum choose "Browse for file" "Paste file path")

                if [ "$FILE_METHOD" = "Paste file path" ]; then
                    CODE_FILE=$(gum input --placeholder "Enter full path to code file...")
                else
                    if [ -x "$BIN_DIR/fuzzy-picker" ]; then
                         CODE_FILE=$("$BIN_DIR/fuzzy-picker" </dev/tty)
                    else
                         CODE_FILE=$(gum file --file)
                    fi
                fi

                if [ -z "$CODE_FILE" ]; then
                    gum style --foreground "$ERROR_COLOR" "No file selected."
                    sleep 1
                    continue 2
                fi

                if [ ! -f "$CODE_FILE" ]; then
                    gum style --foreground "$ERROR_COLOR" "File not found: $CODE_FILE"
                    sleep 1
                    continue
                fi

                # Validate file extension for code files
                EXT="${CODE_FILE##*.}"
                EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')

                case "$EXT_LOWER" in
                    py|js|ts|jsx|tsx|java|cpp|c|h|hpp|go|rs|rb|php|swift|kt|scala|cs|sh|sql)
                        break
                        ;;
                    *)
                        gum style --foreground "$ERROR_COLOR" "Invalid file type: .$EXT"
                        gum style --foreground "$WARNING_COLOR" "Please select a code file (.py, .js, .java, etc.)"
                        sleep 1
                        ;;
                esac
            done

            gum style --foreground "$TEXT_COLOR" "Analyzing: $(basename "$CODE_FILE")"
            echo ""

            gum spin --spinner dot --title "Parsing code structure..." -- sleep 0.5

            RESULT=$(call_utils "code_analyzer.py" "$CODE_FILE")

            gum spin --spinner pulse --title "AI reviewing logic & patterns..." -- sleep 0.5

            SUCCESS=$(echo "$RESULT" | jq -r '.success')

            if [ "$SUCCESS" != "true" ]; then
                ERROR=$(echo "$RESULT" | jq -r '.error')
                gum style --foreground "$ERROR_COLOR" --border normal --padding "1 2" \
                    "Error analyzing code:" "$ERROR"
                gum confirm "Return to menu?" && continue || break
            fi

            echo ""
            gum style --foreground "$SUCCESS_COLOR" "$(printf '\342\234\205') Analysis Complete!"
            echo ""

            # Display results
            LANGUAGE=$(echo "$RESULT" | jq -r '.language')
            TIME_COMPLEXITY=$(echo "$RESULT" | jq -r '.time_complexity')
            TIME_EXPLANATION=$(echo "$RESULT" | jq -r '.time_explanation')
            SPACE_COMPLEXITY=$(echo "$RESULT" | jq -r '.space_complexity')
            READABILITY=$(echo "$RESULT" | jq -r '.readability_score')

            # Build strengths text
            STRENGTHS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && STRENGTHS_TEXT="$STRENGTHS_TEXT
$(printf '\342\200\242') $line"
            done < <(echo "$RESULT" | jq -r '.strengths[]' 2>/dev/null)

            # Build suggestions text
            SUGGESTIONS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && SUGGESTIONS_TEXT="$SUGGESTIONS_TEXT
$(printf '\342\200\242') $line"
            done < <(echo "$RESULT" | jq -r '.suggestions[]' 2>/dev/null)

            # Overall assessment
            OVERALL=$(echo "$RESULT" | jq -r '.overall')

            # Display in styled box matching mockup
            gum style --border normal --border-foreground "39" --padding "1 2" \
                "$(printf '\360\237\223\212') CODE ASSESSMENT RESULTS" \
                "" \
                "$(printf '\342\217\261\357\270\217') Time Complexity: $TIME_COMPLEXITY - Good!" \
                "$(printf '\360\237\222\276') Space Complexity: $SPACE_COMPLEXITY" \
                "$(printf '\360\237\223\235') Code Readability: $READABILITY" \
                "" \
                "$(printf '\342\234\205') WHAT YOU DID WELL:$STRENGTHS_TEXT" \
                "" \
                "$(printf '\342\232\240\357\270\217') SUGGESTIONS:$SUGGESTIONS_TEXT" \
                "" \
                "$(printf '\360\237\222\241') OVERALL: $OVERALL"

            echo ""
            gum confirm "Return to menu?" && continue || break
            ;;

        "Exit")
            clear
            gum style --foreground "$ACCENT_COLOR" --border double --padding "1 2" --align center \
                "Good luck with your job search, $NAME!" \
                "" \
                "Remember: Every application is one step closer" \
                "to your dream job. Keep going!"
            exit 0
            ;;
    esac
done
