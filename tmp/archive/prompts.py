
ANALYSIS_SYSTEM_PROMPT = """
<instructions>
1. Read the full job posting and infer: role_title, company_name, seniority_level.
2. Extract ATS keywords and explicitly mentioned tools/tech from the job post.
3. Build a variable set of categories (3–10) based on the job post emphasis.
   - For each category, include jd_signals (exact phrases) and priority.
4. Build a skill_inventory grouped by relevant domains (e.g., frontend, backend, mobile, cloud/platform, data, testing, devops).
   - Only include skills that are explicitly mentioned OR strongly implied by the job post context.
5. Generate a question_bank that a separate script can ask:
   A) skill_questions: for each skill in skill_inventory, generate a question that asks:
      - whether the candidate has the skill
      - how they used it (project/context)
      - what they built (what)
      - how/why they did it (how/why)
      - result/impact (metrics if possible)
      - links/artifacts if available
   B) category_questions: for each category, generate 2–6 broader questions that collect the same evidence dimensions.
6. Do NOT answer the questions. Do NOT reference a resume. Output ONLY structured JSON matching schema.
</instructions>
"""

ANALYSIS_SCHEMA = """
{
  "type": "object",
  "properties": {
    "variable_name": {
      "type": "object",
      "properties": {
        "{{job_post_text}}": {
          "type": "string",
          "description": "Full job posting text"
        }
      },
      "required": ["{{job_post_text}}"],
      "additionalProperties": false
    },
    "analysis": {
      "type": "object",
      "properties": {
        "role_title": { "type": "string" },
        "company_name": { "type": "string" },
        "seniority_level": {
          "type": "string",
          "enum": ["intern", "junior", "mid", "senior", "staff", "principal", "lead", "manager", "director", "unknown"]
        },
        "ats_keywords": {
          "type": "array",
          "items": { "type": "string" },
          "description": "ATS keywords/phrases (prefer exact wording from the job post)"
        },
        "tools_and_tech": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Explicit tools/tech mentioned in the job post"
        },
        "categories": {
          "type": "array",
          "minItems": 3,
          "description": "Variable set of competency categories derived from the job post",
          "items": {
            "type": "object",
            "properties": {
              "category_id": { "type": "string" },
              "category_label": { "type": "string" },
              "priority": {
                "type": "string",
                "enum": ["must_have", "strong_signal", "nice_to_have"]
              },
              "jd_signals": {
                "type": "array",
                "items": { "type": "string" },
                "description": "Exact phrases from the job post that justify this category"
              },
              "evidence_dimensions": {
                "type": "array",
                "items": {
                  "type": "string",
                  "enum": ["what", "how_why", "tools", "scope", "result_impact", "collaboration", "constraints", "links_artifacts"]
                },
                "description": "What dimensions should be collected for this category"
              }
            },
            "required": ["category_id", "category_label", "priority", "jd_signals", "evidence_dimensions"]
          }
        },
        "skill_inventory": {
          "type": "array",
          "description": "Skills grouped for targeted questioning",
          "items": {
            "type": "object",
            "properties": {
              "group_id": {
                "type": "string",
                "description": "e.g., frontend, backend, mobile, cloud_platform, testing_quality, data, devops"
              },
              "group_label": { "type": "string" },
              "items": {
                "type": "array",
                "items": { "type": "string" },
                "description": "Skills/tech items in this group"
              },
              "jd_signals": {
                "type": "array",
                "items": { "type": "string" },
                "description": "JD phrases that justify including this skill group"
              }
            },
            "required": ["group_id", "group_label", "items", "jd_signals"]
          }
        },
        "question_bank": {
          "type": "object",
          "properties": {
            "skill_questions": {
              "type": "array",
              "description": "One question per skill item",
              "items": {
                "type": "object",
                "properties": {
                  "question_id": { "type": "string" },
                  "group_id": { "type": "string" },
                  "skill": { "type": "string" },
                  "question_text": { "type": "string" },
                  "answer_fields": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "field_key": { "type": "string" },
                        "field_label": { "type": "string" },
                        "expected_format": {
                          "type": "string",
                          "enum": ["short_text", "long_text", "bullet_list", "metric_list", "tool_list", "date_range", "link_list", "boolean"]
                        },
                        "required": { "type": "boolean" }
                      },
                      "required": ["field_key", "field_label", "expected_format", "required"]
                    }
                  }
                },
                "required": ["question_id", "group_id", "skill", "question_text", "answer_fields"]
              }
            },
            "category_questions": {
              "type": "array",
              "description": "Broader questions per category",
              "items": {
                "type": "object",
                "properties": {
                  "question_id": { "type": "string" },
                  "category_id": { "type": "string" },
                  "question_text": { "type": "string" },
                  "answer_fields": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "field_key": { "type": "string" },
                        "field_label": { "type": "string" },
                        "expected_format": {
                          "type": "string",
                          "enum": ["short_text", "long_text", "bullet_list", "metric_list", "tool_list", "date_range", "link_list", "boolean"]
                        },
                        "required": { "type": "boolean" }
                      },
                      "required": ["field_key", "field_label", "expected_format", "required"]
                    }
                  }
                },
                "required": ["question_id", "category_id", "question_text", "answer_fields"]
              }
            }
          },
          "required": ["skill_questions", "category_questions"]
        }
      },
      "required": [
        "role_title",
        "company_name",
        "seniority_level",
        "ats_keywords",
        "tools_and_tech",
        "categories",
        "skill_inventory",
        "question_bank"
      ]
    }
  },
  "required": ["variable_name", "analysis"]
}
"""

RESUME_SYSTEM_PROMPT = """
<instructions>
1. Build from scratch using ONLY:
   - job_post_text
   - responses.categories[].questions[].answer
2. DO NOT invent facts. If the job requires something not supported by answers, add it to do_not_invent_list.
3. Extract ATS keywords and mirror phrasing naturally (no keyword stuffing).
4. Convert answers into proof points:
   - Action + Tool/Tech + Scope + Result/Impact
   - Prefer numbers if the answer includes them. Do not fabricate metrics.
5. Resume output rules:
   - 1 page-ish, ATS-friendly, plain text
   - 2–4 summary bullets
   - Skills grouped to match job emphasis
   - 2–4 projects (preferred for interns/new grads)
   - Experience section allowed but must not be invented
6. Cover letter rules:
   - 250–400 words, 3–4 paragraphs
   - Hook: builder mindset + mission alignment
   - Body: 2 proof paragraphs anchored by strongest evidence
   - Close: collaboration/learning + call to action
7. Output JSON matching the schema. Include both resume_text and cover_letter_text unless output_mode says otherwise.
</instructions>
"""
RESUME_SCHEMA = """
{
  "type": "object",
  "properties": {
    "deliverable": {
      "type": "object",
      "properties": {
        "resume": {
          "type": "object",
          "properties": {
            "headline": { "type": "string", "description": "Name + target role + location/remote (if known)" },

            "summary_bullets": {
              "type": "array",
              "items": { "type": "string" },
              "description": "2–4 bullets. Use job language + proof points."
            },

            "skills_groups": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "group": { "type": "string" },
                  "items": { "type": "array", "items": { "type": "string" } }
                }
              }
            },

            "projects": {
              "type": "array",
              "description": "Prefer 2–4 projects for intern/new grad",
              "items": {
                "type": "object",
                "properties": {
                  "name": { "type": "string" },
                  "stack": { "type": "array", "items": { "type": "string" } },
                  "bullets": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "3–5 bullets each. Action + tool + scope + result/impact."
                  },
                  "links": { "type": "array", "items": { "type": "string" } }
                }
              }
            },

            "experience": {
              "type": "array",
              "description": "Can be empty if no work experience; do not invent",
              "items": {
                "type": "object",
                "properties": {
                  "role": { "type": "string" },
                  "company": { "type": "string" },
                  "dates": { "type": "string" },
                  "bullets": { "type": "array", "items": { "type": "string" } }
                }
              }
            },

            "education": {
              "type": "array",
              "items": { "type": "string" }
            }
          }
        },

        "resume_text": { "type": "string", "description": "Fully assembled plain-text resume" },

        "cover_letter": {
          "type": "object",
          "properties": {
            "opening_hook": { "type": "string" },
            "proof_paragraphs": {
              "type": "array",
              "items": { "type": "string" },
              "description": "2 paragraphs, each anchored by a proof point"
            },
            "closing": { "type": "string" }
          }
        },

        "cover_letter_text": { "type": "string", "description": "Fully assembled cover letter" }
      },
      "required": ["resume_text", "cover_letter_text"]
    }
  },
  "required": ["deliverable"]
}
"""
