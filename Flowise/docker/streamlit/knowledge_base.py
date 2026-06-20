"""Conhecimento Lumina embutido (mesmo conteudo usado pelo agente Flowise)."""

from __future__ import annotations

from pathlib import Path

KNOWLEDGE_FILES = (
    "perfil_empresa_lumina_cosmetics.txt",
    "guia_gestao_lotes_minimos_compra.txt",
)
KNOWLEDGE_MAX_CHARS = 1400


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
        "Assistente de compras Lumina Cosmetics (SP). Responda em portugues do Brasil, "
        "de forma CURTA: no maximo 3 bullets ou 4 linhas. Va direto ao ponto, sem introducao. "
        "Use o CONHECIMENTO BASE para lote minimo, EOQ, cobertura, validade e perfil da empresa. "
        "Nao invente numeros de insumo; se faltar dado, diga em 1 linha.\n\n"
        f"CONHECIMENTO BASE:\n{knowledge}"
    )
