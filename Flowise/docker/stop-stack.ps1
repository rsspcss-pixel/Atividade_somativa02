#Requires -Version 5.1
<#
.SYNOPSIS
    Para o stack Docker (Flowise + Streamlit + ml-api) e o servidor LM Studio.

.EXAMPLE
    .\stop-stack.ps1

.EXAMPLE
    .\stop-stack.ps1 -Down

.EXAMPLE
    .\stop-stack.ps1 -SkipLmStudio
#>
[CmdletBinding()]
param(
    [int] $LmStudioPort = 1234,
    [switch] $SkipLmStudio,
    [switch] $UnloadModels,
    [switch] $Down
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

function Write-Ok([string] $Message) {
    Write-Host "    OK: $Message" -ForegroundColor Green
}

function Write-Warn([string] $Message) {
    Write-Host "    AVISO: $Message" -ForegroundColor Yellow
}

function Invoke-Lms {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]] $Args)

    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & lms @Args 2>&1
    }
    finally {
        $ErrorActionPreference = $prevErrorAction
    }

    $lines = @()
    foreach ($item in @($output)) {
        if ($item -is [System.Management.Automation.ErrorRecord]) {
            $lines += $item.ToString()
        }
        else {
            $lines += [string] $item
        }
    }

    $text = ($lines | Where-Object { $_ -ne "" }) -join [Environment]::NewLine
    if ($text) {
        Write-Host "    $text" -ForegroundColor DarkGray
    }
    return $text
}

function Test-LmStudioApi {
    param([int] $Port)
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:$Port/v1/models" -TimeoutSec 5
        return $true
    }
    catch {
        return $false
    }
}

function Stop-DockerStack {
    param(
        [string] $ComposeDir,
        [switch] $RemoveContainers
    )

    Write-Step "Parando containers Docker Compose"
    Push-Location $ComposeDir
    try {
        $prevErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            if ($RemoveContainers) {
                & docker compose down
            }
            else {
                & docker compose stop
            }
            $exitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $prevErrorAction
        }

        if ($exitCode -ne 0) {
            throw "docker compose $(if ($RemoveContainers) { 'down' } else { 'stop' }) falhou com codigo $exitCode"
        }

        if ($RemoveContainers) {
            Write-Ok "Containers parados e removidos (docker compose down)"
        }
        else {
            Write-Ok "Containers parados (docker compose stop)"
        }

        $prevErrorAction = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & docker compose ps
        }
        finally {
            $ErrorActionPreference = $prevErrorAction
        }
    }
    finally {
        Pop-Location
    }
}

function Stop-LmStudioStack {
    param(
        [int] $Port,
        [switch] $Unload
    )

    Write-Step "Parando LM Studio"
    if (-not (Get-Command lms -ErrorAction SilentlyContinue)) {
        Write-Warn "Comando 'lms' nao encontrado; pulando LM Studio"
        return
    }

    if ($Unload) {
        Write-Step "Descarregando modelos do LM Studio"
        $unloadStatus = Invoke-Lms unload --all
        if ($unloadStatus -match "No models are currently loaded") {
            Write-Ok "Nenhum modelo estava carregado"
        }
        elseif ($unloadStatus) {
            Write-Ok "Modelos descarregados"
        }
    }

    $serverStatus = Invoke-Lms server status
    if ($serverStatus -match "not running|stopped|No server") {
        Write-Ok "Servidor LM Studio ja estava parado"
        return
    }

    if ($serverStatus -notmatch "running on port") {
        Write-Warn "Status do servidor LM Studio desconhecido; tentando parar mesmo assim"
    }

    Invoke-Lms server stop | Out-Null

    if (Test-LmStudioApi -Port $Port) {
        Write-Warn "API ainda responde na porta $Port apos lms server stop"
    }
    else {
        Write-Ok "Servidor LM Studio parado (porta $Port)"
    }
}

try {
    Write-Host ""
    Write-Host "Flowise stack - parada" -ForegroundColor White

    Stop-DockerStack -ComposeDir $ScriptDir -RemoveContainers:$Down

    if (-not $SkipLmStudio) {
        Stop-LmStudioStack -Port $LmStudioPort -Unload:$UnloadModels
    }
    else {
        Write-Warn "Pulando LM Studio (-SkipLmStudio)"
    }

    Write-Step "Pronto"
    Write-Host "    Subir novamente: .\start-stack.ps1" -ForegroundColor DarkGray
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
