"""
Ajusta o chatflow Flowise para menor latencia (menos tokens por requisicao).

Uso (na pasta docker/):
  python flowise/tune_chatflow_speed.py
  python flowise/tune_chatflow_speed.py --db C:/Users/ramon/.flowise/database.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DEFAULT_CHATFLOW_ID = "f92dd892-ced9-4396-863b-9675b17242fb"
DEFAULT_DB = Path.home() / ".flowise" / "database.sqlite"
# Nemotron expoe raciocinio em reasoning_content (Flowise ignora) -> respostas vazias com tools.
DEFAULT_CHAT_MODEL = "google/gemma-3-4b"

SHORT_DOC_STORE_DESCRIPTION = (
    "Documentacao do Projeto Lotes: EOQ, lotes de compra e producao, workflow de "
    "aprovacao, SAP/PFO, shelf life e custos de armazenagem. Consulte para duvidas "
    "sobre lotes, negociacao com fornecedores e revisao de compras."
)

SYSTEM_MESSAGE = (
    "Responda sempre em portugues do Brasil, de forma objetiva e clara. "
    "Use a base de conhecimento quando a pergunta envolver Projeto Lotes, "
    "custos, EOQ ou workflow de aprovacao."
)


def tune_flow_data(flow_data: dict) -> tuple[dict, list[str]]:
    changes: list[str] = []
    nodes = flow_data.get("nodes", [])
    for node in nodes:
        if node.get("data", {}).get("name") != "agentAgentflow":
            continue
        inputs = node.setdefault("data", {}).setdefault("inputs", {})

        stores = inputs.get("agentKnowledgeDocumentStores") or []
        for store in stores:
            old_len = len(store.get("docStoreDescription") or "")
            if old_len > len(SHORT_DOC_STORE_DESCRIPTION) + 20:
                store["docStoreDescription"] = SHORT_DOC_STORE_DESCRIPTION
                changes.append(f"docStoreDescription: {old_len} -> {len(SHORT_DOC_STORE_DESCRIPTION)} chars")

        if inputs.get("agentUserMessage"):
            inputs["agentUserMessage"] = ""
            changes.append("agentUserMessage removida (nao injeta saudacao extra)")

        if inputs.get("agentMemoryType") != "windowSize":
            inputs["agentMemoryType"] = "windowSize"
            changes.append("memoria: allMessages -> windowSize(6)")

        if inputs.get("agentMemoryWindowSize") != 6:
            inputs["agentMemoryWindowSize"] = 6

        messages = inputs.get("agentMessages") or []
        if messages and messages[0].get("role") == "system":
            if messages[0].get("content") != SYSTEM_MESSAGE:
                messages[0]["content"] = SYSTEM_MESSAGE
                changes.append("system prompt enxuto")

        cfg = inputs.setdefault("agentModelConfig", {})
        if cfg.get("temperature") != 0.4:
            cfg["temperature"] = 0.4
            changes.append("temperature: 0.4")
        if cfg.get("maxTokens") != "768":
            cfg["maxTokens"] = "768"
            changes.append("maxTokens: 768")
        model_name = cfg.get("modelName") or ""
        if model_name != DEFAULT_CHAT_MODEL:
            changes.append(f"modelName: {model_name or '(vazio)'} -> {DEFAULT_CHAT_MODEL}")
            cfg["modelName"] = DEFAULT_CHAT_MODEL

    return flow_data, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Otimiza latencia do chatflow Flowise")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--chatflow-id", default=DEFAULT_CHATFLOW_ID)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"Banco nao encontrado: {args.db}")

    conn = sqlite3.connect(str(args.db))
    row = conn.execute(
        "SELECT name, flowData FROM chat_flow WHERE id = ?",
        (args.chatflow_id,),
    ).fetchone()
    if not row:
        raise SystemExit(f"Chatflow nao encontrado: {args.chatflow_id}")

    name, raw = row
    flow_data = json.loads(raw)
    tuned, changes = tune_flow_data(flow_data)

    if not changes:
        print(f"Chatflow '{name}' ja estava otimizado.")
        return 0

    print(f"Chatflow: {name} ({args.chatflow_id})")
    for change in changes:
        print(f"  - {change}")

    if args.dry_run:
        print("Dry-run: nenhuma alteracao gravada.")
        return 0

    conn.execute(
        "UPDATE chat_flow SET flowData = ?, updatedDate = datetime('now') WHERE id = ?",
        (json.dumps(tuned, ensure_ascii=False), args.chatflow_id),
    )
    conn.commit()
    conn.close()
    print("Banco atualizado. Proxima mensagem no chat ja usa a configuracao nova.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
