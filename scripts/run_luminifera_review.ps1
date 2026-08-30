param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "Luminifera review build"
Write-Host "Open http://127.0.0.1:$WebPort/ in the browser."
Write-Host "API docs: http://127.0.0.1:$ApiPort/api/docs"
& powershell -ExecutionPolicy Bypass -File .\scripts\run_web.ps1 -ApiPort $ApiPort -WebPort $WebPort
exit $LASTEXITCODE
