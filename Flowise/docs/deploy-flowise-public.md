# Deploy Flowise publico para Streamlit Cloud

O Streamlit Cloud **nao alcanca** `localhost` nem `http://flowise:3000`. E necessario um Flowise com **URL HTTPS publica**.

## Opcao A — Render (recomendado, permanente)

1. Acesse [Render Blueprints](https://dashboard.render.com/blueprints)
2. Conecte o repositorio `Atividade_somativa02`
3. O arquivo [`render.yaml`](../../../render.yaml) na raiz cria o servico `flowise-lumina`
4. Apos o deploy, abra a URL (ex.: `https://flowise-lumina.onrender.com`)
5. Crie a conta admin e adicione credencial **OpenAI API** (modelo `gpt-4o-mini`)
6. Provisione o agentflow e gere secrets:

```powershell
cd Flowise/docker
.\deploy-flowise-public.ps1 `
  -FlowiseUrl "https://flowise-lumina.onrender.com" `
  -Email "admin@lumina.demo" `
  -Password "SuaSenhaForte!" `
  -Register
```

7. Cole o conteudo de `streamlit/.streamlit/cloud-secrets.toml` no **Streamlit Cloud → Settings → Secrets**
8. Streamlit: **Main file path** = `Flowise/docker/streamlit/app.py`

## Opcao B — ngrok (demo rapida)

```powershell
cd Flowise/docker
.\start-stack.ps1 -SkipLmStudio
# outro terminal:
.\expose-flowise-ngrok.ps1
# copie a URL https://....ngrok-free.app
.\deploy-flowise-public.ps1 -FlowiseUrl "https://....ngrok-free.app" -SkipProvision
```

## API de prediction

| Item | Valor |
|------|--------|
| Endpoint | `{URL_PUBLICA}/api/v1/prediction/f92dd892-ced9-4396-863b-9675b17242fb` |
| Metodo | `POST` |
| Header | `Authorization: Bearer local-dev` (se chatflow sem API key) |
| Body | `{"question": "...", "streaming": false}` |
| Health | `{URL_PUBLICA}/api/v1/ping` |

## Variaveis Streamlit Cloud (Secrets)

```toml
FLOWISE_API_URL = "https://flowise-lumina.onrender.com/api/v1/prediction/f92dd892-ced9-4396-863b-9675b17242fb"
FLOWISE_API_TOKEN = "local-dev"
CHROMA_ENABLED = "0"
REQUEST_CONNECT_TIMEOUT_SECONDS = "15"
REQUEST_READ_TIMEOUT_SECONDS = "120"
```

## Troubleshooting

| Problema | Solucao |
|----------|---------|
| Prediction 401 | Verifique token ou API key do chatflow no Flowise |
| Resposta vazia | Adicione credencial OpenAI no Flowise e reprovisione |
| Render dorme (free) | Primeira requisicao pode levar ~30s (cold start) |
| Tools ML nao funcionam | No cloud o agente usa conhecimento embutido; ML/DuckDB ficam no Streamlit |

## Arquivos relacionados

- `Dockerfile.flowise-cloud` — imagem Render com bootstrap automatico
- `flowise/provision_public_flowise.py` — import agentflow + gera secrets
- `flowise/install_negociacao_agent.py --cloud` — perfil OpenAI sem LM Studio
