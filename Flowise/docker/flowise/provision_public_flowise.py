"""
Provisiona e testa a API publica do Flowise para o Streamlit Cloud.

Uso (na pasta docker/):
  python flowise/provision_public_flowise.py --base-url https://seu-flowise.onrender.com
  python flowise/provision_public_flowise.py --base-url https://xxx.ngrok-free.app --email u@x.com --password secret

Gera/atualiza streamlit/.streamlit/cloud-secrets.toml
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

from agent_config import AGENT_FLOW_NAME, CHATFLOW_ID, build_flow_data, prediction_url

STREAMLIT_DIR = Path(__file__).resolve().parents[1] / "streamlit"
CLOUD_SECRETS_PATH = STREAMLIT_DIR / ".streamlit" / "cloud-secrets.toml"


def _normalize_base(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = f"https://{url}"
    return url


def wait_for_ping(base_url: str, timeout_sec: int = 120) -> None:
    deadline = time.time() + timeout_sec
    ping = f"{base_url}/api/v1/ping"
    while time.time() < deadline:
        try:
            r = requests.get(ping, timeout=10)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise TimeoutError(f"Flowise nao respondeu em {ping} dentro de {timeout_sec}s")


def login(session: requests.Session, base_url: str, email: str, password: str) -> None:
    r = session.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Login falhou ({r.status_code}): {r.text[:300]}")


def register(session: requests.Session, base_url: str, email: str, password: str, name: str) -> None:
    r = session.post(
        f"{base_url}/api/v1/account/register",
        json={
            "user": {
                "email": email,
                "name": name,
                "credential": password,
            }
        },
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Registro falhou ({r.status_code}): {r.text[:300]}")


def upsert_agentflow(session: requests.Session, base_url: str) -> None:
    payload = {
        "id": CHATFLOW_ID,
        "name": AGENT_FLOW_NAME,
        "flowData": json.dumps(build_flow_data(None, cloud=True), ensure_ascii=False),
        "deployed": True,
        "isPublic": False,
        "type": "AGENTFLOW",
    }
    existing = session.get(f"{base_url}/api/v1/chatflows/{CHATFLOW_ID}", timeout=30)
    if existing.status_code == 200:
        r = session.put(f"{base_url}/api/v1/chatflows/{CHATFLOW_ID}", json=payload, timeout=60)
    else:
        r = session.post(f"{base_url}/api/v1/chatflows", json=payload, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Salvar agentflow falhou ({r.status_code}): {r.text[:400]}")


def test_prediction(api_url: str, token: str) -> str:
    r = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "O que e lote minimo de compra?", "streaming": False},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    text = data.get("text") or data.get("answer") or str(data)
    return str(text)[:200]


def write_cloud_secrets(api_url: str, token: str) -> None:
    lines = [
        "# Gerado por provision_public_flowise.py - cole no Streamlit Cloud (Settings > Secrets)",
        "",
        f'FLOWISE_API_URL = "{api_url}"',
        f'FLOWISE_API_TOKEN = "{token}"',
        'CHROMA_ENABLED = "0"',
        'REQUEST_CONNECT_TIMEOUT_SECONDS = "15"',
        'REQUEST_READ_TIMEOUT_SECONDS = "120"',
        "",
    ]
    CLOUD_SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLOUD_SECRETS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Provisiona API publica Flowise para Streamlit Cloud")
    parser.add_argument("--base-url", required=True, help="URL publica do Flowise (HTTPS)")
    parser.add_argument("--email", help="Email admin Flowise (para criar/atualizar agentflow)")
    parser.add_argument("--password", help="Senha admin Flowise")
    parser.add_argument("--name", default="Admin Lumina", help="Nome no registro")
    parser.add_argument("--token", default="local-dev", help="Bearer token (se chatflow sem API key)")
    parser.add_argument("--skip-provision", action="store_true", help="So testa API e gera secrets")
    parser.add_argument("--register", action="store_true", help="Registrar conta antes do login")
    args = parser.parse_args()

    base_url = _normalize_base(args.base_url)
    api_url = prediction_url(base_url)

    print(f"Aguardando Flowise em {base_url} ...")
    wait_for_ping(base_url)

    if not args.skip_provision:
        if not args.email or not args.password:
            print("AVISO: --email e --password ausentes; pulando import do agentflow via API.")
            print("       Importe manualmente ou reexecute com credenciais.")
        else:
            session = requests.Session()
            if args.register:
                try:
                    register(session, base_url, args.email, args.password, args.name)
                    print("Conta registrada.")
                except RuntimeError as exc:
                    print(f"Registro: {exc} (tentando login...)")
            login(session, base_url, args.email, args.password)
            print("Login OK.")
            upsert_agentflow(session, base_url)
            print(f"Agentflow '{AGENT_FLOW_NAME}' provisionado ({CHATFLOW_ID}).")

    print("Testando prediction API ...")
    try:
        preview = test_prediction(api_url, args.token)
        print(f"Resposta OK: {preview}...")
    except Exception as exc:
        print(f"AVISO: prediction falhou: {exc}")
        print("Verifique credencial OpenAI no Flowise e se o agentflow existe.")

    write_cloud_secrets(api_url, args.token)
    print(f"Secrets Streamlit: {CLOUD_SECRETS_PATH}")
    print("")
    print("Proximo passo: Streamlit Cloud -> Settings -> Secrets -> colar cloud-secrets.toml")
    print(f"FLOWISE_API_URL = {api_url}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
