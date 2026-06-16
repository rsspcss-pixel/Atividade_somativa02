#Requires -Version 5.1
<#
.SYNOPSIS
    Gera .streamlit/secrets.toml a partir do .env local (nao commitado).

.DESCRIPTION
    Converte variaveis relevantes do .env para o formato TOML do Streamlit.
    O ficheiro gerado fica em .streamlit/secrets.toml (gitignored).

.EXAMPLE
    .\setup-secrets.ps1

.EXAMPLE
    .\setup-secrets.ps1 -EnvFile .env.example -Force
#>
[CmdletBinding()]
param(
    [string] $EnvFile = ".env",
    [string] $OutputPath = "",
    [switch] $Force,
    [switch] $Cloud
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

$SecretKeys = @(
    "CHAT_BACKEND",
    "FLOWISE_API_URL",
    "FLOWISE_API_TOKEN",
    "CHROMA_ENABLED",
    "OPENAI_API_KEY",
    "OPENAI_CHAT_MODEL",
    "OPENAI_EMBEDDING_MODEL",
    "APP_ENV",
    "GUARDRAILS_ENABLED",
    "GUARDRAILS_MAX_INPUT_CHARS",
    "GUARDRAILS_BLOCK_INJECTION",
    "GUARDRAILS_BLOCK_ON_PII",
    "GUARDRAILS_APPEND_DISCLAIMER",
    "GUARDRAILS_RATE_LIMIT",
    "GUARDRAILS_RATE_WINDOW_SECONDS",
    "GUARDRAILS_LINK_ALLOWLIST",
    "REQUEST_CONNECT_TIMEOUT_SECONDS",
    "REQUEST_READ_TIMEOUT_SECONDS",
    "CHAT_PROMPT_PREFIX"
)

function Read-DotEnv([string] $Path) {
    $result = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $result
    }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim()
        if ($value.Length -ge 2 -and $value[0] -eq $value[-1] -and $value[0] -in '"', "'") {
            $value = $value.Substring(1, $value.Length - 2)
        }
        if ($value) { $result[$key] = $value }
    }
    return $result
}

function Escape-TomlString([string] $Value) {
    return ($Value -replace '\\', '\\' -replace '"', '\"')
}

Push-Location $ScriptDir
try {
    $envPath = Join-Path $ScriptDir $EnvFile
    if (-not (Test-Path -LiteralPath $envPath)) {
        throw "Ficheiro nao encontrado: $envPath. Copie .env.example para .env e preencha os valores."
    }

    $secretsDir = Join-Path $ScriptDir ".streamlit"
    if ($OutputPath) {
        $outPath = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $ScriptDir $OutputPath }
    } elseif ($Cloud) {
        $outPath = Join-Path $secretsDir "cloud-secrets.toml"
    } else {
        $outPath = Join-Path $secretsDir "secrets.toml"
    }
    if ((Test-Path -LiteralPath $outPath) -and -not $Force) {
        Write-Host "secrets.toml ja existe. Use -Force para sobrescrever." -ForegroundColor Yellow
        return
    }

    $vars = Read-DotEnv $envPath
    if ($Cloud) {
        $vars["CHROMA_ENABLED"] = "0"
        if (-not $vars.ContainsKey("CHAT_BACKEND") -or -not $vars["CHAT_BACKEND"].Trim()) {
            $vars["CHAT_BACKEND"] = "openai"
        }
    } elseif (-not $vars.ContainsKey("CHAT_BACKEND") -or -not $vars["CHAT_BACKEND"].Trim()) {
        $vars["CHAT_BACKEND"] = "flowise"
    } elseif (-not $vars.ContainsKey("CHROMA_ENABLED")) {
        $vars["CHROMA_ENABLED"] = "0"
    }

    $backend = if ($vars.ContainsKey("CHAT_BACKEND")) { $vars["CHAT_BACKEND"].Trim().ToLower() } else { "auto" }
    if ($Cloud -and ($backend -eq "openai" -or $backend -eq "auto")) {
        $backend = "openai"
    }

    $missing = @()
    if ($backend -eq "openai") {
        if (-not $vars.ContainsKey("OPENAI_API_KEY") -or -not $vars["OPENAI_API_KEY"].Trim()) {
            $missing += "OPENAI_API_KEY"
        }
    } else {
        foreach ($required in @("FLOWISE_API_URL", "FLOWISE_API_TOKEN")) {
            if (-not $vars.ContainsKey($required) -or -not $vars[$required].Trim()) {
                $missing += $required
            }
        }
    }
    if ($missing.Count -gt 0) {
        throw "Variaveis obrigatorias em ${EnvFile}: $($missing -join ', ')"
    }

    if ($vars.ContainsKey("FLOWISE_API_TOKEN") -and $vars["FLOWISE_API_TOKEN"] -match "INSIRA_UM_CODIGO_AQUI") {
        throw "FLOWISE_API_TOKEN ainda e placeholder em ${EnvFile}. Use local-dev (dev) ou uma API key real."
    }

    New-Item -ItemType Directory -Force -Path $secretsDir | Out-Null

    $lines = @(
        "# Gerado por setup-secrets.ps1 - NAO commitar",
        "# $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        ""
    )
    foreach ($key in $SecretKeys) {
        if (-not $vars.ContainsKey($key)) { continue }
        $value = $vars[$key].Trim()
        if (-not $value) { continue }
        $lines += "$key = `"$(Escape-TomlString $value)`""
    }

    $lines | Set-Content -LiteralPath $outPath -Encoding UTF8
    Write-Host "OK: $outPath" -ForegroundColor Green

    if ($Cloud -and $backend -eq "flowise" -and $vars["FLOWISE_API_URL"] -match "^(http://flowise|http://localhost|http://127\.0\.0\.1)") {
        Write-Host ""
        Write-Host "AVISO: FLOWISE_API_URL parece URL interna Docker." -ForegroundColor Yellow
        Write-Host "       No Streamlit Cloud prefira CHAT_BACKEND=openai + OPENAI_API_KEY." -ForegroundColor Yellow
    }
}
finally {
    Pop-Location
}
