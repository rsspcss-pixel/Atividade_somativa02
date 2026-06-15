#Requires -Version 5.1
<#
.SYNOPSIS
    Sobe o LM Studio (servidor + modelo) e o stack Docker (Flowise + Streamlit + ml-api).

.EXAMPLE
    .\start-stack.ps1

.EXAMPLE
    .\start-stack.ps1 -Build

.EXAMPLE
    .\start-stack.ps1 -SkipLmStudio
#>
[CmdletBinding()]
param(
    [string] $LmStudioModel = "google/gemma-3-4b",
    [int] $LmStudioContextLength = 8192,
    [int] $LmStudioPort = 1234,
    [switch] $SkipLmStudio,
    [switch] $Build,
    [int] $LmStudioReadyTimeoutSec = 120,
    [int] $DockerReadyTimeoutSec = 180
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

function Wait-LmStudioApi {
    param(
        [int] $Port,
        [int] $TimeoutSec
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-LmStudioApi -Port $Port) {
            return $true
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Test-LmStudioModelLoaded {
    param([string] $Model)
    $status = Invoke-Lms ps
    return ($status -match [regex]::Escape($Model))
}

function Start-LmStudioStack {
    param(
        [string] $Model,
        [int] $ContextLength,
        [int] $Port,
        [int] $ReadyTimeoutSec
    )

    Write-Step "Verificando CLI do LM Studio (lms)"
    if (-not (Get-Command lms -ErrorAction SilentlyContinue)) {
        throw "Comando 'lms' nao encontrado. Instale o LM Studio e garanta que o CLI esteja no PATH."
    }
    Write-Ok "CLI encontrado: $((Get-Command lms).Source)"

    Write-Step "Iniciando servidor LM Studio na porta $Port"
    $serverStatus = Invoke-Lms server status
    if ($serverStatus -notmatch "running on port $Port") {
        Invoke-Lms server start -p $Port | Out-Null
    }
    else {
        Write-Ok "Servidor ja estava ativo na porta $Port"
    }

    if (-not (Wait-LmStudioApi -Port $Port -TimeoutSec $ReadyTimeoutSec)) {
        throw "LM Studio nao respondeu em http://localhost:$Port/v1/models dentro de ${ReadyTimeoutSec}s."
    }
    Write-Ok "API LM Studio respondendo em http://localhost:$Port/v1/models"

    Write-Step "Carregando modelo '$Model' (contexto $ContextLength tokens)"
    if (Test-LmStudioModelLoaded -Model $Model) {
        $psStatus = Invoke-Lms ps
        if ($psStatus -notmatch "CONTEXT\s+$ContextLength\b") {
            Write-Warn "Modelo carregado com contexto diferente; recarregando com $ContextLength tokens"
            Invoke-Lms unload $Model | Out-Null
            Start-Sleep -Seconds 2
            Invoke-Lms load $Model --yes -c $ContextLength --parallel 1 --identifier $Model | Out-Null
        }
        else {
            Write-Ok "Modelo '$Model' ja estava carregado com contexto $ContextLength"
        }
    }
    else {
        Invoke-Lms load $Model --yes -c $ContextLength --parallel 1 --identifier $Model | Out-Null
        if (-not (Test-LmStudioModelLoaded -Model $Model)) {
            Write-Warn "Modelo pode ter sido carregado sob demanda; testando chat..."
            $body = @{
                model    = $Model
                messages = @(@{ role = "user"; content = "ping" })
                max_tokens = 5
                stream   = $false
            } | ConvertTo-Json -Depth 5
            try {
                $null = Invoke-RestMethod `
                    -Uri "http://localhost:$Port/v1/chat/completions" `
                    -Method Post `
                    -Body $body `
                    -ContentType "application/json" `
                    -TimeoutSec 180
                Write-Ok "Modelo respondeu ao teste de chat"
            }
            catch {
                throw "Falha ao carregar/testar o modelo '$Model': $($_.Exception.Message)"
            }
        }
        else {
            Write-Ok "Modelo '$Model' carregado"
        }
    }
}

function Invoke-DockerComposeUp {
    param([switch] $WithBuild)

    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        if ($WithBuild) {
            & docker compose up -d --build
        }
        else {
            & docker compose up -d
        }
        return $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prevErrorAction
    }
}

function Wait-HttpReady {
    param(
        [string] $Url,
        [int] $TimeoutSec
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
            # ainda subindo
        }
        Start-Sleep -Seconds 3
    }
    return $false
}

function Show-DockerComposeStatus {
    $prevErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker compose ps
    }
    finally {
        $ErrorActionPreference = $prevErrorAction
    }
}

function Start-DockerStack {
    param(
        [string] $ComposeDir,
        [switch] $WithBuild,
        [int] $ReadyTimeoutSec,
        [int] $FlowisePort,
        [int] $StreamlitPort,
        [int] $MlApiPort
    )

    Write-Step "Subindo containers Docker Compose"
    Push-Location $ComposeDir
    try {
        if (-not (Test-Path ".env")) {
            Write-Warn "Arquivo .env nao encontrado. Executando setup.ps1..."
            $setupScript = Join-Path $ComposeDir "setup.ps1"
            if (Test-Path -LiteralPath $setupScript) {
                & $setupScript
            }
        }

        $exitCode = Invoke-DockerComposeUp -WithBuild:$WithBuild
        if ($exitCode -ne 0) {
            throw "docker compose up falhou com codigo $exitCode"
        }
        Write-Ok "Containers iniciados"

        Write-Step "Aguardando servicos principais"
        $checks = @(
            @{ Name = "flowise";   Url = "http://localhost:$FlowisePort/api/v1/ping" }
            @{ Name = "ml-api";    Url = "http://localhost:$MlApiPort/health" }
            @{ Name = "streamlit"; Url = "http://localhost:$StreamlitPort/_stcore/health" }
        )
        foreach ($check in $checks) {
            $ok = Wait-HttpReady -Url $check.Url -TimeoutSec $ReadyTimeoutSec
            if ($ok) {
                Write-Ok "$($check.Name) disponivel ($($check.Url))"
            }
            else {
                Write-Warn "$($check.Name) ainda nao respondeu; verifique com: docker compose ps"
            }
        }

        Show-DockerComposeStatus
    }
    finally {
        Pop-Location
    }
}

function Read-EnvPort {
    param(
        [string] $ComposeDir,
        [string] $Name,
        [int] $Default
    )
    $envFile = Join-Path $ComposeDir ".env"
    if (-not (Test-Path $envFile)) {
        return $Default
    }
    $match = Select-String -Path $envFile -Pattern "^\s*$Name\s*=\s*(\d+)\s*$" | Select-Object -First 1
    if ($match) {
        return [int] $match.Matches[0].Groups[1].Value
    }
    return $Default
}

try {
    Write-Host ""
    Write-Host "Flowise stack - LM Studio + Docker Compose" -ForegroundColor White

    if (-not $SkipLmStudio) {
        Start-LmStudioStack -Model $LmStudioModel -ContextLength $LmStudioContextLength -Port $LmStudioPort -ReadyTimeoutSec $LmStudioReadyTimeoutSec
    }
    else {
        Write-Warn "Pulando LM Studio (-SkipLmStudio)"
    }

    $flowisePort = Read-EnvPort -ComposeDir $ScriptDir -Name "PORT" -Default 3000
    $streamlitPort = Read-EnvPort -ComposeDir $ScriptDir -Name "STREAMLIT_PORT" -Default 8502
    $mlApiPort = Read-EnvPort -ComposeDir $ScriptDir -Name "ML_API_PORT" -Default 8503

    Start-DockerStack `
        -ComposeDir $ScriptDir `
        -WithBuild:$Build `
        -ReadyTimeoutSec $DockerReadyTimeoutSec `
        -FlowisePort $flowisePort `
        -StreamlitPort $streamlitPort `
        -MlApiPort $mlApiPort

    Write-Step "Bootstrap agentflow no Flowise"
    $bootstrapScript = Join-Path $ScriptDir "bootstrap-flowise.ps1"
    if (Test-Path -LiteralPath $bootstrapScript) {
        & $bootstrapScript
    }
    else {
        Write-Warn "bootstrap-flowise.ps1 nao encontrado; pule a instalacao automatica do agentflow."
    }

    Write-Step "Pronto"
    Write-Host "    LM Studio API : http://localhost:$LmStudioPort/v1" -ForegroundColor White
    Write-Host "    Flowise       : http://localhost:$flowisePort" -ForegroundColor White
    Write-Host "    Streamlit     : http://localhost:$streamlitPort" -ForegroundColor White
    Write-Host "    ML API        : http://localhost:$mlApiPort" -ForegroundColor White
    Write-Host ""
    Write-Host "Parar stack      : .\stop-stack.ps1" -ForegroundColor DarkGray
    Write-Host "DeepEval (Docker): .\run-eval.ps1" -ForegroundColor DarkGray
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
