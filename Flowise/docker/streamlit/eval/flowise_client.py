"""Cliente Flowise sincrono para avaliacoes (sem dependencia do Streamlit)."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

ABNT_PROMPT_PREFIX = (
    "Responda em portugues do Brasil, com redacao formal e clara, seguindo estilo tecnico "
    "compativel com ABNT. Use acentuacao correta, termos precisos e, quando fizer sentido, "
    "apresente em topicos objetivos."
)


def _normalize_secret(value: str | None) -> str:
    if not value:
        return ""
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _repair_mojibake(text: str) -> str:
    markers = ("Ã", "Â", "â€", "â€™", "â€œ", "â€”")
    if not any(marker in text for marker in markers):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
        if repaired:
            return repaired
    except UnicodeError:
        pass
    return text


def extract_answer(data: object) -> str:
    if isinstance(data, dict):
        if data.get("text"):
            return str(data["text"])
        if data.get("answer"):
            return str(data["answer"])
        if data.get("response"):
            return str(data["response"])
    return _repair_mojibake(str(data))


def _collect_sse_text(response: requests.Response) -> str:
    full_text = ""
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data:"):
            continue
        payload = raw_line[len("data:") :].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            decoded = json.loads(payload)
            if isinstance(decoded, dict):
                if decoded.get("text"):
                    full_text += _repair_mojibake(str(decoded["text"]))
                elif decoded.get("token"):
                    full_text += _repair_mojibake(str(decoded["token"]))
                elif isinstance(decoded.get("data"), str):
                    full_text += _repair_mojibake(decoded["data"])
            elif isinstance(decoded, str):
                full_text += _repair_mojibake(decoded)
        except json.JSONDecodeError:
            full_text += _repair_mojibake(payload)
    return full_text


def query_flowise_sync(
    question: str,
    *,
    api_url: str | None = None,
    api_token: str | None = None,
    connect_timeout: int | None = None,
    read_timeout: int | None = None,
    streaming: bool = False,
) -> str:
    """Envia uma pergunta ao Flowise e devolve a resposta completa."""
    url = api_url or os.getenv("FLOWISE_API_URL", "").strip()
    token = _normalize_secret(api_token or os.getenv("FLOWISE_API_TOKEN"))
    if not url or not token:
        raise RuntimeError("FLOWISE_API_URL e FLOWISE_API_TOKEN sao obrigatorios para a avaliacao.")

    connect = connect_timeout or int(os.getenv("REQUEST_CONNECT_TIMEOUT_SECONDS", "10"))
    read = read_timeout or int(os.getenv("REQUEST_READ_TIMEOUT_SECONDS", "600"))
    formatted_question = f"{ABNT_PROMPT_PREFIX}\n\nPergunta: {question}"
    headers = {"Authorization": f"Bearer {token}"}
    payload: dict[str, Any] = {"question": formatted_question, "streaming": streaming}

    with requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=(connect, read),
        stream=streaming,
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if streaming and "text/event-stream" in content_type:
            text = _collect_sse_text(response)
            if text.strip():
                return text.strip()

        try:
            return extract_answer(response.json()).strip()
        except ValueError:
            return extract_answer(response.text).strip()
