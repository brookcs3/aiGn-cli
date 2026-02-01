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
    """Load jobs from CSV"""
    if not os.path.exists("jobs.csv"):
        print("❌ No jobs.csv found. Run job_hunter.py first!")
        sys.exit(1)
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
        # Pipe: cat temp_file | python AICHAT.py --chat
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
    
    # Load prompt template
    with open("A-PRopt.txt", 'r') as f:
        prompt_template = f.read()
    
    # Build prompt
    full_prompt = f"""{prompt_template}

Job Posting:
{job_description}

Please analyze and output JSON only."""
    
    # Call AICHAT.py
    response_text = call_aichat(full_prompt)
    
    # Debug: save raw response
    with open("debug_ai_response.txt", 'w') as f:
        f.write(response_text)
    print(f"💾 Debug: saved AI response to debug_ai_response.txt ({len(response_text)} chars)")
    
    # Try to extract JSON - look for question_bank specifically
    try:
        import re
        
        # Look for question_bank in the response
        qb_match = re.search(r'"question_bank"\s*:\s*\{', response_text)
        
        if qb_match:
            # Found question_bank, extract from there
            start = response_text.find('{', qb_match.start())
            
            # Find matching closing brace
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
            # Fallback: try to parse whole thing
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
    """Simple text-based Q&A - collect answers"""
    print("\n📝 Answer these questions about your experience:\n")
    
    answers = {'categories': []}
    question_bank = analysis['analysis']['question_bank']
    
    # Ask skill questions
    for sq in question_bank['skill_questions']:
        print(f"\n❓ {sq['question_text']}")
        print(f"   (Skill: {sq['skill']})")
        
        answer = input("   Your answer: ").strip()
        
        # Find or create category
        group_id = sq['group_id']
        category = next((c for c in answers['categories'] if c['category_id'] == group_id), None)
        
        if not category:
            category = {
                'category_id': group_id,
                'category_label': group_id.replace('_', ' ').title(),
                'priority': 'must_have',
                'questions': []
            }
            answers['categories'].append(category)
        
        category['questions'].append({
            'question_id': sq['question_id'],
            'question_text': sq['question_text'],
            'answer': answer,
            'resume_mapping_hint': 'project_bullets'
        })
    
    # Ask category questions
    print("\n\n━━━ Broader Questions ━━━\n")
    for cq in question_bank['category_questions']:
        print(f"\n❓ {cq['question_text']}")
        answer = input("   Your answer: ").strip()
        
        category_id = cq['category_id']
        category = next((c for c in answers['categories'] if c['category_id'] == category_id), None)
        
        if not category:
            category = {
                'category_id': category_id,
                'category_label': category_id.replace('_', ' ').title(),
                'priority': 'strong_signal',
                'questions': []
            }
            answers['categories'].append(category)
        
        category['questions'].append({
            'question_id': cq['question_id'],
            'question_text': cq['question_text'],
            'answer': answer,
            'resume_mapping_hint': 'summary'
        })
    
    return answers


def call_ai_generate_resume(job_description, user_answers):
    """Second AI call: generate resume + cover letter with SchINte.txt"""
    print("\n\n🤖 Step 2: Generating resume and cover letter...\n")
    
    # Load prompt template
    with open("SchINte.txt", 'r') as f:
        prompt_template = f.read()
    
    # Build payload
    payload = {
        "variable_name": {
            "{{job_post_text}}": job_description,
            "{{builder_guide}}": "Build from scratch. Do not invent facts. Use ONLY answers.",
            "{{output_mode}}": "resume_and_cover_letter",
            "responses": user_answers
        }
    }
    
    full_prompt = f"""{prompt_template}

Input Data:
{json.dumps(payload, indent=2)}

Generate JSON output only."""
    
    # Call AICHAT.py
    response_text = call_aichat(full_prompt)
    
    # Extract JSON
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
    company = job_info['company'].replace(' ', '_').replace('/', '_')
    title = result['analysis']['inferred_target_role'].replace(' ', '_').replace('/', '_')
    
    folder = f"applications/{company}_{title}"
    os.makedirs(folder, exist_ok=True)
    
    # Save resume
    resume_path = f"{folder}/resume.txt"
    with open(resume_path, 'w') as f:
        f.write(result['deliverable']['resume_text'])
    
    # Save cover letter
    cover_letter_path = f"{folder}/cover_letter.txt"
    with open(cover_letter_path, 'w') as f:
        f.write(result['deliverable']['cover_letter_text'])
    
    # Save JSON
    json_path = f"{folder}/data.json"
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Saved to {folder}/")
    print(f"   - resume.txt")
    print(f"   - cover_letter.txt")
    print(f"   - data.json")
    
    # Display resume
    print("\n" + "="*60)
    print("📄 RESUME")
    print("="*60)
    print(result['deliverable']['resume_text'])
    print("\n" + "="*60)
    print("✉️  COVER LETTER")
    print("="*60)
    print(result['deliverable']['cover_letter_text'])
    print("="*60 + "\n")


def main():
    """Main pipeline"""
    try:
        # Step 1: Load and select job
        jobs_df = load_jobs()
        display_jobs(jobs_df)
        selected_job = select_job(jobs_df)
        
        print(f"\n✅ Selected: {selected_job['title']} at {selected_job['company']}\n")
        
        # Check if description exists
        if pd.isna(selected_job['description']) or not selected_job['description']:
            print("❌ No job description available for this posting")
            sys.exit(1)
        
        job_description = selected_job['description']
        
        # Step 2: AI analyzes job → generates questions
        analysis = call_ai_analyze_job(job_description)
        
        print(f"\n✅ Analysis complete!")
        
        # Check structure and extract question_bank
        if 'analysis' in analysis:
            question_bank = analysis['analysis']['question_bank']
        else:
            question_bank = analysis.get('question_bank', {})
        
        print(f"   - Generated {len(question_bank.get('skill_questions', []))} skill questions")
        print(f"   - Generated {len(question_bank.get('category_questions', []))} category questions")
        
        # Ask if user wants to save analysis
        if ask_yes_no("Save this analysis to a file?"):
            with open("last_analysis.json", 'w') as f:
                json.dump(analysis, f, indent=2)
            print("💾 Saved analysis to last_analysis.json")
        
        # Ask if user wants to continue or return to menu
        if not ask_yes_no("Continue to questions?"):
            print("\n👋 Returning to menu...")
            main()  # Restart from beginning
            return
        
        # Step 4: User answers questions via TUI
        print("\n🚀 Launching interactive Q&A...\n")
        
        # Launch question_tui.py with direct stdin access
        subprocess.run([
            "python", "question_tui.py", "last_analysis.json"
        ], stdin=sys.stdin)
        
        # Load answers from TUI
        if not os.path.exists("user_answers.json"):
            print("❌ No answers file created. Exiting.")
            sys.exit(1)
        
        with open("user_answers.json", 'r') as f:
            user_answers = json.load(f)
        
        # Save answers
        with open("last_answers.json", 'w') as f:
            json.dump(user_answers, f, indent=2)
        print("\n💾 Saved answers to last_answers.json")
        
        # Step 5: AI generates resume + cover letter
        result = call_ai_generate_resume(job_description, user_answers)
        
        # Step 6: Save and display
        save_output(result, selected_job)
        
        print("\n🎉 Done! Your application is ready.")
        
        # Ask if user wants to apply to another job
        if ask_yes_no("Apply to another job?"):
            print("\n" + "="*60 + "\n")
            main()  # Restart
            return
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
