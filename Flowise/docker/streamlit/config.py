import os

from app_paths import resolve_app_path


def _normalize_secret_env(value: str | None) -> str:
    """Remove espacos e aspas envolventes comuns em ficheiros .env."""
    if not value:
        return ""
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _get_config_value(name: str, default: str = "") -> str:
    """Le variavel de st.secrets (Streamlit Cloud) ou do ambiente."""
    try:
        import streamlit as st

        if name in st.secrets:
            raw = st.secrets[name]
            if raw is not None and str(raw).strip():
                return _normalize_secret_env(str(raw))
    except Exception:
        pass
    return _normalize_secret_env(os.getenv(name, default))


def _required(name: str) -> str:
    value = _get_config_value(name)
    if not value:
        raise ValueError(
            f"Missing required config: {name}. "
            f"Defina em st.secrets ou na variavel de ambiente {name}."
        )
    return value


def _optional_int(name: str, default: str | None) -> int | None:
    raw = _get_config_value(name, default or "")
    if not raw:
        return None
    return int(raw)


def _env_bool(name: str, default: str = "0") -> bool:
    return _get_config_value(name, default).strip().lower() not in ("0", "false", "no")


FLOWISE_API_URL = _required("FLOWISE_API_URL")
FLOWISE_API_TOKEN = _required("FLOWISE_API_TOKEN")
REQUEST_CONNECT_TIMEOUT_SECONDS = _optional_int("REQUEST_CONNECT_TIMEOUT_SECONDS", "10")
REQUEST_READ_TIMEOUT_SECONDS = _optional_int("REQUEST_READ_TIMEOUT_SECONDS", "600")
DUCKDB_DATABASE_PATH = str(
    resolve_app_path(_get_config_value("DUCKDB_DATABASE_PATH", "data/compras.duckdb") or "data/compras.duckdb")
)
DUCKDB_SOURCE_DIR = str(resolve_app_path(_get_config_value("DUCKDB_SOURCE_DIR", "data") or "data"))

# ChromaDB opcional (pesado; desativado por defeito em producao / Streamlit Cloud)
CHROMA_ENABLED = _env_bool("CHROMA_ENABLED", "0")
OPENAI_API_KEY = _get_config_value("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = _get_config_value("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small") or "text-embedding-3-small"
CHROMA_PERSIST_DIRECTORY = str(
    resolve_app_path(_get_config_value("CHROMA_PERSIST_DIRECTORY", "data/chroma") or "data/chroma")
)
CHROMA_COLLECTION_NAME = _get_config_value("CHROMA_COLLECTION_NAME", "negociacao_conhecimento") or "negociacao_conhecimento"
KNOWLEDGE_TXT_DIR = str(
    resolve_app_path(_get_config_value("KNOWLEDGE_TXT_DIR", "data/documentos_negociacao") or "data/documentos_negociacao")
)
CHAT_PROMPT_PREFIX = _get_config_value("CHAT_PROMPT_PREFIX", "")

# Guardrails (ver guardrails.py)
APP_ENV = _get_config_value("APP_ENV", "demo").lower() or "demo"
GUARDRAILS_ENABLED = _env_bool("GUARDRAILS_ENABLED", "1")
GUARDRAILS_MAX_INPUT_CHARS = _optional_int("GUARDRAILS_MAX_INPUT_CHARS", "4000") or 4000
GUARDRAILS_BLOCK_INJECTION = _env_bool("GUARDRAILS_BLOCK_INJECTION", "1")
GUARDRAILS_BLOCK_ON_PII = _env_bool("GUARDRAILS_BLOCK_ON_PII", "0")
GUARDRAILS_APPEND_DISCLAIMER = _env_bool("GUARDRAILS_APPEND_DISCLAIMER", "1")
GUARDRAILS_RATE_LIMIT = _optional_int("GUARDRAILS_RATE_LIMIT", "20") or 20
GUARDRAILS_RATE_WINDOW_SECONDS = _optional_int("GUARDRAILS_RATE_WINDOW_SECONDS", "60") or 60
_link_allowlist_raw = _get_config_value("GUARDRAILS_LINK_ALLOWLIST", "")
GUARDRAILS_LINK_ALLOWLIST = [p.strip() for p in _link_allowlist_raw.split(",") if p.strip()]
