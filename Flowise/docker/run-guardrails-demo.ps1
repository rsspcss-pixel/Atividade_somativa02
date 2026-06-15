#Requires -Version 5.1
<#
.SYNOPSIS
    Demonstracao dos guardrails (antes/depois) via Docker — sem Python local.

.DESCRIPTION
    Executa test_guardrails.py e guardrails_demo.py no container e grava
    docs/guardrails-demo.md no repositorio.

.EXAMPLE
    .\run-guardrails-demo.ps1

.EXAMPLE
    .\run-guardrails-demo.ps1 -Build
#>
[CmdletBinding()]
param(
    [switch] $Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}

function Write-Step([string] $Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Push-Location $ScriptDir
try {
    $composeArgs = @("compose", "--profile", "guardrails", "run", "--rm", "--no-deps")
    if ($Build) {
        $composeArgs += "--build"
    }
    $composeArgs += "streamlit-guardrails"

    Write-Step "Executando guardrails no Docker (nao precisa do stack Flowise ligado)"
    Write-Host "    docker $($composeArgs -join ' ')" -ForegroundColor DarkGray
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "streamlit-guardrails terminou com codigo $LASTEXITCODE"
    }

    $report = Join-Path (Split-Path $ScriptDir -Parent) "docs\guardrails-demo.md"
    Write-Host ""
    Write-Host "Concluido." -ForegroundColor Green
    Write-Host "Relatorio: $report" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Equivalente manual:" -ForegroundColor DarkGray
    Write-Host "  docker compose --profile guardrails run --rm --no-deps streamlit-guardrails" -ForegroundColor DarkGray
}
finally {
    Pop-Location
}
