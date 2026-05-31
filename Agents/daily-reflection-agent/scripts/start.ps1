$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "Starting Daily Reflection Agent..." -ForegroundColor Green
Write-Host "Make sure LM Studio is serving a loaded chat model at http://127.0.0.1:1234" -ForegroundColor DarkGreen
python .\server.py
