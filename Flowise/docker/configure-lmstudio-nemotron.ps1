#Requires -Version 5.1
<#
.SYNOPSIS
    Desativa "thinking" do Nemotron no LM Studio (menos latencia + respostas visiveis).

.EXAMPLE
    .\configure-lmstudio-nemotron.ps1
#>
[CmdletBinding()]
param(
    [string] $ModelYaml = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $ModelYaml) {
    $ModelYaml = Join-Path $env:USERPROFILE ".lmstudio\hub\models\nvidia\nemotron-3-nano-4b\model.yaml"
}

if (-not (Test-Path -LiteralPath $ModelYaml)) {
    Write-Host "AVISO: model.yaml do Nemotron nao encontrado em $ModelYaml" -ForegroundColor Yellow
    exit 0
}

$content = Get-Content -LiteralPath $ModelYaml -Raw -Encoding UTF8
if ($content -match "defaultValue:\s*false" -and $content -match "enableThinking") {
    Write-Host "Nemotron ja configurado sem thinking (defaultValue: false)." -ForegroundColor Green
    exit 0
}

$updated = $content -replace "(key:\s*enableThinking[\s\S]*?defaultValue:\s*)true", '$1false'
if ($updated -eq $content) {
    Write-Host "AVISO: Nao foi possivel ajustar enableThinking em $ModelYaml" -ForegroundColor Yellow
    exit 0
}

Set-Content -LiteralPath $ModelYaml -Value $updated -Encoding UTF8 -NoNewline
Write-Host "Nemotron: thinking desativado por padrao em $ModelYaml" -ForegroundColor Green
Write-Host "Recarregue o modelo (start-stack.ps1 ou lms unload/load)." -ForegroundColor DarkGray
