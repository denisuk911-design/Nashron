param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
& .\.venv\Scripts\python.exe -m uvicorn services.api.app:app --host 127.0.0.1 --port $Port
