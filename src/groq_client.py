"""Safe Groq API wrapper."""

from __future__ import annotations

import os
from typing import Iterable, Optional

from groq import Groq
from .config import SETTINGS


class GroqClientError(RuntimeError):
    """Raised when the Groq client cannot complete a request."""


def resolve_api_key(user_key: Optional[str] = None) -> Optional[str]:
    """Resolve the Groq API key from UI input, Streamlit Secrets, or .env."""
    key = (user_key or "").strip()

    # 1. API key manually entered in the Streamlit sidebar
    if key:
        return key

    # 2. Streamlit Community Cloud / Streamlit Secrets
    try:
        import streamlit as st

        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"].strip()
    except Exception:
        pass

    # 3. Local .env / environment variable
    return os.getenv("GROQ_API_KEY", "").strip() or None


class GroqClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = SETTINGS.model,
        fallback_model: str = SETTINGS.fallback_model,
        timeout: float = 45.0,
    ) -> None:
        key = resolve_api_key(api_key)
        if not key:
            raise GroqClientError(
                "Groq API key is missing. Add it in the sidebar or set GROQ_API_KEY."
            )

        self.client = Groq(api_key=key, timeout=timeout, max_retries=2)
        self.model = model
        self.fallback_model = fallback_model

    def chat(
        self,
        messages: Iterable[dict],
        *,
        temperature: float = 0.35,
        max_tokens: int = 1800,
        json_mode: bool = False,
    ) -> str:
        """Call Groq with a fallback model for model-unavailable errors."""
        kwargs = {
            "messages": list(messages),
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as first_error:
            # A fallback is useful when the configured model is unavailable.
            if self.fallback_model and self.fallback_model != self.model:
                try:
                    kwargs["model"] = self.fallback_model
                    response = self.client.chat.completions.create(**kwargs)
                    return response.choices[0].message.content or ""
                except Exception as second_error:
                    raise GroqClientError(
                        f"Groq request failed with both models: {second_error}"
                    ) from second_error

            raise GroqClientError(f"Groq request failed: {first_error}") from first_error
