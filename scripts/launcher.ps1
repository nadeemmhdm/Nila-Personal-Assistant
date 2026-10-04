$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:LOCALAPPDATA 'NilaApp'
$Commit = (Get-Content (Join-Path $Root 'current.txt') -Raw).Trim()
if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid Nila installation pointer. Rerun installer.' }
$Binary = Join-Path $Root "versions\$Commit\nila.exe"
if (-not (Test-Path $Binary)) { throw 'Nila binary is missing. Rerun installer.' }
& $Binary @args
exit $LASTEXITCODE
