"""Conhecimento Lumina embutido (mesmo conteudo usado pelo agente Flowise)."""

from __future__ import annotations

from pathlib import Path

KNOWLEDGE_FILES = (
    "perfil_empresa_lumina_cosmetics.txt",
    "guia_gestao_lotes_minimos_compra.txt",
    "catalogo_insumos_destaque_lumina.txt",
    "parametros_custo_armazenagem_e_servicos_logisticos.txt",
    "guia_prazo_validade_e_permanencia_estoque.txt",
)
KNOWLEDGE_MAX_CHARS = 3200


def load_knowledge_digest(knowledge_dir: str | Path, max_chars: int = KNOWLEDGE_MAX_CHARS) -> str:
    base = Path(knowledge_dir)
    parts: list[str] = []
    for name in KNOWLEDGE_FILES:
        path = base / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if text:
            parts.append(text)
    if not parts:
        return ""
    digest = "\n\n---\n\n".join(parts)
    if len(digest) <= max_chars:
        return digest
    return digest[: max_chars - 3].rstrip() + "..."


def build_system_message(knowledge_dir: str | Path) -> str:
    knowledge = load_knowledge_digest(knowledge_dir)
    return (
        "Voce e o assistente de compras da Lumina Cosmetics (fabrica de cosmeticos, SP). "
        "Responda SEMPRE em portugues do Brasil, de forma AGIL: maximo 4 bullets ou 6 linhas curtas. "
        "Va direto ao ponto; evite introducoes longas e repeticao. "
        "Para conceitos de lote minimo, EOQ, cobertura, validade ou perfil da empresa, "
        "use o CONHECIMENTO BASE abaixo. "
        "Se faltar dado numerico especifico de um insumo, diga o que falta em 1 linha.\n\n"
        f"CONHECIMENTO BASE:\n{knowledge}"
    )
