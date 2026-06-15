"""Aguarda Flowise e instala agentflow cloud no SQLite persistente."""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

import requests

BOOTSTRAP_DIR = Path(__file__).resolve().parent
if str(BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_DIR))

from agent_config import CHATFLOW_ID  # noqa: E402
from install_negociacao_agent import main as install_main  # noqa: E402

PORT = os.getenv("PORT", "3000")
HOST = os.getenv("HOST", "127.0.0.1")
DB_DIR = Path(os.getenv("DATABASE_PATH", "/root/.flowise"))
DB_PATH = DB_DIR / "database.sqlite"
PING = f"http://{HOST}:{PORT}/api/v1/ping"


def wait_flowise(timeout_sec: int = 180) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = requests.get(PING, timeout=5)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    print(f"AVISO: timeout aguardando {PING}", flush=True)


def db_has_chatflow() -> bool:
    if not DB_PATH.is_file():
        return False
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute("SELECT id FROM chat_flow WHERE id = ?", (CHATFLOW_ID,)).fetchone()
    conn.close()
    return row is not None


def main() -> int:
    wait_flowise()
    if db_has_chatflow():
        print(f"Agentflow {CHATFLOW_ID} ja existe; bootstrap ignorado.", flush=True)
        return 0
    # Flowise cria o banco apos primeiro ping; aguardar arquivo
    for _ in range(30):
        if DB_PATH.is_file():
            break
        time.sleep(2)
    if not DB_PATH.is_file():
        print(f"AVISO: banco nao encontrado em {DB_PATH}", flush=True)
        return 0
    os.environ.setdefault("FLOWISE_CLOUD", "1")
    sys.argv = ["install_negociacao_agent.py", "--db", str(DB_PATH), "--cloud"]
    install_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
