#Requires -Version 5.1
<#
.SYNOPSIS
    Provisiona Flowise publico (opcional) quando CHAT_BACKEND=flowise no Streamlit Cloud.

.EXAMPLE
    .\deploy-flowise-public.ps1 -FlowiseUrl "https://....ngrok-free.app" -SkipProvision
#>
[CmdletBinding()]
param(
    [string] $FlowiseUrl = "",
    [string] $Email = "",
    [string] $Password = "",
    [switch] $Register,
    [switch] $SkipProvision
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

Write-Host ""
Write-Host "Flowise publico (opcional — deploy padrao usa OpenAI no Streamlit Cloud)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para share.streamlit.io sem Flowise externo:" -ForegroundColor Green
Write-Host "  .\deploy-streamlit-cloud.ps1 -OpenCloud" -ForegroundColor White
Write-Host ""
Write-Host "Este script e util apenas com CHAT_BACKEND=flowise + URL HTTPS (ngrok ou hospedagem propria)." -ForegroundColor DarkGray
Write-Host ""

if ($FlowiseUrl) {
    Write-Host "==> Provisionar agentflow + gerar secrets Streamlit (modo flowise)" -ForegroundColor Cyan
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
        Write-Host "Defina CHAT_BACKEND=flowise no arquivo gerado." -ForegroundColor Yellow
        Write-Host "Arquivo: $secrets" -ForegroundColor Green
        if (Test-Path $secrets) { Start-Process notepad $secrets }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Exemplo (ngrok):" -ForegroundColor Cyan
    Write-Host "  .\expose-flowise-ngrok.ps1" -ForegroundColor White
    Write-Host "  .\deploy-flowise-public.ps1 -FlowiseUrl `"https://....ngrok-free.app`" -SkipProvision" -ForegroundColor White
}

Write-Host ""
Write-Host "Streamlit Cloud: Main file path = Flowise/docker/streamlit/app.py" -ForegroundColor Yellow
Write-Host ""
