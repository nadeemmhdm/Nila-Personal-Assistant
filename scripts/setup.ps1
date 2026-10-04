$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install Python 3.11+ from python.org, then reopen PowerShell.' }
py -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
if (-not (Test-Path nila\static\index.html)) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22 LTS, then rerun setup.' }
    Push-Location web
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
        npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
    } finally { Pop-Location }
}
Write-Host 'Nila installed. First run: ollama pull llama3.2:1b'
Write-Host 'Launch Web UI: .\.venv\Scripts\nila.exe web'
Write-Host 'Launch chat:   .\.venv\Scripts\nila.exe'
