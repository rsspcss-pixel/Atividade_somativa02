"""Utilitarios de seguranca compartilhados pelas APIs FastAPI."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

APP_ENV = os.getenv("APP_ENV", "demo").strip().lower() or "demo"
IS_PRODUCTION = APP_ENV == "production"


def require_token_in_production(token: str, env_name: str) -> None:
    if IS_PRODUCTION and not token:
        raise RuntimeError(
            f"{env_name} e obrigatorio quando APP_ENV=production. "
            f"Defina a variavel antes de subir o servico."
        )


def public_error_detail(exc: Exception, *, context: str = "") -> str:
    """Em producao, nao expoe stack nem caminhos internos."""
    if context:
        logger.exception("%s: %s", context, exc)
    else:
        logger.exception("%s", exc)
    if os.getenv("APP_ENV", "demo").strip().lower() == "production":
        return "Erro interno do servidor."
    return str(exc)


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "1" if default else "0").strip().lower()
    return raw in ("1", "true", "yes", "on")
