#Requires -Version 5.1
<#
.SYNOPSIS
    Instala o agente DeepEval no Flowise e executa regressao completa.

.DESCRIPTION
    A regressao roda no container streamlit-eval (igual run-eval.ps1 -Regression),
    nao via HTTP na eval-api — evita "Response ended prematurely" em runs longos.

.EXAMPLE
    .\run-regression-agent.ps1 -InstallOnly

.EXAMPLE
    .\run-regression-agent.ps1 -Limit 3

.EXAMPLE
    .\run-regression-agent.ps1 -Limit 41 -SaveBaseline

.EXAMPLE
    .\run-regression-agent.ps1 -Build
#>
[CmdletBinding()]
param(
    [int] $Limit = 5,
    [switch] $InstallOnly,
    [switch] $SaveBaseline,
    [switch] $Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

function Write-Step([string] $Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Push-Location $ScriptDir
try {
    Write-Step "Instalando agente DeepEval Regressao no Flowise"
    python flowise/install_deepeval_agent.py
    if ($LASTEXITCODE -ne 0) { throw "install_deepeval_agent.py falhou" }

    if ($InstallOnly) {
        Write-Host "Agente instalado. Abra o Flowise e publique o fluxo 'Agente DeepEval Regressao'." -ForegroundColor Green
        return
    }

    Write-Step "Verificando LM Studio (judge local em host.docker.internal:1234)"
    try {
        $models = Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -TimeoutSec 5
        $ids = @($models.data | ForEach-Object { $_.id })
        $judgeModel = "nvidia/nemotron-3-nano-4b:4"
        if ($ids -notcontains $judgeModel) {
            Write-Host "    AVISO: modelo $judgeModel nao listado; carregue no LM Studio." -ForegroundColor Yellow
        }
        else {
            Write-Host "    OK: LM Studio respondendo" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "    AVISO: LM Studio inacessivel em localhost:1234" -ForegroundColor Yellow
    }

    Write-Step "Verificando Flowise no Docker"
    $flowise = docker compose ps flowise --format "{{.State}}" 2>$null
    if ($flowise -ne "running") {
        throw "Servico flowise nao esta running. Execute primeiro: .\start-stack.ps1"
    }
    Write-Host "    OK: flowise running" -ForegroundColor Green

    $composeArgs = @("compose", "--profile", "eval", "run", "--rm")
    if ($Build) {
        $composeArgs += "--build"
    }
    $composeArgs += "-e", "DEEPEVAL_REGRESSION_MODE=1"
    if ($Limit -gt 0) {
        $composeArgs += "-e", "DEEPEVAL_REGRESSION_LIMIT=$Limit"
    }
    if ($SaveBaseline) {
        $composeArgs += "-e", "DEEPEVAL_SAVE_BASELINE=1"
        Write-Host "    Baseline sera gravada em streamlit/data/deepeval_results/regression_baseline.json" -ForegroundColor DarkGray
    }

    $composeArgs += "streamlit-eval"

    Write-Step "Executando regressao no container (limit=$Limit, save_baseline=$SaveBaseline)"
    Write-Host "    Pode demorar varios minutos (Flowise + judge local por golden)." -ForegroundColor DarkGray
    Write-Host "    docker $($composeArgs -join ' ')" -ForegroundColor DarkGray
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "streamlit-eval terminou com codigo $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Regressao concluida." -ForegroundColor Green
    Write-Host "Relatorio: streamlit/data/deepeval_results/regression_report.json" -ForegroundColor DarkGray
    if ($SaveBaseline) {
        Write-Host "Baseline:  streamlit/data/deepeval_results/regression_baseline.json" -ForegroundColor DarkGray
    }
}
finally {
    Pop-Location
}
