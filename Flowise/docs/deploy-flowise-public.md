# Deploy Flowise publico (opcional)

> **Para a entrega no Streamlit Cloud, use [deploy-streamlit-cloud.md](deploy-streamlit-cloud.md)** — o chat funciona com OpenAI direto, sem Flowise externo.

Este guia e apenas se voce quiser manter o agente **Flowise** como backend do chat (ex.: demo com ngrok ou hospedagem propria).

## Opcao A — ngrok (demo rapida)

```powershell
cd Flowise/docker
.\start-stack.ps1 -SkipLmStudio
# outro terminal:
.\expose-flowise-ngrok.ps1
# copie a URL https://....ngrok-free.app
.\deploy-flowise-public.ps1 -FlowiseUrl "https://....ngrok-free.app" -SkipProvision
```

No Streamlit Cloud, use `CHAT_BACKEND=flowise` e a URL HTTPS do ngrok em `FLOWISE_API_URL`.

## Opcao B — Render (hospedagem permanente, opcional)

Arquivos em `render.yaml` (raiz) e `Flowise/docker/render.yaml`. Nao e necessario para o deploy padrao no share.streamlit.io.

## API de prediction (quando usar Flowise)

| Item | Valor |
|------|--------|
| Endpoint | `{URL_PUBLICA}/api/v1/prediction/f92dd892-ced9-4396-863b-9675b17242fb` |
| Metodo | `POST` |
| Header | `Authorization: Bearer local-dev` |
| Body | `{"question": "...", "streaming": false}` |

## Secrets Streamlit (modo Flowise)

```toml
CHAT_BACKEND = "flowise"
FLOWISE_API_URL = "https://SUA-URL/api/v1/prediction/f92dd892-ced9-4396-863b-9675b17242fb"
FLOWISE_API_TOKEN = "local-dev"
CHROMA_ENABLED = "0"
```
