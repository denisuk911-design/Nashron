param(
  [int]$ApiPort = 18000,
  [int]$WebPort = 13000,
  [int]$ProxyPort = 12000,
  [string]$Cloudflared = "$PSScriptRoot\..\.tools\cloudflared.exe",
  [string]$ProfileDir = "$PSScriptRoot\..\.review_channel_profile",
  [string]$Manifest = "$PSScriptRoot\..\QA\REVIEW_CHANNEL\live.json"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$cloudflared = (Resolve-Path $Cloudflared).Path
$runWeb = (Resolve-Path (Join-Path $PSScriptRoot "run_web.ps1")).Path
$python = (Resolve-Path (Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe")).Path
$proxyScript = (Resolve-Path (Join-Path $PSScriptRoot "review_proxy.py")).Path
$commit = (& git rev-parse HEAD).Trim()
$env:GIT_COMMIT = $commit
$profilePath = Resolve-Path $ProfileDir -ErrorAction SilentlyContinue
if ($profilePath) { $env:TEAM2050_HOME = $profilePath.Path } else { New-Item -ItemType Directory -Force $ProfileDir | Out-Null; $env:TEAM2050_HOME = (Resolve-Path $ProfileDir).Path }
$manifestPath = [IO.Path]::GetFullPath($Manifest)
New-Item -ItemType Directory -Force (Split-Path $manifestPath) | Out-Null
$tunnelOut = Join-Path $root ".tmp-review-tunnel.out"
$tunnelErr = Join-Path $root ".tmp-review-tunnel.err"
$serviceOut = Join-Path $root ".tmp-review-service.out"
$serviceErr = Join-Path $root ".tmp-review-service.err"
Remove-Item $tunnelOut,$tunnelErr,$serviceOut,$serviceErr -Force -ErrorAction SilentlyContinue
$service = $null
$proxy = $null
$tunnel = $null
try {
  $service = Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$runWeb`"","-ApiPort",$ApiPort,"-WebPort",$WebPort) -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput $serviceOut -RedirectStandardError $serviceErr
  $health = "http://127.0.0.1:$ApiPort/api/health"
  $ready = $false
  1..60 | ForEach-Object {
    if ($ready) { return }
    Start-Sleep -Milliseconds 500
    try { if ((Invoke-RestMethod $health -TimeoutSec 2).status -eq "ready") { $ready = $true } } catch { if ($service.HasExited) { $detail=((Get-Content $serviceOut,$serviceErr -Raw -ErrorAction SilentlyContinue) -join "`n"); throw "Luminifera Web service exited with code $($service.ExitCode): $detail" } }
  }
  if (-not $ready) { throw "Local Luminifera service did not become ready: $health" }
  $proxy = Start-Process -FilePath $python -ArgumentList @($proxyScript,"--port",$ProxyPort,"--web-port",$WebPort,"--api-port",$ApiPort) -PassThru -WindowStyle Hidden
  Start-Sleep -Milliseconds 500
  $tunnel = Start-Process -FilePath $cloudflared -ArgumentList @("tunnel","--no-autoupdate","--url","http://127.0.0.1:$ProxyPort") -PassThru -WindowStyle Hidden -RedirectStandardOutput $tunnelOut -RedirectStandardError $tunnelErr
  $publicUrl = $null
  1..60 | ForEach-Object {
    if ($publicUrl) { return }
    Start-Sleep -Milliseconds 500
    $text = ((Get-Content $tunnelOut,$tunnelErr -Raw -ErrorAction SilentlyContinue) -join "`n")
    $match = [regex]::Match($text, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($match.Success) { $publicUrl = $match.Value }
    if ($tunnel.HasExited -and -not $publicUrl) { throw "cloudflared exited with code $($tunnel.ExitCode): $text" }
  }
  if (-not $publicUrl) { throw "Cloudflare Tunnel URL was not announced within 30 seconds." }
  $build = Invoke-RestMethod "$publicUrl/api/build-info" -TimeoutSec 30
  $app = Invoke-WebRequest "$publicUrl/app" -UseBasicParsing -TimeoutSec 30
  if ($app.StatusCode -ne 200) { throw "Review URL /app returned HTTP $($app.StatusCode)." }
  $record = [ordered]@{ url="$publicUrl/app"; build_info=$build; local_api=$health; checks=[ordered]@{ app=($app.StatusCode -eq 200); build_sha=($build.commit -eq $commit); health=((Invoke-RestMethod $health).status -eq "ready") }; started_at=(Get-Date).ToUniversalTime().ToString("o"); process_id=$tunnel.Id }
  $record | ConvertTo-Json -Depth 5 | Set-Content -Path $manifestPath -Encoding utf8
  Write-Host "Luminifera review URL: $publicUrl/app"
  Write-Host "Build: $($build.commit)"
  Write-Host "Keep this window running during review. Press Ctrl+C to stop."
  while (-not $tunnel.HasExited -and -not $service.HasExited) { Start-Sleep -Seconds 1 }
}
finally {
  if ($tunnel -and -not $tunnel.HasExited) { taskkill /F /T /PID $tunnel.Id 2>$null | Out-Null }
  if ($proxy -and -not $proxy.HasExited) { taskkill /F /T /PID $proxy.Id 2>$null | Out-Null }
  if ($service -and -not $service.HasExited) { taskkill /F /T /PID $service.Id 2>$null | Out-Null }
}
