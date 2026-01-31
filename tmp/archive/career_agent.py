import os
import sys
import json
import time
import subprocess
import requests
import pandas as pd
from jobspy import scrape_jobs
from prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_SCHEMA, RESUME_SYSTEM_PROMPT, RESUME_SCHEMA

# --- Configuration ---
LOCAL_LLM_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "gpt-4o" # or whatever the local model is called, e.g., "hugging-quants/Meta-Llama-3..."

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def gum_input(placeholder, header=""):
    """Wrapper for gum input"""
    cmd = ["gum", "input", "--placeholder", placeholder]
    if header:
        cmd_write = subprocess.Popen(["gum", "style", "--foreground", "212", header], stdout=subprocess.PIPE)
        header_out, _ = cmd_write.communicate()
        print(header_out.decode().strip())
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def gum_write(content, width=80):
    """Wrapper for gum write (text area)"""
    cmd = ["gum", "write", "--width", str(width), "--placeholder", "Type your answer here... (Ctrl+D to save)"]
    if content:
        # Pre-fill content if needed, though gum write is usually for new input
        pass
    result = subprocess.run(cmd, input=content, capture_output=True, text=True)
    return result.stdout.strip()

def gum_choose(options, header="Select an option:"):
    """Wrapper for gum choose"""
    # options should be a list of strings
    cmd = ["gum", "choose", "--header", header] + options
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def call_ai(system_prompt, user_prompt, schema):
    """
    Tries to call a local LLM. If fails, dumps to file and asks user.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"} 
    }
    
    print("\n🤖 Consulting the AI...")
    try:
        response = requests.post(LOCAL_LLM_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        return json.loads(content)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Fallback to manual
        print("\n⚠️  Local LLM not found (or timed out). Switching to Manual Mode.")
        return manual_ai_step(system_prompt, user_prompt, schema)
    except Exception as e:
        print(f"\n❌ Error calling LLM: {e}")
        return manual_ai_step(system_prompt, user_prompt, schema)

def manual_ai_step(system_prompt, user_prompt, schema):
    """
    Dumps prompts to files and waits for JSON paste.
    """
    timestamp = int(time.time())
    prompt_file = f"prompt_{timestamp}.txt"
    json_file = f"response_{timestamp}.json"
    
    full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}\n\nOUTPUT SCHEMA:\n{schema}"
    
    with open(prompt_file, "w") as f:
        f.write(full_prompt)
        
    subprocess.run(["gum", "style", "--border", "double", "--margin", "1", "--padding", "1", 
                    f"Action Required: Copy prompt from {prompt_file}, paste into your AI, and save the JSON output to {json_file}."])
    
    input(f"Press Enter once you have saved {json_file}...")
    
    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        return None

def main():
    clear_screen()
    subprocess.run(["gum", "style", "--foreground", "212", "--border", "double", "--align", "center", "--width", "50", "🦄 CAREER AGENT v1.0 🦄"])

    # 1. Scrape Jobs
    term = gum_input("Job Title (e.g. 'Software Engineer')", "🔍 What role are you looking for?")
    location = gum_input("Location (e.g. 'Remote', 'SF')", "🌍 Where?")
    
    print("\n🚀 Scraping jobs...")
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=term,
            location=location,
            results_wanted=5,
            country_nameof='USA',
            linkedin_fetch_description=True
        )
    except Exception as e:
        print(f"Error scraping: {e}")
        return

    if jobs.empty:
        print("No jobs found.")
        return

    # 2. Select Job
    options = []
    # Create valid indices map
    job_map = {}
    
    for idx, row in jobs.iterrows():
        title = row.get('title', 'Unknown')
        company = row.get('company', 'Unknown')
        
        # We need a string for gum choose
        label = f"{title} @ {company}"
        # Ensure unique labels if duplicate titles
        if label in options:
            label = f"{label} ({idx})"
            
        options.append(label)
        job_map[label] = row

    choice = gum_choose(options, header="Pick a job to apply for:")
    if not choice:
        return

    selected_job = job_map[choice]
    job_description = selected_job.get('description', '')
    if not job_description:
         print("⚠️ No description found for this job. Trying to fetch URL...")
         # Fallback logic if needed, but for now just warn
    
    # 3. Analyze Job (Step 1)
    print("\n🧠 Analyzing job description...")
    
    # Fill schema/variables
    user_prompt_1 = json.dumps({"variable_name": {"{{job_post_text}}": job_description}})
    
    analysis_result = call_ai(ANALYSIS_SYSTEM_PROMPT, user_prompt_1, ANALYSIS_SCHEMA)
    
    if not analysis_result:
        print("Analysis failed.")
        return

    # Extract Question Bank
    # Handle potentially nested structure depending on how strict the AI followed schema
    # The schema puts 'analysis' at the top level, and inside that 'question_bank'
    try:
        analysis_data = analysis_result.get('analysis', analysis_result) # Fallback if AI returned inner object directly
        question_bank = analysis_data.get('question_bank', {})
        skill_qs = question_bank.get('skill_questions', [])
        cat_qs = question_bank.get('category_questions', [])
    except Exception as e:
        print(f"Error parsing analysis JSON: {e}")
        return

    # 4. Conduct Interview
    user_responses = {
        "categories": [] # We will restructure this to match Prompt 2 schema requirement if needed
    }
    
    # We need to build a structure that Prompt 2 can consume.
    # The Prompt 2 input schema expects `responses.categories[].questions[].answer`
    # This implies we need to map the flat lists back to categories.
    
    # Let's collect answers first
    category_answers_map = {} # category_id -> list of populated questions
    
    total_qs = len(skill_qs) + len(cat_qs)
    print(f"\n🎤 Starting Interview ({total_qs} questions)...")
    
    # Ask Skill Questions
    for q in skill_qs:
        q_text = q['question_text']
        skill = q['skill']
        print(f"\n🔹 Skill: {skill}")
        # Use gum write for longer answers
        print(f"❓ {q_text}")
        answer = gum_write("", width=60)
        
        # Store answer. For Prompt 2, skills might need to be mapped to categories
        # or we just assume the Prompt 2 schema provided ("responses.categories...") covers everything.
        # Actually Prompt 2 schema seems to focus on 'categories'.
        # We'll just dump EVERYTHING into a "responses" object that the AI can read.
        q['answer'] = answer
        
    # Ask Category Questions
    for q in cat_qs:
        q_text = q['question_text']
        cat_id = q['category_id']
        print(f"\n🔸 Category: {cat_id}")
        print(f"❓ {q_text}")
        answer = gum_write("", width=60)
        q['answer'] = answer
        
        if cat_id not in category_answers_map:
             category_answers_map[cat_id] = []
        category_answers_map[cat_id].append(q)

    # Construct Responses Object for Prompt 2
    # We need to format specific to the "responses" schema expected by Prompt 2
    # schema: responses -> categories -> [ {category_id, ..., questions: [ {answer...} ] } ]
    
    final_responses_obj = {
        "categories": []
    }
    
    for cat_id, questions in category_answers_map.items():
        cat_obj = {
            "category_id": cat_id,
            "questions": questions # These now have 'answer' field
        }
        final_responses_obj["categories"].append(cat_obj)

    # 5. Generate Resume (Step 2)
    print("\n📝 Generating Resume & Cover Letter...")
    
    prompt_2_inputs = {
        "variable_name": {
            "{{job_post_text}}": job_description,
            "{{builder_guide}}": "Standard Builder Guide",
            "{{output_mode}}": "resume_and_cover_letter",
            "responses": final_responses_obj,
             # Pass the full analysis too so it has context on skills? 
             # The Prompt 2 schema provided showed 'responses' having the analysis inside it in the example?
             # Actually the example showed "responses": { "analysis": ... }.
             # So let's include the full analysis in responses.
            "analysis": analysis_data 
        }
    }
    
    resume_result = call_ai(RESUME_SYSTEM_PROMPT, json.dumps(prompt_2_inputs), RESUME_SCHEMA)
    
    if not resume_result:
        print("Resume generation failed.")
        return

    # 6. Render Result
    try:
        deliverable = resume_result.get('deliverable', resume_result) # fallback
        resume_text = deliverable.get('resume_text', '')
        cover_letter = deliverable.get('cover_letter_text', '')
        
        final_md = f"# 📄 RESUME\n\n{resume_text}\n\n---\n\n# ✉️ COVER LETTER\n\n{cover_letter}"
        
        with open("final_application.md", "w") as f:
            f.write(final_md)
            
        print("\n✨ Done! Opening in Glow...")
        time.sleep(1)
        subprocess.run(["glow", "final_application.md"])
        
    except Exception as e:
        print(f"Error rendering result: {e}")
        print("Raw result saved to final_application.json")
        with open("final_application.json", "w") as f:
            json.dump(resume_result, f, indent=2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
