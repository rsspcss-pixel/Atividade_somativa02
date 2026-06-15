#Requires -Version 5.1
<#
.SYNOPSIS
    Instala agentflows e tools no banco SQLite do Flowise apos o container subir.

.EXAMPLE
    .\bootstrap-flowise.ps1
#>
[CmdletBinding()]
param(
    [string] $DbPath = "",
    [int] $WaitSeconds = 90
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

if (-not $DbPath) {
    $DbPath = Join-Path $env:USERPROFILE ".flowise\database.sqlite"
}

function Wait-ForDatabase([string] $Path, [int] $TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $Path) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host ""
Write-Host "Bootstrap Flowise (agentflows + tools)" -ForegroundColor Cyan

if (-not (Wait-ForDatabase -Path $DbPath -TimeoutSec $WaitSeconds)) {
    Write-Host "AVISO: Banco nao encontrado em $DbPath" -ForegroundColor Yellow
    Write-Host "       Inicie o Flowise primeiro: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Push-Location $ScriptDir
try {
    $seedScript = Join-Path $ScriptDir "streamlit\seed_demo_data.py"
    if (Test-Path -LiteralPath $seedScript) {
        Write-Host "Preparando dataset + modelo ML..." -ForegroundColor Cyan
        python $seedScript --train-ml
        if ($LASTEXITCODE -ne 0) { throw "seed_demo_data.py falhou." }
    }

    python flowise/install_negociacao_agent.py --db $DbPath
    if ($LASTEXITCODE -ne 0) { throw "install_negociacao_agent.py falhou." }

    python flowise/tune_chatflow_speed.py --db $DbPath
    if ($LASTEXITCODE -ne 0) { throw "tune_chatflow_speed.py falhou." }

    Write-Host ""
    Write-Host "Bootstrap concluido." -ForegroundColor Green
    Write-Host "Chat Streamlit: http://localhost:8502" -ForegroundColor White
}
catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
