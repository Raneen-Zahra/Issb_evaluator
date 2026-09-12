"""ISSB Evaluator App - Streamlit entry point."""

from __future__ import annotations

import streamlit as st

from src.config import PERSONAS, SETTINGS, EVALUATION_DIMENSIONS
from src.groq_client import GroqClient, GroqClientError
from src.prompts import (
    final_evaluation_prompt,
    learning_prompt,
    parse_evaluation,
    persona_system,
    probe_prompt,
    readiness_prompt,
    testing_prompt,
)
from src.session_manager import (
    add_message,
    init_state,
    record_answer,
    reset_session,
    test_complete,
)

st.set_page_config(
    page_title="ISSB Evaluator",
    page_icon="🎖️",
    layout="wide",
)

init_state()

# ---------- Styling ----------
st.markdown(
    """
    <style>
    .mode-card {
        padding: 1rem 1.2rem;
        border-radius: 0.8rem;
        border: 1px solid rgba(128,128,128,.25);
        margin-bottom: 1rem;
    }
    .disclaimer {
        font-size: .82rem;
        opacity: .75;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🎖️ ISSB Evaluator")
    st.caption("Practice simulator — not an official ISSB assessment.")

    persona = st.radio(
    "Evaluation persona",
    list(PERSONAS.keys()),
    index=list(PERSONAS.keys()).index(st.session_state.active_persona),
    key="persona_radio",
)

    if persona != st.session_state.active_persona:
        reset_session(persona)
        add_message(
            "assistant",
            f"🔄 **Mode Shift Confirmed:** You are now in **{persona}** mode. "
            f"This session has been reset so the new evaluator can assess you "
            f"consistently.",
        )
        st.rerun()

    st.divider()
    st.subheader("Session")
    st.write(f"**Phase:** {st.session_state.phase.title()}")
    st.write(f"**Test answers:** {len(st.session_state.test_answers)}/8")

    if st.button("🔄 Reset session", use_container_width=True):
        reset_session(persona)
        st.rerun()

    st.divider()
    st.caption(
        "Practice scores and force indicators are heuristic outputs from the "
        "AI simulator. They are not official ISSB percentiles or selection odds."
    )

# ---------- Client ----------
try:
    client = GroqClient(
        model=SETTINGS.model,
        fallback_model=SETTINGS.fallback_model,
        timeout=SETTINGS.timeout,
    )
except GroqClientError as exc:
    client = None
    st.warning(str(exc))

# ---------- Header ----------
st.title("🎖️ ISSB Evaluator App")
st.write(
    "Build clearer expression, stronger self-awareness, and practical "
    "decision-making before entering the formal simulation."
)

st.markdown(
    f"""
    <div class="mode-card">
    <strong>Active mode:</strong> {st.session_state.active_persona}<br>
    <strong>Focus:</strong> {PERSONAS[st.session_state.active_persona]["focus"]}
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Initial learning message ----------
if not st.session_state.chat_history:
    add_message(
        "assistant",
        f"**Mode Shift Confirmed — {st.session_state.active_persona}**\n\n"
        "We will start with a short learning phase. I will give you one useful "
        "principle at a time, then a small practice question. We will not jump "
        "straight into scoring.",
    )

# ---------- Chat history ----------
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------- Learning / readiness / test controls ----------
if st.session_state.phase == "learning":
    if len(st.session_state.chat_history) <= 1:
        # Nothing taught yet — show the button to kick things off.
        if st.button("📘 Start learning guidance", use_container_width=True):
            if not client:
                st.error("Configure your Groq API key first.")
            else:
                messages = [
                    {"role": "system", "content": persona_system(persona) + learning_prompt(persona)},
                    *[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history[-6:]
                    ],
                ]
                try:
                    reply = client.chat(messages, temperature=SETTINGS.temperature, max_tokens=1000)
                    add_message("assistant", reply)
                    st.session_state.practice_turns += 1
                    st.rerun()
                except GroqClientError as exc:
                    st.error(str(exc))
    else:
        # Teaching has started — let the candidate actually type an answer.
        answer = st.chat_input("Type your answer to the practice question…")
        if answer:
            add_message("user", answer)
            if client:
                messages = [
                    {"role": "system", "content": persona_system(persona) + learning_prompt(persona)},
                    *[
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.chat_history[-6:]
                    ],
                ]
                try:
                    reply = client.chat(messages, temperature=SETTINGS.temperature, max_tokens=1000)
                    add_message("assistant", reply)
                    st.session_state.practice_turns += 1
                except GroqClientError as exc:
                    st.error(str(exc))
            st.rerun()

    if st.button("🚦 Go to readiness gate", use_container_width=True):
        add_message(
            "assistant",
            "### Readiness Gate\n\n"
            "You can keep practicing without any pressure. If you choose "
            "the formal simulation, the questions will become more direct "
            "and evidence-focused. **Are you ready for the evaluation?**",
        )
        st.session_state.phase = "readiness"
        st.rerun()

elif st.session_state.phase == "readiness":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Ready for Test", type="primary", use_container_width=True):
            st.session_state.ready = True
            st.session_state.phase = "testing"
            if client:
                try:
                    reply = client.chat(
    [{"role": "system", "content": testing_prompt(persona, 0, [])}],
    temperature=0.3,
    max_tokens=600,
)
                    add_message("assistant", reply)
                except GroqClientError as exc:
                    st.error(str(exc))
            else:
                st.error("Configure your Groq API key first.")
            st.rerun()

    with col2:
        if st.button("📚 Need More Practice", use_container_width=True):
            st.session_state.ready = False
            st.session_state.phase = "learning"
            quote = (
                "“Continuous effort — not instant perfection — is what builds readiness.”"
            )
            add_message(
                "assistant",
                f"That's completely fine. We will keep practicing without forcing "
                f"the test.\n\n> {quote}\n\n"
                "Try one short exercise: answer in 2–3 sentences — "
                "**What is one skill you want to improve before ISSB, and what "
                "are you doing about it?**"
            )
            st.rerun()

elif st.session_state.phase == "testing":
    progress = min(len(st.session_state.test_answers) / 8, 1.0)
    st.progress(progress, text=f"Formal simulation: {len(st.session_state.test_answers)}/8")

    if not test_complete():
        answer = st.chat_input("Type your answer to the current question…")
        if answer:
            # Find the most recent assistant question as the test prompt.
            question = next(
                (
                    m["content"]
                    for m in reversed(st.session_state.chat_history)
                    if m["role"] == "assistant"
                ),
                "Current ISSB simulation question",
            )

            add_message("user", answer)

            is_too_short = len(answer.split()) < 6
            already_probed = st.session_state.get("followup_given", False)

            if is_too_short and not already_probed and client:
                st.session_state.followup_given = True
                try:
                    followup = client.chat(
                        [{"role": "system", "content": probe_prompt(persona, question)}],
                        temperature=0.4,
                        max_tokens=500,
                    )
                    add_message("assistant", followup)
                except GroqClientError as exc:
                    st.error(str(exc))
                st.rerun()

            st.session_state.followup_given = False
            record_answer(question, answer)

            if client:
                try:
                    acknowledgement = client.chat(
                        [
                            {"role": "system", "content": persona_system(persona)},
                            {
                                "role": "user",
                                "content": (
                                    "A candidate just answered this ISSB-style "
                                    "question. Give a very brief neutral acknowledgement "
                                    "without scoring or revealing the ideal answer: "
                                    f"\n\n{answer}"
                                ),
                            },
                        ],
                        temperature=0.25,
                        max_tokens=500,
                    )
                    add_message("assistant", acknowledgement)

                    if not test_complete():
                        asked_questions = [a["question"] for a in st.session_state.test_answers]
                        next_question = client.chat(
                            [
                                {
                                    "role": "system",
                                    "content": testing_prompt(
                                        persona, st.session_state.question_number, asked_questions
                                    ),
                                },
                                *[
                                    {"role": m["role"], "content": m["content"]}
                                    for m in st.session_state.chat_history[-4:]
                                ],
                            ],
                            temperature=0.35,
                            max_tokens=600,
                        )
                        add_message("assistant", next_question)
                except GroqClientError as exc:
                    st.error(str(exc))
            st.rerun()
    else:
        st.success("The 8-question simulation is complete.")
        st.session_state.phase = "completed"
        st.rerun()

elif st.session_state.phase == "completed":
    st.success("Evaluation evidence collected. Generate your report when ready.")

    if st.button("📊 Generate Final Evaluation Report", type="primary", use_container_width=True):
        if not client:
            st.error("Configure your Groq API key first.")
        else:
            with st.spinner("Analyzing response evidence…"):
                try:
                    raw = client.chat(
                        final_evaluation_prompt(
                            persona,
                            st.session_state.test_answers,
                        ),
                        temperature=0.15,
                        max_tokens=3500,
                        json_mode=True,
                    )
                    st.session_state.evaluation = parse_evaluation(raw)
                    st.session_state.report_generated = True
                    st.rerun()
                except (GroqClientError, ValueError) as exc:
                    st.error(f"Could not generate a valid report: {exc}")

# ---------- Report ----------
if st.session_state.evaluation:
    data = st.session_state.evaluation

    st.divider()
    st.header("📊 Final Practice Evaluation")
    st.warning(
        "These are AI-generated practice indicators, not official ISSB "
        "percentiles, selection recommendations, or probabilities."
    )

    st.subheader("Leadership Traits Breakdown")
    traits = data.get("leadership_traits", {})
    for dimension in EVALUATION_DIMENSIONS:
        value = float(traits.get(dimension, 0))
        st.write(f"**{dimension.replace('_', ' ').title()} — {value:.0f}/100**")
        st.progress(int(value))

    st.subheader("Force Practice Indicators")
    force_cols = st.columns(3)
    for col, force in zip(force_cols, ["Army", "Navy", "PAF"]):
        with col:
            value = float(data.get("force_indicators", {}).get(force, 0))
            st.metric(f"{force} practice indicator", f"{value:.0f}%")

    st.subheader("Overall Assessment")
    st.write(data.get("overall_summary", ""))

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Strengths")
        for item in data.get("strengths", []):
            st.markdown(f"- {item}")

        st.subheader("Habits to Build")
        for item in data.get("habits", []):
            st.markdown(f"- {item}")

    with c2:
        st.subheader("Shortcomings to Work On")
        for item in data.get("shortcomings", []):
            st.markdown(f"- {item}")

    st.subheader("Response Review")
    for i, item in enumerate(data.get("response_review", []), 1):
        with st.expander(f"Response {i}: {item.get('question', 'Question')}"):
            st.markdown("**How they answered**")
            st.write(item.get("how_they_answered", ""))
            st.markdown("**How they should NOT have answered**")
            st.write(item.get("how_they_should_not_have_answered", ""))
            st.markdown("**Ideal recommended response structure**")
            st.write(item.get("ideal_recommended_response", ""))

    st.caption(
        "Use the report to identify practice priorities. Do not memorize the "
        "ideal-response examples; your real experiences should remain your own."
    )
