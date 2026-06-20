"""
Instala o agentflow principal (Assistente de Negociacao) e as custom tools no Flowise local.

Uso (na pasta docker/):
  python flowise/install_negociacao_agent.py
  python flowise/install_negociacao_agent.py --cloud
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
    LOCAL_ATTACH_TOOLS,
    TOOL_NAMES,
    build_flow_data,
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


def clear_chatflow_api_key(conn: sqlite3.Connection) -> None:
    """Garante que o chatflow aceite FLOWISE_API_TOKEN=local-dev (sem API key vinculada)."""
    conn.execute(
        "UPDATE chat_flow SET apikeyid = NULL, updatedDate = datetime('now') WHERE id = ?",
        (CHATFLOW_ID,),
    )


def upsert_chatflow(
    conn: sqlite3.Connection,
    workspace_id: str,
    credential_id: str | None,
    *,
    cloud: bool = False,
    tool_ids: dict[str, str] | None = None,
) -> None:
    flow_data = json.dumps(
        build_flow_data(credential_id, cloud=cloud, tool_ids=tool_ids),
        ensure_ascii=False,
    )
    existing = conn.execute("SELECT id FROM chat_flow WHERE id = ?", (CHATFLOW_ID,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE chat_flow SET name = ?, flowData = ?, type = 'AGENTFLOW',
                   deployed = 1, apikeyid = NULL, updatedDate = datetime('now')
            WHERE id = ?
            """,
            (AGENT_FLOW_NAME, flow_data, CHATFLOW_ID),
        )
    else:
        conn.execute(
            """
            INSERT INTO chat_flow (id, name, flowData, deployed, isPublic, type, workspaceId, apikeyid)
            VALUES (?, ?, ?, 1, 0, 'AGENTFLOW', ?, NULL)
            """,
            (CHATFLOW_ID, AGENT_FLOW_NAME, flow_data, workspace_id),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala agentflow Assistente Negociacao no Flowise")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Perfil cloud (OpenAI gpt-4o-mini, sem tools Docker)",
    )
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(
            f"Banco Flowise nao encontrado: {args.db}\n"
            "Inicie o Flowise uma vez (docker compose up) para criar o banco em ~/.flowise/"
        )

    conn = sqlite3.connect(str(args.db))
    workspace_id, credential_id = get_workspace_and_credential(conn)
    tool_id_map: dict[str, str] = {}
    if not args.cloud and LOCAL_ATTACH_TOOLS:
        tool_id_map = {name: upsert_tool(conn, workspace_id, name) for name in TOOL_NAMES}
    upsert_chatflow(
        conn,
        workspace_id,
        credential_id if args.cloud else None,
        cloud=args.cloud,
        tool_ids=tool_id_map or None,
    )
    clear_chatflow_api_key(conn)
    conn.commit()
    conn.close()

    if tool_id_map:
        print(f"Tools instaladas: {', '.join(f'{n} ({tid})' for n, tid in tool_id_map.items())}")
    print(f"Agentflow '{AGENT_FLOW_NAME}' pronto (id={CHATFLOW_ID}, cloud={args.cloud})")
    print(f"Prediction URL: http://localhost:3000/api/v1/prediction/{CHATFLOW_ID}")
    print(f"Conhecimento: {len(build_system_message())} chars no system prompt")
    if args.cloud and not credential_id:
        print("")
        print("AVISO: Adicione credencial OpenAI no Flowise (Settings -> Credentials).")
        print("       Depois reexecute: python flowise/install_negociacao_agent.py --cloud")
    elif not args.cloud and not credential_id:
        print("")
        print("AVISO: Crie credencial OpenAI Custom apontando para LM Studio:")
        print("       Base URL: http://host.docker.internal:1234/v1  |  API Key: lm-studio")
    print("")
    print("Streamlit: use FLOWISE_API_TOKEN=local-dev se o chatflow nao tiver API key atribuida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
