"""
Instala o agente Flowise 'DeepEval Regressao' e a custom tool no banco local.

Uso (na pasta docker/):
  python flowise/install_deepeval_agent.py
  python flowise/install_deepeval_agent.py --db C:/Users/ramon/.flowise/database.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from pathlib import Path

DEFAULT_DB = Path.home() / ".flowise" / "database.sqlite"
TOOL_JSON = Path(__file__).resolve().parent / "tools" / "avaliar_regressao_deepeval.json"
CHATFLOW_ID = "a8f3c2e1-9b4d-4a6e-8f1c-2d7e9a0b3c4d"
TOOL_NAME = "avaliar_regressao_deepeval"
AGENT_FLOW_NAME = "Agente DeepEval Regressao"

SYSTEM_MESSAGE = (
    "Voce e o Agente DeepEval de Regressao do assistente Flowise. "
    "Sua funcao e executar avaliacoes de qualidade com a metrica de regressao "
    "(comparacao da resposta atual do chat vs golden dataset e baseline). "
    "Use a ferramenta avaliar_regressao_deepeval com: "
    "modo=run e limit=5 para smoke test rapido; "
    "modo=run sem limit para avaliacao completa; "
    "modo=report para ultimo relatorio; "
    "modo=baseline apos uma boa execucao para salvar referencia; "
    "modo=single com question e expected_output para um caso isolado. "
    "Resuma pass_rate, mean_score, regressions_detected e liste falhas. "
    "Responda em portugues do Brasil."
)


def load_tool_spec() -> dict:
    return json.loads(TOOL_JSON.read_text(encoding="utf-8"))


def upsert_tool(conn: sqlite3.Connection, workspace_id: str) -> str:
    spec = load_tool_spec()
    tool_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, TOOL_NAME))
    existing = conn.execute("SELECT id FROM tool WHERE name = ?", (TOOL_NAME,)).fetchone()
    if existing:
        tool_id = existing[0]
        conn.execute(
            """
            UPDATE tool SET description = ?, color = ?, iconSrc = ?, schema = ?, func = ?,
                   updatedDate = datetime('now')
            WHERE id = ?
            """,
            (
                spec["description"],
                spec.get("color", ""),
                spec.get("iconSrc", ""),
                spec.get("schema", ""),
                spec.get("func", ""),
                tool_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO tool (id, name, description, color, iconSrc, schema, func, workspaceId)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tool_id,
                spec["name"],
                spec["description"],
                spec.get("color", ""),
                spec.get("iconSrc", ""),
                spec.get("schema", ""),
                spec.get("func", ""),
                workspace_id,
            ),
        )
    return tool_id


def build_flow_data(credential_id: str | None) -> dict:
    model_config: dict = {
        "cache": "",
        "modelName": "google/gemma-3-4b",
        "temperature": 0.3,
        "streaming": True,
        "maxTokens": "768",
        "topP": "",
        "frequencyPenalty": "",
        "presencePenalty": "",
        "timeout": "",
        "baseOptions": "",
        "agentModel": "chatOpenAICustom",
        "basepath": "http://host.docker.internal:1234/v1",
    }
    if credential_id:
        model_config["FLOWISE_CREDENTIAL_ID"] = credential_id

    return {
        "nodes": [
            {
                "id": "startAgentflow_0",
                "type": "agentFlow",
                "position": {"x": 100, "y": 120},
                "data": {
                    "id": "startAgentflow_0",
                    "label": "Start",
                    "version": 1.1,
                    "name": "startAgentflow",
                    "type": "Start",
                    "inputs": {"startInputType": "chatInput"},
                },
            },
            {
                "id": "agentAgentflow_0",
                "type": "agentFlow",
                "position": {"x": 420, "y": 120},
                "data": {
                    "id": "agentAgentflow_0",
                    "label": "DeepEval Regressao",
                    "version": 1.1,
                    "name": "agentAgentflow",
                    "type": "Agent",
                    "inputs": {
                        "agentModel": "chatOpenAICustom",
                        "agentMessages": [{"role": "system", "content": SYSTEM_MESSAGE}],
                        "agentTools": [
                            {
                                "agentSelectedTool": TOOL_NAME,
                                "agentSelectedToolRequiresHumanInput": "",
                            }
                        ],
                        "agentKnowledgeDocumentStores": [],
                        "agentKnowledgeVSEmbeddings": "",
                        "agentEnableMemory": True,
                        "agentMemoryType": "windowSize",
                        "agentMemoryWindowSize": 8,
                        "agentUserMessage": "",
                        "agentReturnResponseAs": "assistantMessage",
                        "agentStructuredOutput": "",
                        "agentUpdateState": "",
                        "agentModelConfig": model_config,
                    },
                },
            },
        ],
        "edges": [
            {
                "id": "edge_start_agent",
                "source": "startAgentflow_0",
                "target": "agentAgentflow_0",
                "type": "agentFlow",
                "data": {"sourceColor": "#7EE787", "targetColor": "#4DD0E1"},
            }
        ],
    }


def get_workspace_and_credential(conn: sqlite3.Connection) -> tuple[str, str | None]:
    row = conn.execute(
        "SELECT workspaceId FROM chat_flow WHERE workspaceId IS NOT NULL LIMIT 1"
    ).fetchone()
    workspace_id = row[0] if row else str(uuid.uuid4())
    cred = conn.execute(
        "SELECT id FROM credential WHERE credentialName LIKE '%OpenAI%' OR name LIKE '%OpenAI%' LIMIT 1"
    ).fetchone()
    if not cred:
        cred = conn.execute("SELECT id FROM credential LIMIT 1").fetchone()
    return workspace_id, cred[0] if cred else None


def upsert_chatflow(conn: sqlite3.Connection, workspace_id: str, credential_id: str | None) -> None:
    flow_data = json.dumps(build_flow_data(credential_id), ensure_ascii=False)
    existing = conn.execute("SELECT id FROM chat_flow WHERE id = ?", (CHATFLOW_ID,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE chat_flow SET name = ?, flowData = ?, type = 'AGENTFLOW',
                   updatedDate = datetime('now')
            WHERE id = ?
            """,
            (AGENT_FLOW_NAME, flow_data, CHATFLOW_ID),
        )
    else:
        conn.execute(
            """
            INSERT INTO chat_flow (id, name, flowData, deployed, isPublic, type, workspaceId)
            VALUES (?, ?, ?, 0, 0, 'AGENTFLOW', ?)
            """,
            (CHATFLOW_ID, AGENT_FLOW_NAME, flow_data, workspace_id),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala agente DeepEval Regressao no Flowise")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"Banco Flowise nao encontrado: {args.db}")

    conn = sqlite3.connect(str(args.db))
    workspace_id, credential_id = get_workspace_and_credential(conn)
    tool_id = upsert_tool(conn, workspace_id)
    upsert_chatflow(conn, workspace_id, credential_id)
    conn.commit()
    conn.close()

    print(f"Tool '{TOOL_NAME}' instalada (id={tool_id})")
    print(f"Agentflow '{AGENT_FLOW_NAME}' pronto (id={CHATFLOW_ID})")
    print("Abra o Flowise -> Agentflows e publique o fluxo para obter URL de prediction.")
    print(f"Prediction URL (apos deploy): http://localhost:3000/api/v1/prediction/{CHATFLOW_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
