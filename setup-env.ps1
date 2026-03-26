param(
  [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "backend"
$envPath = Join-Path $backendDir ".env"

if ((Test-Path $envPath) -and (-not $Force)) {
  Write-Host "backend/.env already exists. Re-run with -Force to overwrite."
  exit 1
}

function Read-Secret {
  param(
    [Parameter(Mandatory=$true)]
    [string]$Prompt
  )

  $secure = Read-Host -Prompt $Prompt -AsSecureString
  $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  }
  finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
}

$openaiApiKey = Read-Secret -Prompt "OPENAI_API_KEY (required)"
$langsmithApiKey = Read-Secret -Prompt "LANGSMITH_API_KEY (optional; press Enter to skip)"

if ([string]::IsNullOrEmpty($langsmithApiKey)) {
  $langsmithTracing = "false"
  # Avoid writing an empty key.
  $langsmithApiKeyValue = ""
} else {
  $langsmithTracing = "true"
  $langsmithApiKeyValue = $langsmithApiKey
}

$content = @"
LLM_PROVIDER=openai
# LLM_MODEL=
# ANTHROPIC_API_KEY=
# GEMINI_API_KEY=
OPENAI_API_KEY=$openaiApiKey
OPENAI_MODEL=gpt-4o-mini
LANGSMITH_API_KEY=$langsmithApiKeyValue
LANGSMITH_PROJECT=inboxpilot-ai
LANGSMITH_TRACING=$langsmithTracing
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/inboxpilot
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CONFIDENCE_THRESHOLD=0.7
MAX_MESSAGE_LENGTH=10000
"@

Set-Content -Path $envPath -Value $content -Encoding ascii
Write-Host "Wrote $envPath"

