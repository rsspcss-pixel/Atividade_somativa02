import os

from app_paths import APP_ROOT, DATA_DIR, resolve_app_path

# Defaults (sobrescritos por initialize())
CHAT_BACKEND = "openai"
FLOWISE_API_URL = ""
FLOWISE_API_TOKEN = ""
OPENAI_API_KEY = ""
OPENAI_CHAT_MODEL = "gpt-4o-mini"
REQUEST_CONNECT_TIMEOUT_SECONDS = 10
REQUEST_READ_TIMEOUT_SECONDS = 600
DUCKDB_DATABASE_PATH = str(resolve_app_path("data/compras.duckdb"))
DUCKDB_SOURCE_DIR = str(DATA_DIR)
CHROMA_ENABLED = False
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
CHROMA_PERSIST_DIRECTORY = str(resolve_app_path("data/chroma"))
CHROMA_COLLECTION_NAME = "negociacao_conhecimento"
KNOWLEDGE_TXT_DIR = str(resolve_app_path("data/documentos_negociacao"))
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
_PATHS_INITIALIZED = False
APP_CONFIG_VERSION = "2026.06.20-cloud5"


def _running_in_docker() -> bool:
    """Streamlit dentro do docker-compose (alcanca http://flowise:3000)."""
    return os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER", "").strip() in ("1", "true", "yes")


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(APP_ROOT / ".env")
    except ImportError:
        pass


def _normalize_secret_env(value: str | None) -> str:
    if not value:
        return ""
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1].strip()
    return s


def _is_streamlit_cloud() -> bool:
    """Detecta Streamlit Community Cloud (nao confundir com Docker headless local)."""
    env_markers = (
        os.getenv("STREAMLIT_RUNTIME_ENVIRONMENT") == "cloud",
        bool(os.getenv("STREAMLIT_SHARING_BASE_URL")),
    )
    if any(env_markers):
        return True

    host = (os.getenv("HOST") or "").lower()
    if "streamlit.app" in host or "share.streamlit.io" in host:
        return True

    try:
        import streamlit as st

        ctx = getattr(st, "context", None)
        url = str(getattr(ctx, "url", "") or "")
        if any(token in url for token in ("streamlit.app", "share.streamlit.io")):
            return True
        # Heuristica: app publicado sem Flowise Docker na mesma rede
        if getattr(ctx, "is_embedded", False) is False and url.startswith("https://"):
            # Evita falso positivo local HTTPS; Cloud quase sempre streamlit.app
            pass
    except Exception:
        pass
    return False


def _get_config_value(name: str, default: str = "") -> str:
    """Le st.secrets (Streamlit Cloud) e depois variavel de ambiente."""
    try:
        import streamlit as st

        secrets = st.secrets
        if name in secrets:
            raw = secrets[name]
            if raw is not None and str(raw).strip():
                return _normalize_secret_env(str(raw))
        try:
            flat = dict(secrets)
            if name in flat and flat[name] is not None and str(flat[name]).strip():
                return _normalize_secret_env(str(flat[name]))
        except Exception:
            pass
    except Exception:
        pass

    env_val = _normalize_secret_env(os.getenv(name))
    if env_val:
        return env_val
    return _normalize_secret_env(default)


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


def _cloud_openai_required_message() -> str:
    return (
        "Streamlit Cloud: use CHAT_BACKEND=openai e OPENAI_API_KEY nos Secrets. "
        "Remova FLOWISE_API_URL e FLOWISE_API_TOKEN (validos apenas no Docker local). "
        "Modelo: Flowise/docker/streamlit/.streamlit/secrets.toml.example"
    )


def _resolve_chat_backend() -> str:
    openai_key = _get_config_value("OPENAI_API_KEY")
    flowise_url = _get_config_value("FLOWISE_API_URL")
    flowise_token = _get_config_value("FLOWISE_API_TOKEN")
    requested = _get_config_value("CHAT_BACKEND", "").strip().lower() or "auto"

    # Streamlit Cloud nunca usa Flowise (servico so existe no Docker local).
    if _is_streamlit_cloud():
        if openai_key:
            return "openai"
        raise ValueError(_cloud_openai_required_message())

    local_flowise_ok = bool(
        flowise_url
        and flowise_token
        and _is_internal_flowise_url(flowise_url)
        and _running_in_docker()
    )
    public_flowise_ok = bool(
        flowise_url and flowise_token and not _is_internal_flowise_url(flowise_url)
    )

    # Docker local: Flowise na rede interna
    if local_flowise_ok and requested in ("flowise", "auto"):
        return "flowise"

    # Flowise publico (Render/ngrok) — so se pedido explicitamente
    if public_flowise_ok and requested == "flowise":
        return "flowise"

    # Streamlit Cloud e demais: OpenAI quando a chave existir
    if openai_key:
        return "openai"

    if public_flowise_ok:
        return "flowise"

    if local_flowise_ok:
        return "flowise"

    if _is_streamlit_cloud() or not _running_in_docker():
        raise ValueError(_cloud_openai_required_message())

    raise ValueError(
        "Chat nao configurado. Localmente use FLOWISE_API_URL + FLOWISE_API_TOKEN (Docker) "
        "ou OPENAI_API_KEY."
    )


def initialize_paths() -> None:
    """Caminhos de dados/ML — sempre absolutos, independente do chat."""
    global _PATHS_INITIALIZED
    global DUCKDB_DATABASE_PATH, DUCKDB_SOURCE_DIR, CHROMA_ENABLED, OPENAI_EMBEDDING_MODEL
    global CHROMA_PERSIST_DIRECTORY, CHROMA_COLLECTION_NAME, KNOWLEDGE_TXT_DIR, CHAT_PROMPT_PREFIX
    global APP_ENV, GUARDRAILS_ENABLED, GUARDRAILS_MAX_INPUT_CHARS, GUARDRAILS_BLOCK_INJECTION
    global GUARDRAILS_BLOCK_ON_PII, GUARDRAILS_APPEND_DISCLAIMER, GUARDRAILS_RATE_LIMIT
    global GUARDRAILS_RATE_WINDOW_SECONDS, GUARDRAILS_LINK_ALLOWLIST
    global REQUEST_CONNECT_TIMEOUT_SECONDS, REQUEST_READ_TIMEOUT_SECONDS, OPENAI_API_KEY

    if _PATHS_INITIALIZED:
        return

    _load_dotenv()

    REQUEST_CONNECT_TIMEOUT_SECONDS = _optional_int("REQUEST_CONNECT_TIMEOUT_SECONDS", "10")
    REQUEST_READ_TIMEOUT_SECONDS = _optional_int("REQUEST_READ_TIMEOUT_SECONDS", "600")
    DUCKDB_DATABASE_PATH = str(
        resolve_app_path(_get_config_value("DUCKDB_DATABASE_PATH", "data/compras.duckdb") or "data/compras.duckdb")
    )
    DUCKDB_SOURCE_DIR = str(resolve_app_path(_get_config_value("DUCKDB_SOURCE_DIR", "data") or "data"))
    CHROMA_ENABLED = _env_bool("CHROMA_ENABLED", "0")
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
    _PATHS_INITIALIZED = True


def initialize_chat() -> None:
    """Credenciais do chat (Flowise ou OpenAI)."""
    global CHAT_BACKEND, FLOWISE_API_URL, FLOWISE_API_TOKEN, OPENAI_API_KEY, OPENAI_CHAT_MODEL

    CHAT_BACKEND = _resolve_chat_backend()
    FLOWISE_API_URL = ""
    FLOWISE_API_TOKEN = ""
    OPENAI_CHAT_MODEL = "gpt-4o-mini"

    if CHAT_BACKEND == "flowise":
        FLOWISE_API_URL = _required("FLOWISE_API_URL")
        FLOWISE_API_TOKEN = _required("FLOWISE_API_TOKEN")
    else:
        if not _get_config_value("OPENAI_API_KEY"):
            if _is_streamlit_cloud():
                raise ValueError(_cloud_openai_required_message())
            raise ValueError(
                "Missing required config: OPENAI_API_KEY. "
                "Defina em st.secrets (Streamlit Cloud > Settings > Secrets) ou no ambiente."
            )
        OPENAI_API_KEY = _required("OPENAI_API_KEY")
        OPENAI_CHAT_MODEL = _get_config_value("OPENAI_CHAT_MODEL", "gpt-4o-mini") or "gpt-4o-mini"


def initialize() -> None:
    """Carrega configuracao apos st.set_page_config (secrets disponiveis no Cloud)."""
    global _INITIALIZED

    if _INITIALIZED:
        return

    initialize_paths()
    initialize_chat()
    _INITIALIZED = True
