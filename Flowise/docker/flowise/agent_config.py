"""Configuracao compartilhada do agentflow Assistente Negociacao (velocidade + conhecimento)."""

from __future__ import annotations

from pathlib import Path

CHATFLOW_ID = "f92dd892-ced9-4396-863b-9675b17242fb"
AGENT_FLOW_NAME = "Assistente Negociacao"
TOOL_NAMES = ("buscar_insumo_duckdb", "classificar_risco_renegociacao")
DEFAULT_CHAT_MODEL = "google/gemma-3-4b"

# Respostas ageis: menos tokens gerados e menos contexto no prompt
MAX_TOKENS = "384"
TEMPERATURE = 0.3
MEMORY_WINDOW = 4

KNOWLEDGE_DIR = (
    Path(__file__).resolve().parents[1] / "streamlit" / "data" / "documentos_negociacao"
)
KNOWLEDGE_FILES = (
    "perfil_empresa_lumina_cosmetics.txt",
    "guia_gestao_lotes_minimos_compra.txt",
    "catalogo_insumos_destaque_lumina.txt",
    "parametros_custo_armazenagem_e_servicos_logisticos.txt",
    "guia_prazo_validade_e_permanencia_estoque.txt",
)
KNOWLEDGE_MAX_CHARS = 3200
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
        "Voce e o assistente de compras da Lumina Cosmetics (fabrica de cosmeticos, SP). "
        "Responda SEMPRE em portugues do Brasil, de forma AGIL: maximo 4 bullets ou 6 linhas curtas. "
        "Va direto ao ponto; evite introducoes longas e repeticao. "
        "Para conceitos de lote minimo, EOQ, cobertura, validade ou perfil da empresa, "
        "use o CONHECIMENTO BASE abaixo (nao chame ferramenta). "
        "Chame buscar_insumo_duckdb ou classificar_risco_renegociacao SOMENTE quando o usuario "
        "pedir numeros de um insumo/fornecedor especifico ou risco de renegociacao. "
        "Se faltar dado, diga o que falta em 1 linha.\n\n"
        f"CONHECIMENTO BASE:\n{knowledge}"
    )
