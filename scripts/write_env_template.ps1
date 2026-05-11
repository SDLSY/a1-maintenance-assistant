$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

if (Test-Path -LiteralPath ".env.local") {
  Write-Host ".env.local already exists. Not overwriting."
  exit 0
}

Copy-Item -LiteralPath ".env.example" -Destination ".env.local"
Write-Host "Created .env.local from .env.example. Fill in keys locally; do not paste keys in chat."

