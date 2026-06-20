"""Configuracao compartilhada do agentflow Assistente Negociacao (velocidade + conhecimento)."""

from __future__ import annotations

from pathlib import Path

CHATFLOW_ID = "f92dd892-ced9-4396-863b-9675b17242fb"
AGENT_FLOW_NAME = "Assistente Negociacao"
TOOL_NAMES = ("buscar_insumo_duckdb", "classificar_risco_renegociacao")
DEFAULT_CHAT_MODEL = "nvidia/nemotron-3-nano-4b"
CLOUD_CHAT_MODEL = "gpt-4o-mini"

# Respostas ageis: menos tokens, menos contexto, sem tools no agente local
MAX_TOKENS = "128"
TEMPERATURE = 0.2
MEMORY_WINDOW = 2
ENABLE_CHAT_MEMORY = False
LOCAL_ATTACH_TOOLS = False

KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[1] / "streamlit" / "data" / "documentos_negociacao"
)
KNOWLEDGE_FILES = (
    "perfil_empresa_lumina_cosmetics.txt",
    "guia_gestao_lotes_minimos_compra.txt",
)
KNOWLEDGE_MAX_CHARS = 1400
DOC_STORE_DESCRIPTION = (
    "Docs Lumina: lotes minimos, EOQ, cobertura, perfil da empresa cosmetica, "
    "custos de armazenagem, validade e insumos destaque."
)


def load_knowledge_digest(max_chars: int = KNOWLEDGE_MAX_CHARS) -> str:
    parts: list[str] = []
    for name in KNOWLEDGE_FILES:
        path = KNOWLEDGE_DIR / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        parts.append(text)
    if not parts:
        return ""
    digest = "\n\n---\n\n".join(parts)
    if len(digest) <= max_chars:
        return digest
    return digest[: max_chars - 3].rstrip() + "..."


def build_system_message() -> str:
    knowledge = load_knowledge_digest()
    return (
        "Assistente de compras Lumina Cosmetics (SP). Responda em portugues do Brasil, "
        "de forma CURTA: no maximo 3 bullets ou 4 linhas. Va direto ao ponto, sem introducao. "
        "Use o CONHECIMENTO BASE para lote minimo, EOQ, cobertura, validade e perfil da empresa. "
        "Nao invente numeros de insumo; se faltar dado, diga em 1 linha.\n\n"
        f"CONHECIMENTO BASE:\n{knowledge}"
    )


from agentflow_builder import build_agentflow


def build_flow_data(
    credential_id: str | None = None,
    *,
    cloud: bool = False,
    tool_ids: dict[str, str] | None = None,
) -> dict:
    """Monta flowData do agentflow (local=LM Studio, cloud=OpenAI)."""
    resolved_tool_ids: tuple[str, ...] = ()
    if not cloud and LOCAL_ATTACH_TOOLS and tool_ids:
        resolved_tool_ids = tuple(tool_ids[name] for name in TOOL_NAMES if name in tool_ids)

    if cloud:
        model_config: dict = {
            "cache": "",
            "modelName": CLOUD_CHAT_MODEL,
            "temperature": str(TEMPERATURE),
            "streaming": True,
            "maxTokens": MAX_TOKENS,
            "topP": "",
            "frequencyPenalty": "",
            "presencePenalty": "",
            "timeout": "",
            "strictToolCalling": "",
            "stopSequence": "",
            "basepath": "",
            "proxyUrl": "",
            "baseOptions": "",
            "allowImageUploads": "",
            "imageResolution": "low",
            "reasoningEffort": "",
        }
        agent_model = "chatOpenAI"
        if credential_id:
            model_config["credential"] = credential_id
            model_config["FLOWISE_CREDENTIAL_ID"] = credential_id
    else:
        model_config = {
            "cache": "",
            "modelName": DEFAULT_CHAT_MODEL,
            "temperature": str(TEMPERATURE),
            "streaming": True,
            "maxTokens": MAX_TOKENS,
            "topP": "",
            "frequencyPenalty": "",
            "presencePenalty": "",
            "timeout": "",
            "strictToolCalling": "",
            "stopSequence": "",
            "basepath": "http://host.docker.internal:1234/v1",
            "proxyUrl": "",
            "baseOptions": "",
            "allowImageUploads": "",
            "imageResolution": "low",
            "reasoningEffort": "",
            "openAIApiKey": "lm-studio",
        }
        agent_model = "chatOpenAICustom"

    return build_agentflow(
        label=AGENT_FLOW_NAME,
        system_message=build_system_message(),
        tool_ids=resolved_tool_ids,
        model_config=model_config,
        agent_model=agent_model,
        memory_window=MEMORY_WINDOW,
        enable_memory=ENABLE_CHAT_MEMORY,
    )


def prediction_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/api/v1/prediction/{CHATFLOW_ID}"
