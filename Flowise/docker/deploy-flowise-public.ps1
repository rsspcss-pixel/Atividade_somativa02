#Requires -Version 5.1
<#
.SYNOPSIS
    Guia e scripts para expor Flowise publicamente (Render ou ngrok) e configurar Streamlit Cloud.

.EXAMPLE
    .\deploy-flowise-public.ps1

.EXAMPLE
    .\deploy-flowise-public.ps1 -FlowiseUrl "https://flowise-lumina.onrender.com" -Email "admin@lumina.demo" -Password "SenhaForte123!"
#>
[CmdletBinding()]
param(
    [string] $FlowiseUrl = "",
    [string] $Email = "",
    [string] $Password = "",
    [switch] $Register,
    [switch] $SkipProvision,
    [switch] $OpenRender
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..\..")

Write-Host ""
Write-Host "Flowise publico + Streamlit Cloud" -ForegroundColor Cyan
Write-Host ""

Write-Host "==> 1. Deploy no Render (recomendado)" -ForegroundColor Cyan
Write-Host @"

  a) Acesse https://dashboard.render.com -> New -> Blueprint
  b) Conecte o repo: rsspcss-pixel/Atividade_somativa02
  c) Render detecta render.yaml na raiz do repo
  d) Apos deploy, anote a URL: https://flowise-lumina.onrender.com (exemplo)

  e) Abra a URL -> crie conta admin -> Credentials -> OpenAI API
     (cole sua OPENAI_API_KEY para gpt-4o-mini)

"@ -ForegroundColor White

Write-Host "==> 2. Tunel rapido (ngrok) — demo local" -ForegroundColor Cyan
Write-Host "     Suba o stack: .\start-stack.ps1 -SkipLmStudio" -ForegroundColor DarkGray
Write-Host "     Em outro terminal: .\expose-flowise-ngrok.ps1" -ForegroundColor DarkGray
Write-Host ""

if ($OpenRender) {
    Start-Process "https://dashboard.render.com/blueprints"
}

if ($FlowiseUrl) {
    Write-Host "==> 3. Provisionar agentflow + gerar secrets Streamlit" -ForegroundColor Cyan
    Push-Location $ScriptDir
    try {
        $args = @(
            "flowise/provision_public_flowise.py",
            "--base-url", $FlowiseUrl
        )
        if ($Email) { $args += @("--email", $Email) }
        if ($Password) { $args += @("--password", $Password) }
        if ($Register) { $args += "--register" }
        if ($SkipProvision) { $args += "--skip-provision" }
        python @args
        if ($LASTEXITCODE -ne 0) { throw "provision_public_flowise.py falhou." }

        $secrets = Join-Path $ScriptDir "streamlit\.streamlit\cloud-secrets.toml"
        Write-Host ""
        Write-Host "Cole em https://share.streamlit.io -> seu app -> Settings -> Secrets" -ForegroundColor Green
        Write-Host "Arquivo: $secrets" -ForegroundColor Green
        if (Test-Path $secrets) { Start-Process notepad $secrets }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "==> 3. Depois do deploy, execute:" -ForegroundColor Cyan
    Write-Host @"

  cd Flowise/docker
  .\deploy-flowise-public.ps1 `
    -FlowiseUrl "https://SUA-URL.onrender.com" `
    -Email "seu@email.com" `
    -Password "sua-senha" `
    -Register

"@ -ForegroundColor White
}

Write-Host ""
Write-Host "Streamlit Cloud: Main file path = Flowise/docker/streamlit/app.py" -ForegroundColor Yellow
Write-Host ""
