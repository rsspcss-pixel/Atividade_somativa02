#Requires -Version 5.1
<#
.SYNOPSIS
    Executa avaliacao DeepEval via Docker (sem Python local).

.DESCRIPTION
    Requer:
    - Stack Docker ativo (Flowise): .\start-stack.ps1
    - LM Studio com servidor na porta 1234 e modelo nvidia/nemotron-3-nano-4b:4 (contexto maior; :2 estoura prompt do DeepEval)

.EXAMPLE
    .\run-eval.ps1

.EXAMPLE
    .\run-eval.ps1 -DryRun

.EXAMPLE
    .\run-eval.ps1 -Build
#>
[CmdletBinding()]
param(
    [switch] $Build,
    [switch] $DryRun,
    [switch] $Regression,
    [int] $Limit = 0
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
    Write-Step "Verificando LM Studio (judge local em host.docker.internal:1234)"
    try {
        $models = Invoke-RestMethod -Uri "http://localhost:1234/v1/models" -TimeoutSec 5
        $ids = @($models.data | ForEach-Object { $_.id })
        $judgeModel = "nvidia/nemotron-3-nano-4b:4"
        if ($ids -notcontains $judgeModel) {
            Write-Host "    AVISO: modelo $judgeModel nao listado; carregue no LM Studio (variante :4 = mais contexto)." -ForegroundColor Yellow
        }
        else {
            Write-Host "    OK: LM Studio respondendo com $judgeModel" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "    AVISO: LM Studio inacessivel em localhost:1234. Suba com .\start-stack.ps1" -ForegroundColor Yellow
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
    if ($DryRun) {
        $composeArgs += "-e", "DEEPEVAL_DRY_RUN=1"
        Write-Step "Modo dry-run: metricas only (actual_output = expected_output)"
    }
    if ($Regression) {
        $composeArgs += "-e", "DEEPEVAL_REGRESSION_MODE=1"
        if ($Limit -gt 0) {
            $composeArgs += "-e", "DEEPEVAL_REGRESSION_LIMIT=$Limit"
        }
        Write-Step "Modo regressao: metrica GEval + baseline"
    }

    $composeArgs += "streamlit-eval"

    Write-Step "Executando DeepEval no container streamlit-eval"
    Write-Host "    docker $($composeArgs -join ' ')" -ForegroundColor DarkGray
    & docker @composeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "streamlit-eval terminou com codigo $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Avaliacao concluida." -ForegroundColor Green
    Write-Host "Resultados (se configurado): streamlit/data/deepeval_results/" -ForegroundColor DarkGray
}
finally {
    Pop-Location
}
