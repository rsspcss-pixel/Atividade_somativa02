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

from agent_config import (
    CHATFLOW_ID,
    DEFAULT_CHAT_MODEL,
    MAX_TOKENS,
    MEMORY_WINDOW,
    TEMPERATURE,
    build_system_message,
)

DEFAULT_DB = Path.home() / ".flowise" / "database.sqlite"


def tune_flow_data(flow_data: dict) -> tuple[dict, list[str]]:
    changes: list[str] = []
    nodes = flow_data.get("nodes", [])
    target_system = build_system_message()
    for node in nodes:
        if node.get("data", {}).get("name") != "agentAgentflow":
            continue
        inputs = node.setdefault("data", {}).setdefault("inputs", {})

        if inputs.get("agentUserMessage"):
            inputs["agentUserMessage"] = ""
            changes.append("agentUserMessage removida")

        if inputs.get("agentMemoryType") != "windowSize":
            inputs["agentMemoryType"] = "windowSize"
            changes.append("memoria: windowSize")

        if inputs.get("agentMemoryWindowSize") != MEMORY_WINDOW:
            inputs["agentMemoryWindowSize"] = MEMORY_WINDOW
            changes.append(f"memoria: window={MEMORY_WINDOW}")

        messages = inputs.get("agentMessages") or []
        if messages and messages[0].get("role") == "system":
            if messages[0].get("content") != target_system:
                messages[0]["content"] = target_system
                changes.append("system prompt atualizado (conhecimento + respostas ageis)")

        cfg = inputs.setdefault("agentModelConfig", {})
        if cfg.get("temperature") != TEMPERATURE:
            cfg["temperature"] = TEMPERATURE
            changes.append(f"temperature: {TEMPERATURE}")
        if cfg.get("maxTokens") != MAX_TOKENS:
            cfg["maxTokens"] = MAX_TOKENS
            changes.append(f"maxTokens: {MAX_TOKENS}")
        model_name = cfg.get("modelName") or ""
        if model_name != DEFAULT_CHAT_MODEL:
            changes.append(f"modelName: {model_name or '(vazio)'} -> {DEFAULT_CHAT_MODEL}")
            cfg["modelName"] = DEFAULT_CHAT_MODEL

    return flow_data, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Otimiza latencia do chatflow Flowise")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--chatflow-id", default=CHATFLOW_ID)
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
