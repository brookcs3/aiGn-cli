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
    echo "gum could not be found, please install it with 'brew install gum'"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "python3 could not be found, please install Python 3.10+"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "jq could not be found, please install it with 'brew install jq'"
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
BACKEND_DIR="$SCRIPT_DIR/backend"
cd "$SCRIPT_DIR" || exit 1

# -- Backend Helper Function --
call_backend() {
    local script="$1"
    shift
    python3 "$BACKEND_DIR/$script" "$@" 2>/dev/null
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
                "RESUME ANALYZER" "Upload your resume for AI-powered feedback"
            echo ""

            # File picker - filter to resume formats only
            gum style --foreground "$TEXT_COLOR" "Supported formats: PDF, DOCX, TXT"
            echo ""

            while true; do
                RESUME_FILE=$(gum file ~ --height 12 --file)

                if [ -z "$RESUME_FILE" ]; then
                    gum style --foreground "$ERROR_COLOR" "No file selected."
                    sleep 1
                    continue 2
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

            # Call real backend with spinner
            gum spin --spinner dot --title "Scanning document structure..." -- sleep 0.5

            RESULT=$(call_backend "resume_analyzer.py" "$RESUME_FILE")

            gum spin --spinner pulse --title "Analyzing content..." -- sleep 0.5

            # Parse JSON result
            SUCCESS=$(echo "$RESULT" | jq -r '.success')

            if [ "$SUCCESS" != "true" ]; then
                ERROR=$(echo "$RESULT" | jq -r '.error')
                gum style --foreground "$ERROR_COLOR" --border normal --padding "1 2" \
                    "Error analyzing resume:" "$ERROR"
                gum confirm "Return to menu?" && continue || break
            fi

            SCORE=$(echo "$RESULT" | jq -r '.score')

            echo ""
            gum style --foreground "$SUCCESS_COLOR" --border double --padding "1 2" \
                "$(printf '\342\234\205') ANALYSIS COMPLETE"

            echo ""

            # Display score with color based on value
            if [ "$SCORE" -ge 70 ]; then
                SCORE_COLOR="$SUCCESS_COLOR"
            elif [ "$SCORE" -ge 50 ]; then
                SCORE_COLOR="$WARNING_COLOR"
            else
                SCORE_COLOR="$ERROR_COLOR"
            fi

            # Build results display
            STRENGTHS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && STRENGTHS_TEXT="$STRENGTHS_TEXT
$(printf '\342\200\242') $line"
            done < <(echo "$RESULT" | jq -r '.strengths[]' 2>/dev/null)

            IMPROVEMENTS_TEXT=""
            while IFS= read -r line; do
                [ -n "$line" ] && IMPROVEMENTS_TEXT="$IMPROVEMENTS_TEXT
$(printf '\342\200\242') $line"
            done < <(echo "$RESULT" | jq -r '.improvements[]' 2>/dev/null)

            RECOMMENDATION=$(echo "$RESULT" | jq -r '.recommendations[0] // empty' 2>/dev/null)

            # Display in styled box matching mockup
            gum style --border normal --border-foreground "39" --padding "1 2" \
                "$(printf '\360\237\223\212') RESUME SCORE: $SCORE/100" \
                "" \
                "$(printf '\342\234\205') STRENGTHS:$STRENGTHS_TEXT" \
                "" \
                "$(printf '\342\232\240\357\270\217') AREAS FOR IMPROVEMENT:$IMPROVEMENTS_TEXT" \
                "" \
                "$(printf '\360\237\222\241') TOP RECOMMENDATION:" \
                "   $RECOMMENDATION"

            echo ""

            gum confirm "Save this analysis to a file?" && {
                OUTFILE="resume_analysis_$(date +%Y%m%d_%H%M%S).txt"
                echo "Resume Analysis for $NAME - $(date)" > "$OUTFILE"
                echo "File: $(basename "$RESUME_FILE")" >> "$OUTFILE"
                echo "Score: $SCORE/100" >> "$OUTFILE"
                echo "" >> "$OUTFILE"
                echo "$RESULT" | jq -r '.' >> "$OUTFILE"
                gum style --foreground "$SUCCESS_COLOR" "Saved to: $OUTFILE"
            }

            gum confirm "Return to menu?" && continue || break
            ;;

        "Match Jobs to Skills")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "JOB MATCHER" "Find roles that match your skillset"
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

            RESULT=$(call_backend "job_matcher.py" "$SKILLS" "$LOCATION")

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

                # Format salary
                if [ "$SAL_MIN" != "null" ] && [ "$SAL_MIN" != "N/A" ]; then
                    SAL_MIN_K=$((SAL_MIN / 1000))
                    SAL_MAX_K=$((SAL_MAX / 1000))
                    SALARY="\$${SAL_MIN_K}-${SAL_MAX_K}k"
                else
                    SALARY="Salary N/A"
                fi

                JOB_DISPLAY="$JOB_DISPLAY
$COUNT. $TITLE @ $COMPANY (${SCORE}% match)
   $(printf '\360\237\222\260') $SALARY | $(printf '\360\237\223\215') $LOCATION | $(printf '\360\237\217\267\357\270\217')$INDUSTRY
"
                COUNT=$((COUNT + 1))
            done < <(echo "$RESULT" | jq -c '.jobs[:5][]')

            # Display in styled box
            gum style --border normal --border-foreground "39" --padding "1 2" \
                "$(printf '\360\237\216\257') TOP 5 JOB MATCHES (Based on: $SKILLS)" \
                "" \
                "$JOB_DISPLAY"

            FROM_CACHE=$(echo "$RESULT" | jq -r '.from_cache // false')
            if [ "$FROM_CACHE" = "true" ]; then
                CACHE_AGE=$(echo "$RESULT" | jq -r '.cache_age_minutes')
                echo ""
                gum style --foreground "$TEXT_COLOR" --italic "Results from cache ($CACHE_AGE minutes ago)"
            fi

            echo ""
            gum confirm "Return to menu?" && continue || break
            ;;

        "Generate Cover Letter")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\342\234\215\357\270\217') COVER LETTER GENERATOR" "AI-powered personalized cover letters"
            echo ""

            COMPANY=$(gum input --placeholder "Company name..." --header "What company are you applying to?")
            [ -z "$COMPANY" ] && COMPANY="Acme Corp"

            ROLE=$(gum input --placeholder "Job title..." --header "What role?")
            [ -z "$ROLE" ] && ROLE="Software Engineer"

            echo ""
            gum style --foreground "$TEXT_COLOR" "Optional: Select your resume to personalize the letter"
            gum style --foreground "$TEXT_COLOR" --italic "(PDF, DOCX, or TXT)"
            RESUME_FILE=$(gum file ~ --height 8 --file) || RESUME_FILE=""

            # Validate file extension if a file was selected
            if [ -n "$RESUME_FILE" ]; then
                EXT="${RESUME_FILE##*.}"
                EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')
                if [[ "$EXT_LOWER" != "pdf" && "$EXT_LOWER" != "docx" && "$EXT_LOWER" != "doc" && "$EXT_LOWER" != "txt" ]]; then
                    gum style --foreground "$WARNING_COLOR" "Skipping invalid file type. Generating without resume."
                    RESUME_FILE=""
                fi
            fi

            echo ""
            gum spin --spinner pulse --title "Generating personalized cover letter..." -- sleep 1

            if [ -n "$RESUME_FILE" ]; then
                RESULT=$(call_backend "cover_letter.py" "$COMPANY" "$ROLE" "$NAME" "$RESUME_FILE")
            else
                RESULT=$(call_backend "cover_letter.py" "$COMPANY" "$ROLE" "$NAME")
            fi

            SUCCESS=$(echo "$RESULT" | jq -r '.success')

            if [ "$SUCCESS" != "true" ]; then
                ERROR=$(echo "$RESULT" | jq -r '.error')
                gum style --foreground "$ERROR_COLOR" "Error: $ERROR"
                gum confirm "Return to menu?" && continue || break
            fi

            echo ""
            gum style --foreground "$SUCCESS_COLOR" "$(printf '\342\234\205') Cover letter generated!"
            echo ""

            # Display cover letter with yellow/orange border matching mockup
            COVER_LETTER=$(echo "$RESULT" | jq -r '.cover_letter')
            gum style --border normal --border-foreground "220" --padding "1 2" \
                "$COVER_LETTER"

            USED_RESUME=$(echo "$RESULT" | jq -r '.used_resume')
            if [ "$USED_RESUME" = "true" ]; then
                echo ""
                gum style --foreground "$SUCCESS_COLOR" --italic "Personalized using your resume"
            fi

            echo ""
            gum confirm "Save cover letter to file?" && {
                OUTFILE="cover_letter_${COMPANY// /_}_$(date +%Y%m%d).txt"
                echo "$COVER_LETTER" > "$OUTFILE"
                gum style --foreground "$SUCCESS_COLOR" "Saved to: $OUTFILE"
            }

            gum confirm "Return to menu?" && continue || break
            ;;

        "Interview Prep Questions")
            clear
            gum style --foreground "$ACCENT_COLOR" --border normal --padding "1 2" \
                "$(printf '\360\237\222\254') INTERVIEW PREP" "Practice with AI-generated questions"
            echo ""

            # Category descriptions to help user choose
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

            # Map selection to backend category
            case "$TYPE" in
                "Behavioral") CATEGORY="behavioral" ;;
                "Technical") CATEGORY="technical" ;;
                "System Design") CATEGORY="system_design" ;;
                "Culture Fit") CATEGORY="culture_fit" ;;
            esac

            echo ""
            gum spin --spinner dot --title "Generating relevant questions..." -- sleep 0.5

            RESULT=$(call_backend "interview_prep.py" "$CATEGORY" 4)

            SUCCESS=$(echo "$RESULT" | jq -r '.success')

            if [ "$SUCCESS" != "true" ]; then
                ERROR=$(echo "$RESULT" | jq -r '.error')
                gum style --foreground "$ERROR_COLOR" "Error: $ERROR"
                gum confirm "Return to menu?" && continue || break
            fi

            echo ""

            # Build questions display
            QUESTIONS_TEXT=""
            while IFS= read -r q; do
                NUM=$(echo "$q" | jq -r '.number')
                QUESTION=$(echo "$q" | jq -r '.question')
                QUESTIONS_TEXT="$QUESTIONS_TEXT
$NUM. $QUESTION"
            done < <(echo "$RESULT" | jq -c '.questions[]')

            # Get general tip
            GENERAL_TIP=$(echo "$RESULT" | jq -r '.general_tip')

            # Display in styled box matching mockup
            gum style --border normal --border-foreground "255" --padding "1 2" \
                "$(printf '\360\237\223\213') ${TYPE^^} INTERVIEW QUESTIONS:" \
                "$QUESTIONS_TEXT" \
                "" \
                "$(printf '\360\237\222\241') TIP: $GENERAL_TIP"

            echo ""
            gum confirm "Get different questions?" && {
                RESULT=$(call_backend "interview_prep.py" "$CATEGORY" 4)

                # Rebuild questions display
                QUESTIONS_TEXT=""
                while IFS= read -r q; do
                    NUM=$(echo "$q" | jq -r '.number')
                    QUESTION=$(echo "$q" | jq -r '.question')
                    QUESTIONS_TEXT="$QUESTIONS_TEXT
$NUM. $QUESTION"
                done < <(echo "$RESULT" | jq -c '.questions[]')

                GENERAL_TIP=$(echo "$RESULT" | jq -r '.general_tip')

                echo ""
                gum style --border normal --border-foreground "255" --padding "1 2" \
                    "$(printf '\360\237\223\213') ${TYPE^^} INTERVIEW QUESTIONS:" \
                    "$QUESTIONS_TEXT" \
                    "" \
                    "$(printf '\360\237\222\241') TIP: $GENERAL_TIP"
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
                CODE_FILE=$(gum file ~ --height 12 --file)

                if [ -z "$CODE_FILE" ]; then
                    gum style --foreground "$ERROR_COLOR" "No file selected."
                    sleep 1
                    continue 2
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

            RESULT=$(call_backend "code_analyzer.py" "$CODE_FILE")

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
