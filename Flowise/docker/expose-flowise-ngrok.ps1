#Requires -Version 5.1
<#
.SYNOPSIS
    Expoe o Flowise local (porta 3000) via ngrok e gera cloud-secrets.toml para Streamlit Cloud.

.EXAMPLE
    .\expose-flowise-ngrok.ps1
#>
[CmdletBinding()]
param(
    [int] $Port = 3000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "ERRO: ngrok nao encontrado. Instale: https://ngrok.com/download" -ForegroundColor Red
    Write-Host "Alternativa: deploy no Render com .\deploy-flowise-public.ps1 -OpenRender" -ForegroundColor Yellow
    exit 1
}

Write-Host "Iniciando ngrok na porta $Port ..." -ForegroundColor Cyan
Write-Host "Mantenha este terminal aberto. Em outro terminal rode o provisionamento." -ForegroundColor DarkGray

$ngrok = Start-Process -FilePath "ngrok" -ArgumentList "http", $Port -PassThru -NoNewWindow
Start-Sleep -Seconds 4

try {
    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 10
    $publicUrl = ($tunnels.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1).public_url
    if (-not $publicUrl) {
        throw "Nao foi possivel obter URL publica do ngrok."
    }
    Write-Host ""
    Write-Host "URL publica: $publicUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "Execute em outro terminal:" -ForegroundColor Cyan
    Write-Host "  cd Flowise/docker" -ForegroundColor White
    Write-Host "  .\deploy-flowise-public.ps1 -FlowiseUrl `"$publicUrl`" -SkipProvision" -ForegroundColor White
    Write-Host ""
    Wait-Process -Id $ngrok.Id
}
catch {
    if (-not $ngrok.HasExited) { Stop-Process -Id $ngrok.Id -Force -ErrorAction SilentlyContinue }
    throw
}
