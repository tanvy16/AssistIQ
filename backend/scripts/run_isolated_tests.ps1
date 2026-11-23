<#
.SYNOPSIS
  Run the FULL backend test suite against a disposable local PostgreSQL in Docker.

.DESCRIPTION
  Never touches the shared Neon database. The script:
    1. starts (or reuses) a Docker container "assistiq-isolated-test-pg" bound to
       127.0.0.1:55433 with a random throwaway password,
    2. points DATABASE_URL at it via process environment variables only
       (backend/.env is NOT read for the database and is never modified),
    3. runs `alembic upgrade head` on that container, then pytest.
  LLM calls are pointed at an unroutable port so no Ollama generation happens.

  tests/conftest.py additionally skips every DB-backed test unless DATABASE_URL
  is a loopback database, so an accidental `pytest` against Neon cannot write.

.EXAMPLE
  cd backend
  .\scripts\run_isolated_tests.ps1                  # full suite
  .\scripts\run_isolated_tests.ps1 tests/test_security_mfa.py -q
  .\scripts\run_isolated_tests.ps1 -RemoveContainer # delete the test container afterwards
#>
param(
    [switch]$RemoveContainer,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$PytestArgs
)

$ErrorActionPreference = "Stop"
$container = "assistiq-isolated-test-pg"
$port = 55433
$backend = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required for isolated tests (Docker Desktop must be running)."
}

$existing = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
if (-not $existing) {
    $bytes = New-Object byte[] 18
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $password = ([Convert]::ToBase64String($bytes) -replace '[^A-Za-z0-9]', 'x')
    docker run -d --name $container -e POSTGRES_USER=assistiq -e "POSTGRES_PASSWORD=$password" `
        -e POSTGRES_DB=assistiq_test -p "127.0.0.1:${port}:5432" postgres:16 | Out-Null
} else {
    docker start $container | Out-Null
    $envLines = docker inspect -f "{{range .Config.Env}}{{println .}}{{end}}" $container
    $password = ($envLines | Where-Object { $_ -like "POSTGRES_PASSWORD=*" }) -replace '^POSTGRES_PASSWORD=', ''
}

for ($i = 0; $i -lt 30; $i++) {
    docker exec $container pg_isready -U assistiq -h 127.0.0.1 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 1
}

$env:APP_ENV = "test"
$env:DATABASE_URL = "postgresql+asyncpg://assistiq:${password}@127.0.0.1:${port}/assistiq_test"
$env:JWT_SECRET_KEY = "isolated-test-jwt-secret-key-0123456789abcdef"
$env:LLM_PROVIDER = "ollama"
$env:LLM_BASE_URL = "http://127.0.0.1:9/v1"
$env:LLM_DEFAULT_MODEL = "llama3.2:latest"
$env:CHROMA_PERSIST_DIR = Join-Path ([System.IO.Path]::GetTempPath()) "assistiq-isolated-chroma"
$env:SEED_EMPLOYEE_EMAIL = ""; $env:SEED_AGENT_EMAIL = ""; $env:SEED_ADMIN_EMAIL = ""

Push-Location $backend
try {
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "alembic upgrade failed" }
    if (-not $PytestArgs) { $PytestArgs = @("-q") }
    & $python -m pytest -p no:cacheprovider @PytestArgs
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    if ($RemoveContainer) { docker rm -f $container | Out-Null }
}
exit $code
