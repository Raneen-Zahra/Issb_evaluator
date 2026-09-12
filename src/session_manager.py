"""Session-state helpers for the Streamlit app."""

from __future__ import annotations

import streamlit as st


def init_state() -> None:
    defaults = {
        "chat_history": [],
        "active_persona": "ISSB Psychologist",
        "phase": "learning",
        "ready": False,
        "evaluation": None,
        "question_number": 0,
        "test_answers": [],
        "practice_turns": 0,
        "report_generated": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session(persona: str | None = None) -> None:
    persona = persona or st.session_state.get("active_persona", "ISSB Psychologist")
    for key in [
        "chat_history",
        "evaluation",
        "test_answers",
        "report_generated",
    ]:
        st.session_state[key] = [] if key in {"chat_history", "test_answers"} else None

    st.session_state.active_persona = persona
    st.session_state.phase = "learning"
    st.session_state.ready = False
    st.session_state.question_number = 0
    st.session_state.practice_turns = 0


def add_message(role: str, content: str, *, kind: str = "chat") -> None:
    st.session_state.chat_history.append(
        {"role": role, "content": content, "kind": kind}
    )


def record_answer(question: str, answer: str) -> None:
    st.session_state.test_answers.append(
        {
            "question": question,
            "answer": answer,
            "index": st.session_state.question_number,
        }
    )
    st.session_state.question_number += 1


def test_complete() -> bool:
    return len(st.session_state.test_answers) >= 8
