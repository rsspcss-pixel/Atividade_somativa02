#Requires -Version 5.1
<#
.SYNOPSIS
    Prepara e valida o deploy do app Streamlit no Streamlit Cloud.

.DESCRIPTION
    1. Auditoria de segredos no codigo
    2. Gera .streamlit/secrets.toml a partir do .env
    3. Gera cloud-secrets.toml para colar no painel do Streamlit Cloud
    4. Valida sintaxe Python e dependencias de producao
    5. Opcional: smoke test local com streamlit run

.EXAMPLE
    .\deploy-streamlit-cloud.ps1

.EXAMPLE
    .\deploy-streamlit-cloud.ps1 -SetupSecretsOnly

.EXAMPLE
    .\deploy-streamlit-cloud.ps1 -OpenCloud
#>
[CmdletBinding()]
param(
    [switch] $SetupSecretsOnly,
    [switch] $SkipAudit,
    [switch] $OpenCloud,
    [switch] $RunLocal
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$StreamlitDir = Join-Path $ScriptDir "streamlit"

function Write-Step([string] $Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-SecretLeaks([string] $Root) {
    $patterns = @(
        'sk-proj-[A-Za-z0-9_-]{30,}',
        'sk-[A-Za-z0-9]{40,}'
    )
    $extensions = @("*.py", "*.json", "*.md", "*.toml", "*.yaml", "*.yml", "*.ps1", "*.txt")
    $skipPattern = '(\\|/)\.env(\.|$)|secrets\.toml$|cloud-secrets\.toml$|secrets\.toml\.example$'
    $hits = [System.Collections.Generic.List[string]]::new()
    foreach ($ext in $extensions) {
        foreach ($file in (Get-ChildItem -Path $Root -Recurse -File -Filter $ext -ErrorAction SilentlyContinue)) {
            $rel = $file.FullName.Substring($Root.Length).TrimStart('\', '/')
            if ($rel -match $skipPattern) { continue }
            $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
            if (-not $content) { continue }
            foreach ($pattern in $patterns) {
                if ($content -match $pattern) {
                    $hits.Add("$rel ($pattern)")
                    break
                }
            }
        }
    }
    return $hits.ToArray()
}

Push-Location $ScriptDir
try {
    Write-Step "Auditoria de segredos em docker/streamlit"
    if (-not $SkipAudit) {
        $leaks = @(Test-SecretLeaks $StreamlitDir)
        if ($leaks.Length -gt 0) {
            Write-Host "FALHA: possiveis segredos no codigo:" -ForegroundColor Red
            $leaks | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
            throw "Remova segredos antes do deploy."
        }
        Write-Host "    Nenhum padrao de chave encontrado em ficheiros versionados." -ForegroundColor Green
    }

    Write-Step "Gerando secrets.toml local"
    $setupScript = Join-Path $StreamlitDir "setup-secrets.ps1"
    if (-not (Test-Path -LiteralPath $setupScript)) {
        throw "setup-secrets.ps1 nao encontrado em $StreamlitDir"
    }
    & $setupScript -Force

    Write-Step "Gerando cloud-secrets.toml (para colar no Streamlit Cloud)"
    & $setupScript -Force -Cloud -EnvFile ".env"
    $cloudSecrets = Join-Path $StreamlitDir ".streamlit\cloud-secrets.toml"
    Write-Host "    $cloudSecrets" -ForegroundColor Green

    if ($SetupSecretsOnly) {
        Write-Host ""
        Write-Host "Concluido (apenas secrets)." -ForegroundColor Green
        return
    }

    Write-Step "Validando Python"
    Push-Location $StreamlitDir
    try {
        python -m py_compile app.py config.py guardrails.py chroma_rag.py knowledge_base.py cloud_chat.py
        if ($LASTEXITCODE -ne 0) { throw "py_compile falhou." }
        Write-Host "    Sintaxe OK." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }

    Write-Step "Verificando requirements.txt de producao"
    $reqPath = Join-Path $StreamlitDir "requirements.txt"
    $req = Get-Content -LiteralPath $reqPath -Raw
    $heavy = @("chromadb", "deepeval", "fastapi", "uvicorn", "pytest")
    $foundHeavy = @($heavy | Where-Object { $req -match "(?m)^\s*$_" })
    if ($foundHeavy.Length -gt 0) {
        throw "requirements.txt ainda inclui pacotes pesados: $($foundHeavy -join ', ')"
    }
    Write-Host "    requirements.txt leve (sem chromadb/deepeval/fastapi)." -ForegroundColor Green

    Write-Step "Verificando gitignore"
    $gitignore = Join-Path $StreamlitDir ".gitignore"
    if (-not (Select-String -LiteralPath $gitignore -Pattern "secrets\.toml" -Quiet)) {
        throw ".streamlit/secrets.toml nao esta no .gitignore"
    }
    Write-Host "    secrets.toml protegido no .gitignore." -ForegroundColor Green

    Write-Step "Checklist Streamlit Cloud"
    Write-Host @"

    Repositorio GitHub
      - Main file path: Flowise/docker/streamlit/app.py
      - Branch: main (ou a sua branch de deploy)

    Secrets (Settings > Secrets) — Streamlit Cloud
      - CHAT_BACKEND = openai
      - OPENAI_API_KEY = sk-... (platform.openai.com)
      - OPENAI_CHAT_MODEL = gpt-4o-mini
      - CHROMA_ENABLED = 0

    Modelo: docker/streamlit/.streamlit/secrets.toml.example
      - Ou cloud-secrets.toml gerado por setup-secrets.ps1 -Cloud

    Apos o deploy
      - Teste o chat na aba principal
      - Analytics e ML funcionam sem servicos extra no Cloud

"@ -ForegroundColor White

    if ($OpenCloud) {
        Start-Process "https://share.streamlit.io/"
        if (Test-Path -LiteralPath $cloudSecrets) {
            Start-Process notepad $cloudSecrets
        }
    }

    if ($RunLocal) {
        Write-Step "Smoke test local (Ctrl+C para parar)"
        Push-Location $StreamlitDir
        try {
            streamlit run app.py --server.headless true
        }
        finally {
            Pop-Location
        }
    }

    Write-Host ""
    Write-Host "Deploy preparado com sucesso." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
