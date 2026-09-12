"""Prompt construction and structured evaluation."""

import json
from typing import Any

from .config import (
    COMMANDER_SYSTEM,
    FINAL_REPORT_SCHEMA,
    PERSONAS,
    PSYCHOLOGIST_SYSTEM,
)


def persona_system(persona: str) -> str:
    return (
        PSYCHOLOGIST_SYSTEM
        if persona == "ISSB Psychologist"
        else COMMANDER_SYSTEM
    )


def learning_prompt(persona: str) -> str:
    focus = PERSONAS[persona]["focus"]
    return f"""
You are now in the LEARNING phase for the {persona} simulation.

This persona's focus areas are: {focus}.

TRAIT ROTATION: Look at your own previous messages in this conversation to
see which of the traits above you've already taught a principle about. Pick
a DIFFERENT trait for this turn — do not keep returning to the same one
(e.g. decision-making/leadership) turn after turn. Across a full session, aim
to touch a genuinely varied spread of these traits, not just the easiest or
most obvious one.

TONE: Talk like an experienced senior mentor speaking directly to one
candidate — warm but direct, no corporate or customer-support phrasing.
Never say things like "Certainly!", "I understand you want...", or "As an AI".
Do not narrate what you're about to do — just do it. Vary your phrasing and
structure turn to turn; do not repeat the same template every time.

CONTEXT: If the candidate's previous message in this conversation was an
answer to a practice question, react to what they specifically wrote before
introducing anything new — point out one concrete thing that worked and one
thing to sharpen, using their own words or details where possible. If this is
the very first message in the session, skip straight to teaching.

Then, incrementally:
1. Explain one useful ISSB preparation principle tied to the trait you picked,
   in simple, direct English.
2. Illustrate it briefly — a bare situation/action/result skeleton, not a
   full polished story a candidate could copy and reuse verbatim.
3. Ask exactly one small practice question.
4. Do not score the candidate yet.
5. Do not overwhelm the candidate with a syllabus.

Mention, briefly and only once per session (not every turn), that authentic,
concise answers beat memorized "perfect" ones.
"""

def readiness_prompt(persona: str) -> str:
    return f"""
The candidate is at the READINESS GATE for the {persona} simulation.

Briefly explain that the formal simulation will become more demanding and that
the candidate remains free to continue practice instead. Ask whether they are
ready. If they decline, respond respectfully and offer one short practice
activity rather than pressuring them.
"""


def testing_prompt(persona: str, question_number: int, asked_questions: list[str]) -> str:
    focus = PERSONAS[persona]["focus"]
    covered = "\n".join(f"- {q}" for q in asked_questions) if asked_questions else "None yet — this is the first question."

    return f"""
TESTING PHASE — Question {question_number + 1} of 8.

You are conducting a live ISSB-style interview as the {persona}. Primary
focus areas: {focus}.

Topics/questions already covered in this session (do not repeat these):
{covered}
You are not filling a quota. If the candidate's last answer raises something
genuinely worth pressing on, stay with it rather than moving on just because
a new topic hasn't been covered yet.

Look at the candidate's most recent answer in this conversation. Ask ONE
question that either:
- Follows up on something specific and notable they just said, digging for
  concrete detail the way a real evaluator would, OR
- Opens a fresh topic within the focus areas above, if their last answer was
  already thoroughly explored or this is the first question.

Over the full 8-question session, make sure you eventually touch on a range
of the focus areas above rather than fixating on just one or two.

Ask only one question, then stop. Do not answer it yourself, do not reveal a
model answer, and do not reveal any scoring criteria.
"""
def probe_prompt(persona: str, base_question: str) -> str:
    return f"""
The candidate just gave a very brief or vague answer to this question:
"{base_question}"

As a real ISSB {persona}, do not accept this
as sufficient. Ask ONE natural, respectful follow-up that pushes them to
elaborate with a concrete example or detail — the way a real evaluator would
when an answer is too thin to assess. Do not reveal scoring criteria, do not
answer for them, and do not lecture them about being too brief — just ask the
follow-up naturally, as part of the conversation.
"""

def final_evaluation_prompt(persona: str, answers: list[dict[str, Any]]) -> list[dict]:
    evidence = json.dumps(answers, ensure_ascii=False, indent=2)
    schema = json.dumps(FINAL_REPORT_SCHEMA, ensure_ascii=False, indent=2)

    system = persona_system(persona) + """
FINAL EVALUATION MODE.

Use ONLY the candidate evidence supplied in the user message. Do not invent
events, achievements, personality facts, or current-affairs knowledge.

Return valid JSON only, matching the schema exactly.

Scoring:
- Each leadership trait is an evidence-based practice score from 0-100.
- "force_indicators" are comparative PRACTICE FIT INDICATORS, not official
  ISSB percentiles, not probabilities, and not recommendations by Army, Navy,
  or PAF.
- Keep evidence confidence in mind: a sparse answer should not produce an
  artificially high score.
- "habits" and "shortcomings" must be actionable and grounded in responses.
- "response_review" must contain objects with:
  question, how_they_answered, how_they_should_not_have_answered,
  ideal_recommended_response.
- The ideal response should be a model of structure and authenticity, not a
  script the candidate should memorize. Do not fabricate candidate experiences.
- Do not use protected traits or medical/clinical labels.

Expected JSON schema:
""" + schema

    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                f"Persona: {persona}\n\nCandidate test evidence:\n{evidence}"
            ),
        },
    ]


def parse_evaluation(raw: str) -> dict:
    """Parse JSON defensively and validate required top-level fields."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The model returned invalid evaluation JSON.") from exc

    required = {
        "leadership_traits",
        "force_indicators",
        "strengths",
        "habits",
        "shortcomings",
        "response_review",
        "overall_summary",
    }
    missing = required.difference(data)
    if missing:
        raise ValueError(f"Evaluation JSON is missing fields: {sorted(missing)}")

    # Clamp numeric scores to the promised practice range.
    for key, value in data["leadership_traits"].items():
        try:
            data["leadership_traits"][key] = max(0, min(100, float(value)))
        except (TypeError, ValueError):
            data["leadership_traits"][key] = 0

    for force in ["Army", "Navy", "PAF"]:
        try:
            data["force_indicators"][force] = max(
                0, min(100, float(data["force_indicators"].get(force, 0)))
            )
        except (TypeError, ValueError):
            data["force_indicators"][force] = 0

    return data
