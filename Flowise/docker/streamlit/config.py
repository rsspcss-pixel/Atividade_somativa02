import os

from app_paths import resolve_app_path

# Defaults (sobrescritos por initialize())
CHAT_BACKEND = "openai"
FLOWISE_API_URL = ""
FLOWISE_API_TOKEN = ""
OPENAI_API_KEY = ""
OPENAI_CHAT_MODEL = "gpt-4o-mini"
REQUEST_CONNECT_TIMEOUT_SECONDS = 10
REQUEST_READ_TIMEOUT_SECONDS = 600
DUCKDB_DATABASE_PATH = "data/compras.duckdb"
DUCKDB_SOURCE_DIR = "data"
CHROMA_ENABLED = False
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
CHROMA_PERSIST_DIRECTORY = "data/chroma"
CHROMA_COLLECTION_NAME = "negociacao_conhecimento"
KNOWLEDGE_TXT_DIR = "data/documentos_negociacao"
CHAT_PROMPT_PREFIX = ""
APP_ENV = "demo"
GUARDRAILS_ENABLED = True
GUARDRAILS_MAX_INPUT_CHARS = 4000
GUARDRAILS_BLOCK_INJECTION = True
GUARDRAILS_BLOCK_ON_PII = False
GUARDRAILS_APPEND_DISCLAIMER = True
GUARDRAILS_RATE_LIMIT = 20
GUARDRAILS_RATE_WINDOW_SECONDS = 60
GUARDRAILS_LINK_ALLOWLIST: list[str] = []

_INITIALIZED = False


def _normalize_secret_env(value: str | None) -> str:
    if not value:
        return ""
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _is_streamlit_cloud() -> bool:
    markers = (
        os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud",
        bool(os.getenv("STREAMLIT_SHARING_BASE_URL")),
        "streamlit.app" in (os.getenv("HOST") or "").lower(),
    )
    if any(markers):
        return True
    try:
        import streamlit as st

        if hasattr(st, "context") and getattr(st.context, "url", ""):
            return "streamlit.app" in str(st.context.url)
    except Exception:
        pass
    return False


def _get_config_value(name: str, default: str = "") -> str:
    """Le st.secrets (Streamlit Cloud) ou variavel de ambiente."""
    try:
        import streamlit as st

        secrets = st.secrets
        if name in secrets:
            raw = secrets[name]
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
            f"Defina em st.secrets (Streamlit Cloud > Settings > Secrets) ou no ambiente."
        )
    return value


def _optional_int(name: str, default: str | None) -> int | None:
    raw = _get_config_value(name, default or "")
    if not raw:
        return None
    return int(raw)


def _env_bool(name: str, default: str = "0") -> bool:
    return _get_config_value(name, default).strip().lower() not in ("0", "false", "no")


def _is_internal_flowise_url(url: str) -> bool:
    lowered = url.lower().strip()
    return (
        lowered.startswith("http://flowise")
        or "localhost" in lowered
        or "127.0.0.1" in lowered
    )


def _resolve_chat_backend() -> str:
    on_cloud = _is_streamlit_cloud()
    requested = _get_config_value("CHAT_BACKEND", "").strip().lower()
    if not requested:
        requested = "openai" if on_cloud else "auto"

    flowise_url = _get_config_value("FLOWISE_API_URL")
    flowise_token = _get_config_value("FLOWISE_API_TOKEN")
    openai_key = _get_config_value("OPENAI_API_KEY")

    if requested == "openai":
        return "openai"
    if requested == "flowise":
        if on_cloud and _is_internal_flowise_url(flowise_url):
            raise ValueError(
                "CHAT_BACKEND=flowise nao funciona no Streamlit Cloud com URL Docker interna. "
                "Use CHAT_BACKEND=openai e OPENAI_API_KEY nos Secrets."
            )
        return "flowise"

    # auto
    if on_cloud:
        if openai_key:
            return "openai"
        if flowise_url and flowise_token and not _is_internal_flowise_url(flowise_url):
            return "flowise"
        raise ValueError(
            "Chat nao configurado no Streamlit Cloud. "
            "Defina OPENAI_API_KEY e CHAT_BACKEND=openai em Settings > Secrets."
        )

    if openai_key and (not flowise_url or _is_internal_flowise_url(flowise_url)):
        return "openai"
    if flowise_url and flowise_token:
        return "flowise"
    if openai_key:
        return "openai"
    raise ValueError(
        "Chat nao configurado. Localmente use FLOWISE_API_URL + FLOWISE_API_TOKEN (Docker) "
        "ou OPENAI_API_KEY."
    )


def initialize() -> None:
    """Carrega configuracao apos st.set_page_config (secrets disponiveis no Cloud)."""
    global _INITIALIZED
    global CHAT_BACKEND, FLOWISE_API_URL, FLOWISE_API_TOKEN, OPENAI_API_KEY, OPENAI_CHAT_MODEL
    global REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS
    global DUCKDB_DATABASE_PATH, DUCKDB_SOURCE_DIR, CHROMA_ENABLED, OPENAI_EMBEDDING_MODEL
    global CHROMA_PERSIST_DIRECTORY, CHROMA_COLLECTION_NAME, KNOWLEDGE_TXT_DIR, CHAT_PROMPT_PREFIX
    global APP_ENV, GUARDRAILS_ENABLED, GUARDRAILS_MAX_INPUT_CHARS, GUARDRAILS_BLOCK_INJECTION
    global GUARDRAILS_BLOCK_ON_PII, GUARDRAILS_APPEND_DISCLAIMER, GUARDRAILS_RATE_LIMIT
    global GUARDRAILS_RATE_WINDOW_SECONDS, GUARDRAILS_LINK_ALLOWLIST

    if _INITIALIZED:
        return

    CHAT_BACKEND = _resolve_chat_backend()
    FLOWISE_API_URL = ""
    FLOWISE_API_TOKEN = ""
    OPENAI_API_KEY = ""
    OPENAI_CHAT_MODEL = "gpt-4o-mini"

    if CHAT_BACKEND == "flowise":
        FLOWISE_API_URL = _required("FLOWISE_API_URL")
        FLOWISE_API_TOKEN = _required("FLOWISE_API_TOKEN")
    else:
        OPENAI_API_KEY = _required("OPENAI_API_KEY")
        OPENAI_CHAT_MODEL = _get_config_value("OPENAI_CHAT_MODEL", "gpt-4o-mini") or "gpt-4o-mini"

    REQUEST_CONNECT_TIMEOUT_SECONDS = _optional_int("REQUEST_CONNECT_TIMEOUT_SECONDS", "10")
    REQUEST_READ_TIMEOUT_SECONDS = _optional_int("REQUEST_READ_TIMEOUT_SECONDS", "600")
    DUCKDB_DATABASE_PATH = str(
        resolve_app_path(_get_config_value("DUCKDB_DATABASE_PATH", "data/compras.duckdb") or "data/compras.duckdb")
    )
    DUCKDB_SOURCE_DIR = str(resolve_app_path(_get_config_value("DUCKDB_SOURCE_DIR", "data") or "data"))
    CHROMA_ENABLED = _env_bool("CHROMA_ENABLED", "0")
    if not OPENAI_API_KEY:
        OPENAI_API_KEY = _get_config_value("OPENAI_API_KEY")
    OPENAI_EMBEDDING_MODEL = (
        _get_config_value("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small") or "text-embedding-3-small"
    )
    CHROMA_PERSIST_DIRECTORY = str(
        resolve_app_path(_get_config_value("CHROMA_PERSIST_DIRECTORY", "data/chroma") or "data/chroma")
    )
    CHROMA_COLLECTION_NAME = (
        _get_config_value("CHROMA_COLLECTION_NAME", "negociacao_conhecimento") or "negociacao_conhecimento"
    )
    KNOWLEDGE_TXT_DIR = str(
        resolve_app_path(
            _get_config_value("KNOWLEDGE_TXT_DIR", "data/documentos_negociacao") or "data/documentos_negociacao"
        )
    )
    CHAT_PROMPT_PREFIX = _get_config_value("CHAT_PROMPT_PREFIX", "")
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
    _INITIALIZED = True
