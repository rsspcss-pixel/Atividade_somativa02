# Deploy no Streamlit Cloud (share.streamlit.io)

O app roda **inteiro no Streamlit Cloud**. O chat usa **OpenAI direto** com o conhecimento Lumina embutido — **nao e necessario Render, ngrok nem Flowise publico**.

## Passo a passo

### 1. GitHub

Faca push do repositorio `Atividade_somativa02` para o GitHub (branch `main`).

### 2. Criar app no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io/)
2. **New app** → conecte o repositorio
3. Configure:
   - **Main file path:** `Flowise/docker/streamlit/app.py`
   - **Branch:** `main`

### 3. Secrets (Settings → Secrets)

Cole no painel (substitua a chave OpenAI):

```toml
CHAT_BACKEND = "openai"
OPENAI_API_KEY = "sk-..."
OPENAI_CHAT_MODEL = "gpt-4o-mini"
CHROMA_ENABLED = "0"
REQUEST_CONNECT_TIMEOUT_SECONDS = "15"
REQUEST_READ_TIMEOUT_SECONDS = "120"
```

Modelo de referencia: `Flowise/docker/streamlit/.streamlit/secrets.toml.example`

### 4. Deploy

Salve os secrets e aguarde o rebuild. Teste a aba **Chat** e as abas **Analytics** / **ML** (funcionam sem servicos externos).

## Script local (opcional)

```powershell
cd Flowise/docker
.\deploy-streamlit-cloud.ps1 -OpenCloud
```

Gera `cloud-secrets.toml` a partir do `.env` (se `CHAT_BACKEND=openai` e `OPENAI_API_KEY` estiverem preenchidos).

## Modos de chat

| Modo | Onde | Secrets |
|------|------|---------|
| `openai` | Streamlit Cloud | `OPENAI_API_KEY` |
| `flowise` | Docker local | `FLOWISE_API_URL` + `FLOWISE_API_TOKEN` |
| `auto` | Detecta automaticamente | OpenAI se URL Flowise for interna |

## Troubleshooting

| Problema | Solucao |
|----------|---------|
| Chat indisponivel | Confirme `CHAT_BACKEND=openai` e `OPENAI_API_KEY` nos Secrets |
| Erro 401 OpenAI | Chave invalida ou sem credito em platform.openai.com |
| Dataset ausente | CSVs e modelo ML ja estao no repo; o app prepara na inicializacao |
| Quero Flowise no cloud | Opcional: [deploy-flowise-public.md](deploy-flowise-public.md) (Render/ngrok) |

## Desenvolvimento local (Docker + Flowise)

```powershell
cd Flowise/docker
.\setup.ps1
.\start-stack.ps1
```

Use `CHAT_BACKEND=flowise` no `.env` local (padrao com Docker Compose).
