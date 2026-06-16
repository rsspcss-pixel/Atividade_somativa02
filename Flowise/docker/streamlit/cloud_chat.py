"""Chat OpenAI direto no Streamlit Cloud (sem Flowise externo)."""

from __future__ import annotations

import json
from typing import Callable

import requests

from knowledge_base import build_system_message

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


def query_openai_chat(
    question: str,
    placeholder,
    *,
    api_key: str,
    model: str,
    knowledge_dir: str,
    connect_timeout: int,
    read_timeout: int,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "stream": True,
        "max_tokens": 384,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": build_system_message(knowledge_dir)},
            {"role": "user", "content": question},
        ],
    }
    timeout = (connect_timeout, read_timeout)
    full_text = ""

    with requests.post(
        OPENAI_CHAT_URL,
        headers=headers,
        json=payload,
        timeout=timeout,
        stream=True,
    ) as response:
        response.raise_for_status()
        for raw_line in response.iter_lines(decode_unicode=True):
            if cancel_check and cancel_check():
                break
            if not raw_line or not raw_line.startswith("data:"):
                continue
            data = raw_line[len("data:") :].strip()
            if not data or data == "[DONE]":
                continue
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            token = delta.get("content")
            if token:
                full_text += token
                placeholder.markdown(full_text)

    return full_text.strip() or "Nao foi possivel obter resposta do modelo."
