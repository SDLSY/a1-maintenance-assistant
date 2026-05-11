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

$provider = Read-Host "ACTIVE_MODEL_PROVIDER (local/openai/opencode/codex/spatialai; recommended codex)"
if ([string]::IsNullOrWhiteSpace($provider)) { $provider = "codex" }
$lines = Set-EnvLine $lines "ACTIVE_MODEL_PROVIDER" $provider

$openaiKey = Read-SecretPlain "OPENAI_API_KEY (leave empty to skip)"
if (-not [string]::IsNullOrWhiteSpace($openaiKey)) {
  $lines = Set-EnvLine $lines "OPENAI_API_KEY" $openaiKey
  $lines = Set-EnvLine $lines "CODEX_API_KEY" $openaiKey
}

$opencodeKey = Read-SecretPlain "OPENCODE_API_KEY (leave empty to skip)"
if (-not [string]::IsNullOrWhiteSpace($opencodeKey)) {
  $lines = Set-EnvLine $lines "OPENCODE_API_KEY" $opencodeKey
}

$anthropicKey = Read-SecretPlain "ANTHROPIC_AUTH_TOKEN (leave empty to skip)"
if (-not [string]::IsNullOrWhiteSpace($anthropicKey)) {
  $lines = Set-EnvLine $lines "ANTHROPIC_AUTH_TOKEN" $anthropicKey
}

$anthropicBase = Read-Host "ANTHROPIC_BASE_URL (default https://spatialai.vip)"
if ([string]::IsNullOrWhiteSpace($anthropicBase)) { $anthropicBase = "https://spatialai.vip" }
$lines = Set-EnvLine $lines "ANTHROPIC_BASE_URL" $anthropicBase

$opencodeBase = Read-Host "OPENCODE_BASE_URL (default https://opencode.ai/zen/go/v1)"
if ([string]::IsNullOrWhiteSpace($opencodeBase)) { $opencodeBase = "https://opencode.ai/zen/go/v1" }
$lines = Set-EnvLine $lines "OPENCODE_BASE_URL" $opencodeBase

$lines = Set-EnvLine $lines "ANTHROPIC_MODEL" "claude-opus-4-6"
$lines = Set-EnvLine $lines "OPENAI_BASE_URL" "https://spatialai.vip/v1"
$lines = Set-EnvLine $lines "OPENAI_TEXT_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "OPENAI_VISION_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "CODEX_BASE_URL" "https://spatialai.vip/v1"
$lines = Set-EnvLine $lines "CODEX_TEXT_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "CODEX_VISION_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "OPENCODE_TEXT_MODEL" "qwen3.6-plus"
$lines = Set-EnvLine $lines "OPENCODE_VISION_MODEL" "mimo-v2-omni"
$lines = Set-EnvLine $lines "TEXT_AGENT_PROVIDER" "codex"
$lines = Set-EnvLine $lines "TEXT_AGENT_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "VISION_AGENT_PROVIDER" "codex"
$lines = Set-EnvLine $lines "VISION_AGENT_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "EMBEDDING_AGENT_PROVIDER" "local"
$lines = Set-EnvLine $lines "EMBEDDING_AGENT_MODEL" "local-hash-embedding-v1"
$lines = Set-EnvLine $lines "COMPLIANCE_AGENT_PROVIDER" "codex"
$lines = Set-EnvLine $lines "COMPLIANCE_AGENT_MODEL" "gpt-5.5"
$lines = Set-EnvLine $lines "KNOWLEDGE_AGENT_PROVIDER" "codex"
$lines = Set-EnvLine $lines "KNOWLEDGE_AGENT_MODEL" "gpt-5.5"

Set-Content -LiteralPath $target -Value $lines -Encoding utf8
Write-Host ".env.local updated. No key values were printed."
