#!/usr/bin/env python3
"""
Apply to Job - Interactive Pipeline
Uses your AICHAT.py via pipe
"""
import os
import sys
import json
import subprocess
import pandas as pd


def load_jobs():
    """Load jobs from CSV, always run scraper for fresh jobs"""
    if os.path.exists("jobs.csv"):
        os.remove("jobs.csv")
        print("🗑️  Deleted old jobs.csv")

    print("📡 Running job_scraper.py for fresh jobs...\n")
    # Assuming running from root
    scraper_path = "jobs/job_scraper.py" if os.path.exists("jobs/job_scraper.py") else "job_scraper.py"

    result = subprocess.run(
        [sys.executable, scraper_path],
        capture_output=False,
        text=True
    )
    if result.returncode != 0:
        print("❌ job_scraper.py failed")
        sys.exit(1)
    if not os.path.exists("jobs.csv"):
        print("❌ job_scraper.py ran but jobs.csv still not found")
        sys.exit(1)
    print("\n✅ Fresh jobs loaded!\n")
    return pd.read_csv("jobs.csv")


def display_jobs(df):
    """Display jobs in simple list"""
    print("\n📋 Available Jobs:\n")
    for idx, row in df.iterrows():
        print(f"{idx + 1}. {row['company']} - {row['title']} ({row['location']})")
    print()


def select_job(df):
    """Let user select a job by number"""
    while True:
        try:
            choice = int(input("Select job number (or 0 to quit): "))
            if choice == 0:
                sys.exit(0)
            if 1 <= choice <= len(df):
                return df.iloc[choice - 1]
            print(f"Please enter a number between 1 and {len(df)}")
        except ValueError:
            print("Please enter a valid number")


def call_llm_inference(prompt):
    """Call llm_inference.py via pipe"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        temp_file = f.name

    try:
        # Assuming running from root
        llm_path = "core/llm_inference.py" if os.path.exists("core/llm_inference.py") else "llm_inference.py"

        # Use sys.executable for robustness
        cmd = f"cat {temp_file} | {sys.executable} {llm_path} --chat"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            print(f"❌ llm_inference.py error: {result.stderr}")
            sys.exit(1)

        return result.stdout.strip()
    finally:
        os.unlink(temp_file)


def call_ai_analyze_job(job_description):
    """First AI call: analyze job posting with prompt_job_analysis.txt"""
    print("🤖 Step 1: Analyzing job posting...\n")

    prompt_path = "prompts/prompt_job_analysis.txt" if os.path.exists("prompts/prompt_job_analysis.txt") else "prompt_job_analysis.txt"
    with open(prompt_path, 'r') as f:
        prompt_template = f.read()

    full_prompt = f"""{prompt_template}

Job Posting:
{job_description}

Please analyze and output JSON only."""

    response_text = call_llm_inference(full_prompt)

    with open("debug_ai_response.txt", 'w') as f:
        f.write(response_text)
    print(f"💾 Debug: saved AI response to debug_ai_response.txt ({len(response_text)} chars)")

    try:
        import re
        qb_match = re.search(r'"question_bank"\s*:\s*\{', response_text)

        if qb_match:
            start = response_text.find('{', qb_match.start())
            brace_count = 1
            pos = start + 1
            while pos < len(response_text) and brace_count > 0:
                if response_text[pos] == '{':
                    brace_count += 1
                elif response_text[pos] == '}':
                    brace_count -= 1
                pos += 1

            qb_json = response_text[start:pos]
            question_bank = json.loads(qb_json)
            return {
                'analysis': {
                    'question_bank': question_bank,
                    'role_title': 'Unknown',
                    'company_name': 'Unknown'
                }
            }
        else:
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "{" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]
            else:
                json_str = response_text

            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse AI response as JSON: {e}")
        print(f"Raw response:\n{response_text}")
        sys.exit(1)


def ask_yes_no(question):
    """Ask a yes/no question with nice formatting"""
    print(f"\n{question}")
    print("\n    Yes        No\n")
    while True:
        answer = input(">>> ").strip().lower()
        if answer in ['yes', 'y', '1']:
            return True
        elif answer in ['no', 'n', '0']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def ask_questions_simple(analysis):
    """Simple text-based Q&A - collect answers in flat lookup format"""
    print("\n📝 Answer these questions about your experience:\n")
    answers_lookup = {}
    question_bank = analysis['analysis']['question_bank']

    for sq in question_bank['skill_questions']:
        print(f"\n❓ {sq['question_text']}")
        print(f"   (Skill: {sq['skill']})")
        answer = input("   Your answer: ").strip()
        answers_lookup[sq['question_id']] = answer

    print("\n\n━━━ Broader Questions ━━━\n")
    for cq in question_bank['category_questions']:
        print(f"\n❓ {cq['question_text']}")
        answer = input("   Your answer: ").strip()
        answers_lookup[cq['question_id']] = answer

    return answers_lookup


def build_analysis_with_answers(original_analysis, answers_lookup):
    """Take the original analysis structure and fill in answers"""
    import copy
    analysis_filled = copy.deepcopy(original_analysis)
    question_bank = analysis_filled.get('analysis', {}).get('question_bank', {})

    for sq in question_bank.get('skill_questions', []):
        qid = sq.get('question_id')
        if qid in answers_lookup:
            for field in sq.get('answer_fields', []):
                if 'expected_format' in field:
                    field['format'] = answers_lookup[qid]
                    del field['expected_format']

    for cq in question_bank.get('category_questions', []):
        qid = cq.get('question_id')
        if qid in answers_lookup:
            for field in cq.get('answer_fields', []):
                if 'expected_format' in field:
                    field['format'] = answers_lookup[qid]
                    del field['expected_format']

    return analysis_filled


def build_filled_template_d(job_description):
    """Copy template to filled_prompt.txt, then fill in placeholders directly"""
    import shutil
    import filecmp

    prompt_path = "prompts/prompt_resume_generator.txt" if os.path.exists("prompts/prompt_resume_generator.txt") else "prompt_resume_generator.txt"

    # Step 1: Fresh copy of template
    print("📋 Copying template to filled_prompt.txt...")
    shutil.copy(prompt_path, "filled_prompt.txt")

    # Step 2: Verify copy matches original
    if filecmp.cmp(prompt_path, "filled_prompt.txt", shallow=False):
        print("✅ Copy verified - templates match")
    else:
        print("❌ Copy failed - files don't match!")
        sys.exit(1)

    # Step 3: Read the copy
    with open("filled_prompt.txt", 'r') as f:
        content = f.read()

    # Step 4: Get questions data from debug_ai_response.txt
    with open("debug_ai_response.txt", 'r') as f:
        questions_filled = f.read()

    # Step 5: Replace placeholders
    content = content.replace('{{JOB_POSTING}}', job_description)
    content = content.replace('{{QUESTIONS_FILLED}}', questions_filled)

    # Step 6: Write back to filled_prompt.txt
    with open("filled_prompt.txt", 'w') as f:
        f.write(content)

    print("✅ filled_prompt.txt ready")
    return content


def call_ai_generate_resume(job_description):
    """Second AI call: generate resume + cover letter"""
    print("\n\n🤖 Step 2: Generating analysis...\n")
    filled_prompt = build_filled_template_d(job_description)
    response_text = call_llm_inference(filled_prompt)

    with open("debug_resume_response.txt", 'w') as f:
        f.write(response_text)
    print(f"💾 Debug: saved AI response to debug_resume_response.txt ({len(response_text)} chars)")

    return response_text


def format_cover_letter_with_script(analysis_json):
    """Third step: format cover letter using Python script"""
    print("\n\n📝 Step 3: Formatting cover letter with Python script...\n")

    # Save analysis to temp file
    with open("temp_analysis.json", 'w') as f:
        f.write(analysis_json)

    # Call json_to_cover_letter.py
    script_path = "utils/json_to_cover_letter.py" if os.path.exists("utils/json_to_cover_letter.py") else "json_to_cover_letter.py"

    result = subprocess.run(
        [sys.executable, script_path, "temp_analysis.json"],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )

    if result.returncode != 0:
        print(f"❌ json_to_cover_letter.py failed: {result.stderr}")
        sys.exit(1)

    cover_letter = result.stdout.strip()

    # Clean up temp file
    os.remove("temp_analysis.json")

    print(f"✅ Cover letter formatted ({len(cover_letter)} chars)")
    return cover_letter


def save_output(cover_letter_text, job_info):
    """Save cover letter to file"""
    company = str(job_info.get('company', 'Unknown') or 'Unknown').replace(' ', '_').replace('/', '_')
    title = str(job_info.get('title', 'Unknown') or 'Unknown').replace(' ', '_').replace('/', '_')

    folder = f"applications/{company}_{title}"
    os.makedirs(folder, exist_ok=True)

    # Save cover letter as markdown
    with open(f"{folder}/cover_letter.md", 'w') as f:
        f.write(cover_letter_text)

    print(f"\n✅ Saved to {folder}/cover_letter.md")
    print("\n" + "="*60)
    print("✉️  COVER LETTER")
    print("="*60)
    print(cover_letter_text)
    print("="*60 + "\n")


def main():
    """Main pipeline"""
    try:
        jobs_df = load_jobs()
        display_jobs(jobs_df)
        selected_job = select_job(jobs_df)

        print(f"\n✅ Selected: {selected_job['title']} at {selected_job['company']}\n")

        if pd.isna(selected_job['description']) or not selected_job['description']:
            print("❌ No job description available for this posting")
            sys.exit(1)

        job_description = selected_job['description']
        analysis = call_ai_analyze_job(job_description)

        print(f"\n✅ Analysis complete!")
        question_bank = analysis.get('analysis', {}).get('question_bank', {})

        print(f"   - Generated {len(question_bank.get('skill_questions', []))} skill questions")
        print(f"   - Generated {len(question_bank.get('category_questions', []))} category questions")

        if not ask_yes_no("Continue to questions?"):
            print("\n👋 Returning to menu...")
            main()
            return

        print("\n🚀 Starting Q&A...\n")
        answers_lookup = ask_questions_simple(analysis)

        print("\n🔧 Building filled analysis...")
        analysis_filled = build_analysis_with_answers(analysis, answers_lookup)

        # Step 2: Generate analysis JSON
        analysis_json = call_ai_generate_resume(job_description)

        # Step 3: Format as cover letter with Python script
        cover_letter = format_cover_letter_with_script(analysis_json)

        # Save cover letter
        save_output(cover_letter, selected_job)

        print("\n🎉 Done! Your application is ready.")
        if ask_yes_no("Apply to another job?"):
            print("\n" + "="*60 + "\n")
            main()
        else:
            print("\n👋 Good luck with your applications!")

    except KeyboardInterrupt:
        print("\n\n👋 Cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
