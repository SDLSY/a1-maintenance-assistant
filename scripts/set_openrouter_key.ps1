$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

$target = Join-Path (Get-Location) ".env.local"
if (-not (Test-Path -LiteralPath $target)) {
  Copy-Item -LiteralPath ".env.example" -Destination $target
}

function Read-SecretPlain([string]$Prompt) {
  $secure = Read-Host -Prompt $Prompt -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
}

function Set-EnvLine([string[]]$Lines, [string]$Name, [string]$Value) {
  $escaped = [Regex]::Escape($Name)
  $line = "$Name=$Value"
  $found = $false
  $next = foreach ($item in $Lines) {
    if ($item -match "^\s*$escaped\s*=") {
      $found = $true
      $line
    } else {
      $item
    }
  }
  if (-not $found) {
    $next += $line
  }
  return $next
}

$lines = Get-Content -LiteralPath $target -Encoding utf8
$key = Read-SecretPlain "OPENROUTER_API_KEY"
if ([string]::IsNullOrWhiteSpace($key)) {
  throw "OPENROUTER_API_KEY cannot be empty."
}

$lines = Set-EnvLine $lines "OPENROUTER_BASE_URL" "https://openrouter.ai/api/v1"
$lines = Set-EnvLine $lines "OPENROUTER_API_KEY" $key
$lines = Set-EnvLine $lines "OPENROUTER_EMBEDDING_MODEL" "qwen/qwen3-embedding-8b"
$lines = Set-EnvLine $lines "EMBEDDING_AGENT_PROVIDER" "openrouter"
$lines = Set-EnvLine $lines "EMBEDDING_AGENT_MODEL" "qwen/qwen3-embedding-8b"

Set-Content -LiteralPath $target -Value $lines -Encoding utf8
Write-Host ".env.local updated for OpenRouter embedding. No key value was printed."
