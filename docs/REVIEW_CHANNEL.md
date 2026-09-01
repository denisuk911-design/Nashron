# Luminifera Review Channel

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_luminifera_review_tunnel.ps1
```

The launcher starts the current Web service and a Cloudflare Quick Tunnel. It prints the public HTTPS URL and writes the latest URL, build SHA, and checks to `QA/REVIEW_CHANNEL/live.json`. Keep the PowerShell window open while the reviewer is inspecting the product; stop it with `Ctrl+C`.

The URL is intentionally ephemeral and changes after restart. A stable custom hostname requires a user-owned Cloudflare tunnel credential and is not created automatically. The tunnel exposes only the public Web route and API surface used by the Product UI; credentials and local admin endpoints are not forwarded.
