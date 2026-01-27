#!/usr/bin/env python3
"""
Generate career-focused training data for SmolLM2 fine-tuning.
Creates JSONL file in the same format as dylan_training_data.jsonl
"""
import json
import random
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "career_training_data.jsonl"

# Career advice Q&A pairs
CAREER_QA_PAIRS = [
    # Resume advice
    {
        "user": "How do I improve my resume?",
        "assistant": "Focus on quantifiable achievements. Replace vague statements like 'worked on projects' with specific metrics: 'Led 5-person team to deliver feature used by 10K users, reducing load time by 40%'. Use action verbs, add relevant keywords for ATS systems, and keep it to 1-2 pages."
    },
    {
        "user": "What should I include in my resume summary?",
        "assistant": "Your summary should be 2-3 sentences highlighting: years of experience, key technical skills, your specialty or focus area, and a notable achievement. Example: 'Full-stack engineer with 4 years building scalable web applications. Specialize in React and Node.js with experience in AWS. Led migration that reduced infrastructure costs by 35%.'"
    },
    {
        "user": "How many pages should my resume be?",
        "assistant": "For most professionals, 1 page is ideal if you have under 10 years experience. 2 pages is acceptable for senior roles with extensive relevant experience. Never pad with irrelevant content - quality over quantity. Every bullet point should demonstrate value."
    },
    {
        "user": "Should I include a photo on my resume?",
        "assistant": "In the US, no - it can introduce bias and some companies have policies against it. In Europe and some Asian countries, photos are more common. When in doubt, omit it and let your experience speak for itself."
    },
    {
        "user": "What are good action verbs for a resume?",
        "assistant": "Strong action verbs include: Developed, Implemented, Architected, Led, Optimized, Reduced, Increased, Launched, Mentored, Designed, Built, Automated, Streamlined, Delivered, and Spearheaded. Avoid weak verbs like 'helped with' or 'was responsible for'."
    },

    # Interview advice
    {
        "user": "How do I prepare for a technical interview?",
        "assistant": "Practice coding problems on LeetCode or HackerRank daily - focus on arrays, strings, trees, and dynamic programming. Review system design fundamentals. Most importantly, practice thinking out loud while solving problems. Interviewers want to see your problem-solving process, not just the solution."
    },
    {
        "user": "What is the STAR method?",
        "assistant": "STAR stands for Situation, Task, Action, Result. For behavioral questions, structure your answers: describe the Situation and context, explain the Task or challenge, detail the specific Actions you took, and quantify the Results achieved. This keeps answers focused and impactful."
    },
    {
        "user": "How do I answer 'tell me about yourself'?",
        "assistant": "Keep it to 60-90 seconds. Cover: current role briefly, 1-2 relevant past experiences, why you're interested in this role/company. End with what excites you about this opportunity. Don't recite your resume - tell your professional story with a narrative arc."
    },
    {
        "user": "What questions should I ask the interviewer?",
        "assistant": "Ask about: team structure and collaboration, biggest challenges the team faces, what success looks like in this role, growth opportunities, and the company's technical roadmap. Avoid asking about salary in early rounds or anything easily found on their website."
    },
    {
        "user": "How do I handle a question I don't know the answer to?",
        "assistant": "Be honest but constructive. Say 'I haven't worked with that specifically, but here's how I'd approach learning it...' or 'I'm not sure, but my intuition is... Can you tell me more?' Showing intellectual honesty and problem-solving ability is more valuable than faking knowledge."
    },

    # Job search
    {
        "user": "How do I find good job opportunities?",
        "assistant": "Combine multiple approaches: LinkedIn jobs and networking, company career pages for targets, Indeed/Glassdoor for breadth, AngelList for startups, and referrals from your network. Referrals have the highest success rate - 50% of hires come through connections."
    },
    {
        "user": "Should I apply to jobs I'm not 100% qualified for?",
        "assistant": "Yes! Job requirements are wish lists, not strict requirements. If you meet 60-70% of qualifications, apply. Companies often hire for potential and culture fit. The worst that happens is a no. Many successful hires didn't check every box."
    },
    {
        "user": "How do I negotiate salary?",
        "assistant": "Research market rates on Levels.fyi, Glassdoor, and Blind. Let them make the first offer if possible. Counter 10-20% higher with justification. Consider total compensation: base, equity, bonus, benefits. Be prepared to walk away politely if needed. Practice your pitch beforehand."
    },
    {
        "user": "How long should my job search take?",
        "assistant": "Average is 3-6 months, but it varies widely by market conditions, role level, and effort. Apply consistently (5-10 tailored applications per week is better than 50 generic ones). Track your applications and follow up. Quality networking can accelerate the timeline significantly."
    },
    {
        "user": "Should I take a job I'm not excited about?",
        "assistant": "It depends on your situation. If you need income, there's no shame in taking a bridge job while continuing your search. Every role teaches something. However, if you can afford to wait, holding out for better fit often pays off in long-term career satisfaction and growth."
    },

    # Skills and growth
    {
        "user": "What programming languages should I learn?",
        "assistant": "For general employability: Python (versatile, great for ML/data/scripting), JavaScript/TypeScript (essential for web), and SQL (universal for data). Then specialize based on your interests - Go/Rust for systems, Java/Kotlin for enterprise, Swift/Kotlin for mobile."
    },
    {
        "user": "How do I build a portfolio?",
        "assistant": "Build 2-3 polished projects that solve real problems. Quality over quantity. Include: a full-stack web app, a data or ML project, and something showcasing your specialty. Deploy them live. Write clear READMEs explaining the problem, your approach, and what you learned."
    },
    {
        "user": "Should I get certifications?",
        "assistant": "For cloud (AWS, GCP, Azure), certifications can help, especially for roles requiring specific platforms. For general programming, practical projects and experience matter more. Certifications are most valuable early in career or when switching domains."
    },
    {
        "user": "How do I stay current with technology?",
        "assistant": "Follow tech blogs (Hacker News, dev.to), subscribe to newsletters in your specialty, join communities (Discord, Slack), and build side projects with new tools. The goal isn't to learn everything - it's to have awareness and deep expertise in your focus area."
    },
    {
        "user": "How do I transition to a new tech role?",
        "assistant": "Build projects in the new domain, take relevant courses or certifications, contribute to open source, and network with people already in that role. Frame your existing experience as transferable. Many successful transitions happen internally - talk to your manager about rotation opportunities."
    },

    # Cover letters and applications
    {
        "user": "Do I need a cover letter?",
        "assistant": "If the application has an optional cover letter field, include one - it shows effort and lets you tell your story. Make it specific to the company and role. If you can't write a compelling one, skip it rather than send a generic template."
    },
    {
        "user": "How long should a cover letter be?",
        "assistant": "3-4 paragraphs, about 250-350 words. Opening: why this company/role. Middle: your relevant experience and a key achievement. Closing: express enthusiasm and call to action. Hiring managers skim, so front-load the important parts."
    },
    {
        "user": "How do I follow up after applying?",
        "assistant": "Wait 1-2 weeks, then send a brief, polite follow-up email to the recruiter or hiring manager if you can find their contact. Reference your application, express continued interest, and offer to provide additional info. One follow-up is fine; don't spam."
    },

    # Work and career
    {
        "user": "How do I ask for a raise?",
        "assistant": "Document your achievements and impact with specific metrics. Research market rates. Schedule a meeting with your manager (not during performance review chaos). Present your case: contributions, growth, market data. Be prepared for the conversation to take time - budgets have cycles."
    },
    {
        "user": "Should I take a remote job?",
        "assistant": "Remote work offers flexibility and eliminates commute, but requires self-discipline and intentional communication. Consider: your work style, need for in-person collaboration, career stage (early career benefits from mentorship proximity), and the company's remote culture maturity."
    },
    {
        "user": "How do I deal with imposter syndrome?",
        "assistant": "Recognize it's nearly universal - even senior engineers feel it. Keep a 'wins' document of your achievements. Remember you were hired for a reason. Focus on learning rather than knowing everything. Talk to trusted colleagues - you'll find they share the same feelings."
    },
    {
        "user": "How do I give good feedback to colleagues?",
        "assistant": "Be specific, timely, and actionable. Focus on behavior and impact, not personality. Use 'I noticed' rather than 'you always'. Balance positive and constructive feedback. Deliver difficult feedback privately. Ask for their perspective and make it a dialogue, not a lecture."
    },
    {
        "user": "How do I handle burnout?",
        "assistant": "Recognize the signs: chronic exhaustion, cynicism, reduced effectiveness. Take real time off if possible. Set boundaries on work hours. Talk to your manager about workload. Prioritize sleep, exercise, and activities outside work. Sometimes burnout signals a role or environment mismatch."
    },
]

# System prompts for variety
SYSTEM_PROMPTS = [
    "You are a helpful career advisor. Provide clear, actionable advice about job searching, resume writing, interview preparation, and professional development.",
    "You are an experienced career coach helping professionals navigate their job search and career growth.",
    "You are a knowledgeable career counselor providing practical advice for software professionals.",
]


def generate_training_data():
    """Generate JSONL training data."""
    training_samples = []

    for qa in CAREER_QA_PAIRS:
        # Create training sample
        sample = {
            "messages": [
                {"role": "system", "content": random.choice(SYSTEM_PROMPTS)},
                {"role": "user", "content": qa["user"]},
                {"role": "assistant", "content": qa["assistant"]}
            ],
            "metadata": {
                "category": "career_advice",
                "source": "generated"
            }
        }
        training_samples.append(sample)

    # Shuffle for better training
    random.shuffle(training_samples)

    # Write to JSONL
    with open(OUTPUT_FILE, "w") as f:
        for sample in training_samples:
            f.write(json.dumps(sample) + "\n")

    print(f"Generated {len(training_samples)} training samples")
    print(f"Output: {OUTPUT_FILE}")


def expand_data(multiplier: int = 3):
    """
    Create variations of training data for more robust training.
    Adds slight variations in phrasing.
    """
    variations = []

    for qa in CAREER_QA_PAIRS:
        # Original
        variations.append(qa)

        # Add question variations
        user_variations = [
            qa["user"],
            qa["user"].replace("How do I", "What's the best way to"),
            qa["user"].replace("Should I", "Is it a good idea to"),
            qa["user"].replace("What", "Can you explain what"),
        ]

        for user_var in user_variations[1:multiplier]:
            if user_var != qa["user"]:
                variations.append({
                    "user": user_var,
                    "assistant": qa["assistant"]
                })

    return variations


if __name__ == "__main__":
    generate_training_data()
    print("\nTo train the model, run:")
    print("  python train_career.py")
