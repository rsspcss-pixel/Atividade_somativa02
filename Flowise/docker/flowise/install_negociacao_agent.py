"""
Instala o agentflow principal (Assistente de Negociacao) e as custom tools no Flowise local.

Uso (na pasta docker/):
  python flowise/install_negociacao_agent.py
  python flowise/install_negociacao_agent.py --db C:/Users/ramon/.flowise/database.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from pathlib import Path

from agent_config import (
    AGENT_FLOW_NAME,
    CHATFLOW_ID,
    DEFAULT_CHAT_MODEL,
    MAX_TOKENS,
    MEMORY_WINDOW,
    TEMPERATURE,
    TOOL_NAMES,
    build_system_message,
)

DEFAULT_DB = Path.home() / ".flowise" / "database.sqlite"
TOOLS_DIR = Path(__file__).resolve().parent / "tools"


def load_tool_spec(name: str) -> dict:
    path = TOOLS_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Tool JSON nao encontrada: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_tool(conn: sqlite3.Connection, workspace_id: str, name: str) -> str:
    spec = load_tool_spec(name)
    tool_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
    existing = conn.execute("SELECT id FROM tool WHERE name = ?", (name,)).fetchone()
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
        "modelName": DEFAULT_CHAT_MODEL,
        "temperature": TEMPERATURE,
        "streaming": True,
        "maxTokens": MAX_TOKENS,
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
                    "label": AGENT_FLOW_NAME,
                    "version": 1.1,
                    "name": "agentAgentflow",
                    "type": "Agent",
                    "inputs": {
                        "agentModel": "chatOpenAICustom",
                        "agentMessages": [{"role": "system", "content": build_system_message()}],
                        "agentTools": [
                            {
                                "agentSelectedTool": tool_name,
                                "agentSelectedToolRequiresHumanInput": "",
                            }
                            for tool_name in TOOL_NAMES
                        ],
                        "agentKnowledgeDocumentStores": [],
                        "agentKnowledgeVSEmbeddings": "",
                        "agentEnableMemory": True,
                        "agentMemoryType": "windowSize",
                        "agentMemoryWindowSize": MEMORY_WINDOW,
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
    row = conn.execute("SELECT id FROM workspace LIMIT 1").fetchone()
    if not row:
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
                   deployed = 1, updatedDate = datetime('now')
            WHERE id = ?
            """,
            (AGENT_FLOW_NAME, flow_data, CHATFLOW_ID),
        )
    else:
        conn.execute(
            """
            INSERT INTO chat_flow (id, name, flowData, deployed, isPublic, type, workspaceId)
            VALUES (?, ?, ?, 1, 0, 'AGENTFLOW', ?)
            """,
            (CHATFLOW_ID, AGENT_FLOW_NAME, flow_data, workspace_id),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala agentflow Assistente Negociacao no Flowise")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(
            f"Banco Flowise nao encontrado: {args.db}\n"
            "Inicie o Flowise uma vez (docker compose up) para criar o banco em ~/.flowise/"
        )

    conn = sqlite3.connect(str(args.db))
    workspace_id, credential_id = get_workspace_and_credential(conn)
    tool_ids = [upsert_tool(conn, workspace_id, name) for name in TOOL_NAMES]
    upsert_chatflow(conn, workspace_id, credential_id)
    conn.commit()
    conn.close()

    print(f"Tools instaladas: {', '.join(f'{n} ({tid})' for n, tid in zip(TOOL_NAMES, tool_ids))}")
    print(f"Agentflow '{AGENT_FLOW_NAME}' pronto (id={CHATFLOW_ID})")
    print(f"Prediction URL: http://localhost:3000/api/v1/prediction/{CHATFLOW_ID}")
    print(f"Conhecimento: {len(build_system_message())} chars no system prompt")
    if not credential_id:
        print("")
        print("AVISO: Nenhuma credencial OpenAI encontrada no Flowise.")
        print("       Abra http://localhost:3000 -> Credentials e crie 'OpenAI API' apontando para:")
        print("       Base URL: http://host.docker.internal:1234/v1  |  API Key: lm-studio")
    print("")
    print("Streamlit: use FLOWISE_API_TOKEN=local-dev se o chatflow nao tiver API key atribuida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
