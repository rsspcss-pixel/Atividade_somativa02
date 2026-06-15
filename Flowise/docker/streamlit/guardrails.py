"""
Guardrails locais (pre e pos-LLM) — sem dependencias externas.

Pipeline de entrada: tamanho -> injecao de prompt -> PII (mascarar/bloquear).
Pipeline de saida: PII -> links -> disclaimer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse

DISCLAIMER = (
    "\n\n---\n*Assistente de apoio a negociacao. Valide numeros e decisoes com a equipe de compras.*"
)

# --- PII (padroes Brasil) ---

_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?)?\d{4}[-\s]?\d{4}(?!\d)"
)

# --- Injecao de prompt (heuristicas; camada 1) ---

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instrucoes", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("ignore_portugues", re.compile(r"ignore\s+(as\s+)?instru(c|ç)(o|õ)es", re.I)),
    ("reveal_system", re.compile(r"(reveal|show|print|dump)\s+(the\s+)?(system\s+)?prompt", re.I)),
    ("modo_desenvolvedor", re.compile(r"(modo|mode)\s+(desenvolvedor|developer|admin|root)", re.I)),
    ("tool_abuse", re.compile(r"(save_baseline|avaliar_regressao|regression/run)", re.I)),
    ("jailbreak_dan", re.compile(r"\bDAN\b|do\s+anything\s+now", re.I)),
]

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BARE_URL_RE = re.compile(r"(?<!\]\()https?://[^\s<>]+", re.I)


@dataclass
class GuardrailResult:
    allowed: bool
    text: str
    user_message: str = ""
    actions: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return not self.allowed


def _mask_match(match: re.Match[str], label: str) -> str:
    return f"[{label} REDIGIDO]"


def redact_pii(text: str) -> tuple[str, list[str]]:
    actions: list[str] = []
    out = text

    def sub_once(pattern: re.Pattern[str], label: str, s: str) -> str:
        nonlocal actions
        if pattern.search(s):
            actions.append(f"masked_{label}")
        return pattern.sub(lambda m: _mask_match(m, label), s)

    out = sub_once(_CPF_RE, "CPF", out)
    out = sub_once(_CNPJ_RE, "CNPJ", out)
    out = sub_once(_EMAIL_RE, "EMAIL", out)
    out = sub_once(_PHONE_RE, "TELEFONE", out)
    return out, actions


def detect_prompt_injection(text: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            hits.append(name)
    return hits


def _sanitize_links(text: str, allowlist: Iterable[str]) -> tuple[str, list[str]]:
    allowed = {d.lower().strip() for d in allowlist if d.strip()}
    actions: list[str] = []

    def host_ok(url: str) -> bool:
        if not allowed:
            return False
        try:
            host = (urlparse(url).hostname or "").lower()
        except ValueError:
            return False
        return any(host == d or host.endswith(f".{d}") for d in allowed)

    def replace_md(match: re.Match[str]) -> str:
        label, url = match.group(1), match.group(2).strip()
        if host_ok(url):
            return match.group(0)
        actions.append("stripped_link")
        return f"{label} (link removido)"

    out = _MARKDOWN_LINK_RE.sub(replace_md, text)

    def replace_bare(match: re.Match[str]) -> str:
        url = match.group(0)
        if host_ok(url):
            return url
        actions.append("stripped_link")
        return "(link removido)"

    out = _BARE_URL_RE.sub(replace_bare, out)
    return out, actions


def process_input(
    text: str,
    *,
    max_chars: int = 4000,
    block_injection: bool = True,
    block_on_pii: bool = False,
) -> GuardrailResult:
    """Valida e sanitiza entrada antes de enviar ao LLM."""
    raw = (text or "").strip()
    if not raw:
        return GuardrailResult(allowed=False, text="", user_message="Mensagem vazia.")

    if len(raw) > max_chars:
        return GuardrailResult(
            allowed=False,
            text=raw,
            user_message=(
                f"Mensagem muito longa ({len(raw)} caracteres). "
                f"Limite: {max_chars}. Resuma a pergunta."
            ),
            actions=["blocked_length"],
        )

    injection_hits = detect_prompt_injection(raw)
    if block_injection and injection_hits:
        return GuardrailResult(
            allowed=False,
            text=raw,
            user_message=(
                "Sua mensagem foi bloqueada por padroes associados a manipulacao do assistente "
                "(injecao de prompt). Reformule a pergunta sobre negociacao de insumos."
            ),
            actions=["blocked_injection", *injection_hits],
        )

    redacted, pii_actions = redact_pii(raw)
    if block_on_pii and pii_actions:
        return GuardrailResult(
            allowed=False,
            text=redacted,
            user_message=(
                "Dados pessoais detectados (CPF, CNPJ, e-mail ou telefone). "
                "Remova-os antes de continuar — o chat nao deve processar PII."
            ),
            actions=["blocked_pii", *pii_actions],
        )

    actions = list(pii_actions)
    if redacted != raw:
        actions.append("input_redacted")

    return GuardrailResult(allowed=True, text=redacted, actions=actions)


def process_output(
    text: str,
    *,
    link_allowlist: Iterable[str] | None = None,
    append_disclaimer: bool = True,
) -> GuardrailResult:
    """Sanitiza resposta do LLM antes de exibir ao usuario."""
    raw = (text or "").strip()
    if not raw:
        return GuardrailResult(allowed=True, text="", actions=[])

    out, pii_actions = redact_pii(raw)
    link_actions: list[str] = []
    if link_allowlist is not None:
        out, link_actions = _sanitize_links(out, link_allowlist)

    actions = [*pii_actions, *link_actions]
    if append_disclaimer and DISCLAIMER.strip() not in out:
        out = out + DISCLAIMER
        actions.append("disclaimer_appended")

    return GuardrailResult(allowed=True, text=out, actions=actions)


class RateLimiter:
    """Limite simples por chave (ex.: session_id) em memoria."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float) -> tuple[bool, str]:
        window_start = now - self.window_seconds
        hits = [t for t in self._hits.get(key, []) if t > window_start]
        if len(hits) >= self.max_requests:
            return (
                False,
                f"Limite de {self.max_requests} mensagens a cada "
                f"{int(self.window_seconds)}s atingido. Aguarde um momento.",
            )
        hits.append(now)
        self._hits[key] = hits
        return True, ""
