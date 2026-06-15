#Requires -Version 5.1
<#
.SYNOPSIS
    Prepara arquivos .env locais para Docker + Streamlit (primeira execucao).

.EXAMPLE
    .\setup.ps1
#>
[CmdletBinding()]
param(
    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
$StreamlitDir = Join-Path $ScriptDir "streamlit"

function Copy-EnvIfMissing([string] $Example, [string] $Target, [switch] $Overwrite) {
    if ((Test-Path -LiteralPath $Target) -and -not $Overwrite) {
        Write-Host "    Ja existe: $Target" -ForegroundColor DarkGray
        return $false
    }
    if (-not (Test-Path -LiteralPath $Example)) {
        throw "Exemplo nao encontrado: $Example"
    }
    Copy-Item -LiteralPath $Example -Destination $Target -Force
    Write-Host "    Criado: $Target" -ForegroundColor Green
    return $true
}

function Set-StreamlitDevToken([string] $EnvPath) {
    $content = Get-Content -LiteralPath $EnvPath -Raw -Encoding UTF8
    if ($content -match 'FLOWISE_API_TOKEN="INSIRA_UM_CODIGO_AQUI"') {
        $content = $content -replace 'FLOWISE_API_TOKEN="INSIRA_UM_CODIGO_AQUI"', 'FLOWISE_API_TOKEN="local-dev"'
        Set-Content -LiteralPath $EnvPath -Value $content -Encoding UTF8 -NoNewline
        Write-Host "    FLOWISE_API_TOKEN=local-dev (dev local sem API key no chatflow)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Setup Flowise + Streamlit" -ForegroundColor Cyan
Write-Host ""

Push-Location $ScriptDir
try {
    Write-Host "==> Arquivos de ambiente" -ForegroundColor Cyan
    $dockerCreated = Copy-EnvIfMissing (Join-Path $ScriptDir ".env.example") (Join-Path $ScriptDir ".env") -Overwrite:$Force
    $streamlitCreated = Copy-EnvIfMissing (Join-Path $StreamlitDir ".env.example") (Join-Path $StreamlitDir ".env") -Overwrite:$Force

    $streamlitEnv = Join-Path $StreamlitDir ".env"
    if ($streamlitCreated -or $Force) {
        Set-StreamlitDevToken $streamlitEnv
    }

    Write-Host ""
    Write-Host "==> Proximos passos" -ForegroundColor Cyan
    Write-Host @"

    1. Suba o stack:
         .\start-stack.ps1 -SkipLmStudio   # sem LM Studio (so testar UI)
         .\start-stack.ps1                 # com LM Studio (chat completo)

    2. Acesse:
         Flowise   -> http://localhost:3000
         Streamlit -> http://localhost:8502

    3. Se o chat nao responder, configure credencial OpenAI no Flowise:
         Base URL: http://host.docker.internal:1234/v1
         API Key : lm-studio

    4. Streamlit Cloud (deploy):
         cd docker && .\deploy-streamlit-cloud.ps1
         Main file path: Flowise/docker/streamlit/app.py

"@ -ForegroundColor White
}
finally {
    Pop-Location
}
