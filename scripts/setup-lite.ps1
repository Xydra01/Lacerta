# Build Lacerta's lite Ollama model (Qwen3.5 4B, 8k context) on Windows.
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts/setup-lite.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Error "ollama not found. Install from https://ollama.com, start the app, then re-run."
}

try {
    ollama list | Out-Null
} catch {
    Write-Error "Ollama is installed but not responding. Start Ollama, then re-run."
}

$Base = if ($env:LACERTA_OLLAMA_BASE) { $env:LACERTA_OLLAMA_BASE } else { "qwen3.5:4b" }
# Full tag so this does not replace lacerta:latest (the 9B full profile).
$Tag = if ($env:LACERTA_LITE_TAG) { $env:LACERTA_LITE_TAG } else { "lacerta:lite" }

Write-Host "Pulling base model: $Base"
ollama pull $Base

Write-Host "Creating $Tag from Modelfile.lite (lite / 4B / 8k, all platforms)"
ollama create $Tag -f (Join-Path $RepoRoot "Modelfile.lite")

Write-Host ""
Write-Host "Done. Point .env at the lite profile:"
Write-Host "  copy .env.lite.example .env"
Write-Host "  python -m lacerta.gui"
ollama list
