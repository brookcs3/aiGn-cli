#!/usr/bin/env python3
"""
json_to_cover_letter.py - Parse structured JSON and output formatted cover letter
"""
import json
import re
import sys
import argparse
from datetime import datetime

def strip_code_blocks(content):
    """Remove markdown code block wrappers"""
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    elif content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    return content.strip()


def parse_cover_letter_from_json(json_data):
    """Extract cover letter data from the structured JSON"""
    
    # Navigate to deliverable.cover_letter
    props = json_data.get('properties', json_data)
    deliverable = props.get('deliverable', {})
    cover_letter = deliverable.get('cover_letter', {})
    
    # Get analysis info
    analysis = props.get('analysis', {})
    role = analysis.get('inferred_target_role', 'the position')
    
    # Try to get company from job posting text
    variable_name = props.get('variable_name', {})
    var_props = variable_name.get('properties', variable_name)
    job_text = var_props.get('{{job_post_text}}', var_props.get('job_post_text', ''))
    
    # Extract company name
    company = "the company"
    for name in ['NVIDIA', 'Apple', 'Google', 'Meta', 'SpaceX', 'Microsoft', 'Amazon', 'Tesla']:
        if name.lower() in job_text.lower():
            company = name
            break
    
    return {
        'opening_hook': cover_letter.get('opening_hook', ''),
        'proof_paragraphs': cover_letter.get('proof_paragraphs', []),
        'closing': cover_letter.get('closing', ''),
        'role': role,
        'company': company
    }


def format_cover_letter(data, name="[Your Name]"):
    """Format the extracted data into a cover letter"""
    
    today = datetime.now().strftime("%B %d, %Y")
    
    # Build body paragraphs from proof_paragraphs
    body = []
    for pp in data['proof_paragraphs']:
        if isinstance(pp, dict):
            para = pp.get('paragraph', '')
            proof = pp.get('proof_point', '')
            if para and proof:
                body.append(f"{para} {proof}")
            elif para:
                body.append(para)
        else:
            body.append(str(pp))
    
    body_text = "\n\n".join(body)
    
    letter = f"""{name}
{today}

Dear Hiring Manager,

{data['opening_hook']}

{body_text}

{data['closing']}

Sincerely,
{name}
"""
    return letter


def extract_from_text(content):
    """Extract cover letter data from flattened/extracted text"""
    
    # Simple regex extraction from flattened text
    opening_match = re.search(r'opening_hook\s+(.+?)(?=proof_paragraphs|$)', content)
    closing_match = re.search(r'closing\s+(.+?)(?=```|$)', content)
    role_match = re.search(r'inferred_target_role\s+(\S+(?:\s+\S+)*?)(?=positioning|$)', content)
    
    # Extract proof paragraphs
    para_matches = re.findall(r'paragraph\s+(.+?)(?=proof_point)', content)
    proof_matches = re.findall(r'proof_point\s+(.+?)(?=paragraph|closing|$)', content)
    
    proof_paragraphs = []
    for i, para in enumerate(para_matches):
        proof = proof_matches[i] if i < len(proof_matches) else ''
        proof_paragraphs.append({'paragraph': para.strip(), 'proof_point': proof.strip()})
    
    # Check for company
    company = "the company"
    for name in ['NVIDIA', 'Apple', 'Google', 'Meta', 'SpaceX', 'Microsoft', 'Amazon', 'Tesla']:
        if name in content:
            company = name
            break
    
    return {
        'opening_hook': opening_match.group(1).strip() if opening_match else '',
        'proof_paragraphs': proof_paragraphs,
        'closing': closing_match.group(1).strip() if closing_match else '',
        'role': role_match.group(1).strip() if role_match else 'the position',
        'company': company
    }


def main():
    parser = argparse.ArgumentParser(description='Convert JSON analysis to cover letter')
    parser.add_argument('input', help='Input file (JSON or extracted text)')
    parser.add_argument('--output', '-o', help='Output file (default: print to console)')
    parser.add_argument('--name', '-n', default='[Your Name]', help='Applicant name')
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Strip code block wrappers if present
        content = strip_code_blocks(content)
        
        # Try to parse as JSON first
        try:
            json_data = json.loads(content)
            data = parse_cover_letter_from_json(json_data)
        except json.JSONDecodeError:
            # If it's extracted text, extract from flattened text
            print("Note: Input is not valid JSON, using text extraction", file=sys.stderr)
            data = extract_from_text(content)
        
        # Format the cover letter
        cover_letter = format_cover_letter(data, name=args.name)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(cover_letter)
            print(f"✅ Cover letter saved to {args.output}")
        else:
            print(cover_letter)

    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
