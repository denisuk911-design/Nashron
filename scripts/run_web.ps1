param(
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000,
  [switch]$ApiOnly
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$python = (Resolve-Path ".\.venv\Scripts\python.exe").Path

if ($ApiOnly) {
  & $python -m uvicorn services.api.app:app --host 127.0.0.1 --port $ApiPort
  exit $LASTEXITCODE
}

$api = Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "services.api.app:app", "--host", "127.0.0.1", "--port", $ApiPort) -PassThru -WindowStyle Hidden
try {
  $healthUrl = "http://127.0.0.1:$ApiPort/api/health"
  $ready = $false
  1..30 | ForEach-Object {
    if ($ready) { return }
    Start-Sleep -Milliseconds 500
    try {
      $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
      if ($health.status -eq "ready") { $ready = $true }
    } catch {
      if ($api.HasExited) { throw "Luminifera API завершил запуск с кодом $($api.ExitCode)." }
    }
  }
  if (-not $ready) { throw "Luminifera API не ответил за 15 секунд: $healthUrl" }
  Write-Host "Luminifera Web: http://127.0.0.1:$WebPort/app"
  Write-Host "Luminifera API: http://127.0.0.1:$ApiPort/api/docs"
  Start-Process "http://127.0.0.1:$WebPort/app"
  & $python -m services.web_dev_server --host 127.0.0.1 --port $WebPort --api-base "http://127.0.0.1:$ApiPort"
}
finally {
  if (-not $api.HasExited) {
    Stop-Process -Id $api.Id -Force
  }
}
