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
    """Load jobs from CSV, always run job_hunter for fresh jobs"""
    if os.path.exists("jobs.csv"):
        os.remove("jobs.csv")
        print("🗑️  Deleted old jobs.csv")
    
    print("📡 Running job_hunter.py for fresh jobs...\n")
    result = subprocess.run(
        ["python", "job_hunter.py"],
        capture_output=False,
        text=True
    )
    if result.returncode != 0:
        print("❌ job_hunter.py failed")
        sys.exit(1)
    if not os.path.exists("jobs.csv"):
        print("❌ job_hunter.py ran but jobs.csv still not found")
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


def call_aichat(prompt):
    """Call AICHAT.py via pipe"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        temp_file = f.name

    try:
        cmd = f"cat {temp_file} | python AICHAT.py --chat"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            print(f"❌ AICHAT.py error: {result.stderr}")
            sys.exit(1)

        return result.stdout.strip()
    finally:
        os.unlink(temp_file)


def call_ai_analyze_job(job_description):
    """First AI call: analyze job posting with A-PRopt.txt"""
    print("🤖 Step 1: Analyzing job posting...\n")
    with open("A-PRopt.txt", 'r') as f:
        prompt_template = f.read()

    full_prompt = f"""{prompt_template}

Job Posting:
{job_description}

Please analyze and output JSON only."""

    response_text = call_aichat(full_prompt)

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/debug_ai_response.txt", 'w') as f:
        f.write(response_text)
    print(f"💾 Debug: saved AI response to tmp/debug_ai_response.txt ({len(response_text)} chars)")

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


def build_filled_template_d(job_description, analysis_filled):
    """Fill JSONQ_TEMP.txt with values and save"""
    with open("JSONQ_TEMP.txt", 'r') as f:
        template = f.read()

    analysis_one_line = json.dumps(analysis_filled, separators=(',', ':'))
    job_desc_escaped = job_description.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    template = template.replace('{{JOB_POSTING}}', job_desc_escaped)
    template = template.replace('{{QUESTIONS_FILLED}}', analysis_one_line)

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/filled_prompt.txt", 'w') as f:
        f.write(template)

    return template


def call_ai_generate_resume(job_description, analysis_filled):
    """Second AI call: generate resume + cover letter"""
    print("\n\n🤖 Step 2: Generating resume and cover letter...\n")
    filled_prompt = build_filled_template_d(job_description, analysis_filled)
    response_text = call_aichat(filled_prompt)

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/debug_resume_response.txt", 'w') as f:
        f.write(response_text)
    print(f"💾 Debug: saved AI response to tmp/debug_resume_response.txt ({len(response_text)} chars)")

    try:
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


def save_output(result, job_info):
    """Save resume and cover letter to files"""
    analysis = result.get('analysis', result)
    deliverable = result.get('deliverable', result)

    company = str(job_info.get('company', 'Unknown') or 'Unknown').replace(' ', '_').replace('/', '_')
    title_raw = analysis.get('inferred_target_role') or job_info.get('title') or 'Unknown'
    title = str(title_raw).replace(' ', '_').replace('/', '_')

    folder = f"applications/{company}_{title}"
    os.makedirs(folder, exist_ok=True)

    resume_text = deliverable.get('resume_text', '')
    cover_letter_text = deliverable.get('cover_letter_text', '')

    with open(f"{folder}/resume.txt", 'w') as f:
        f.write(resume_text)
    with open(f"{folder}/cover_letter.txt", 'w') as f:
        f.write(cover_letter_text)
    with open(f"{folder}/data.json", 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Saved to {folder}/")
    print("   - resume.txt")
    print("   - cover_letter.txt")
    print("   - data.json")

    if resume_text:
        print("\n" + "="*60)
        print("📄 RESUME")
        print("="*60)
        print(resume_text)
    if cover_letter_text:
        print("\n" + "="*60)
        print("✉️  COVER LETTER")
        print("="*60)
        print(cover_letter_text)
    if resume_text or cover_letter_text:
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

        with open("last_answers_lookup.json", 'w') as f:
            json.dump(answers_lookup, f, indent=2)

        analysis_str = json.dumps(analysis_filled)
        analysis_str = '\n'.join(line for line in analysis_str.split('\n') if line.strip())
        analysis_str = analysis_str.replace('\n', '')
        with open("last_analysis_filled.json", 'w') as f:
            f.write(analysis_str)
        print("💾 Saved filled analysis to last_analysis_filled.json")

        result = call_ai_generate_resume(job_description, analysis_filled)
        save_output(result, selected_job)

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