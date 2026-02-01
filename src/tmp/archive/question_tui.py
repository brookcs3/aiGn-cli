#!/usr/bin/env python3
"""
Interactive Question TUI - Stage C
Uses gum for beautiful prompts
"""
import json
import sys
import subprocess


def ask_question_with_gum(question):
    """Ask a single question using gum"""
    answers = {}
    
    # Display question
    subprocess.run([
        "gum", "style",
        "--foreground", "212",
        "--bold",
        f"❓ {question['question_text']}"
    ])
    
    if 'skill' in question:
        subprocess.run([
            "gum", "style",
            "--foreground", "240",
            f"   Skill: {question['skill']}"
        ])
    
    print()
    
    # Collect answer fields
    for field in question.get('answer_fields', []):
        field_key = field['field_key']
        field_label = field.get('field_label', field_key)
        expected_format = field.get('expected_format', 'short_text')
        
        if expected_format == 'boolean':
            result = subprocess.run(
                ["gum", "confirm", f"{field_label}?"],
                capture_output=True
            )
            answers[field_key] = result.returncode == 0
            
        elif expected_format in ['bullet_list', 'tool_list', 'metric_list', 'link_list']:
            print(f"{field_label} (comma-separated):")
            result = subprocess.run(
                ["gum", "input", "--placeholder", f"Enter {field_label.lower()}..."],
                capture_output=True,
                text=True
            )
            items = [x.strip() for x in result.stdout.strip().split(',') if x.strip()]
            answers[field_key] = items
            
        elif expected_format == 'long_text':
            print(f"{field_label}:")
            result = subprocess.run(
                ["gum", "write", "--placeholder", f"Enter {field_label.lower()}..."],
                capture_output=True,
                text=True
            )
            answers[field_key] = result.stdout.strip()
            
        else:  # short_text
            print(f"{field_label}:")
            result = subprocess.run(
                ["gum", "input", "--placeholder", f"Enter {field_label.lower()}..."],
                capture_output=True,
                text=True
            )
            answers[field_key] = result.stdout.strip()
    
    return answers


def main():
    """Load questions and run gum prompts"""
    if len(sys.argv) < 2:
        print("Usage: python question_tui.py <analysis.json>")
        sys.exit(1)
    
    # Load analysis file
    with open(sys.argv[1], 'r') as f:
        analysis = json.load(f)
    
    # Extract question_bank
    if 'analysis' in analysis:
        question_bank = analysis['analysis']['question_bank']
    else:
        question_bank = analysis.get('question_bank', {})
    
    all_questions = []
    all_questions.extend(question_bank.get('skill_questions', []))
    all_questions.extend(question_bank.get('category_questions', []))
    
    # Show total
    subprocess.run([
        "gum", "style",
        "--foreground", "212",
        "--border", "rounded",
        "--padding", "1",
        f"📝 {len(all_questions)} Questions Ready"
    ])
    
    # Collect all answers
    output = {'categories': []}
    
    for i, q in enumerate(all_questions):
        # Progress
        subprocess.run([
            "gum", "style",
            "--foreground", "240",
            f"Question {i+1} of {len(all_questions)}"
        ])
        print()
        
        # Ask question
        answer_data = ask_question_with_gum(q)
        
        # Group by category
        group_id = q.get('group_id', q.get('category_id', 'general'))
        category = next((c for c in output['categories'] if c['category_id'] == group_id), None)
        
        if not category:
            category = {
                'category_id': group_id,
                'category_label': group_id.replace('_', ' ').title(),
                'priority': 'must_have',
                'questions': []
            }
            output['categories'].append(category)
        
        category['questions'].append({
            'question_id': q['question_id'],
            'question_text': q['question_text'],
            'answer': json.dumps(answer_data),
            'resume_mapping_hint': 'project_bullets'
        })
        
        print()
    
    # Save answers
    with open('user_answers.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    # Success message
    subprocess.run([
        "gum", "style",
        "--foreground", "212",
        "--bold",
        f"✅ Saved {len(all_questions)} answers to user_answers.json"
    ])


if __name__ == "__main__":
    main()
