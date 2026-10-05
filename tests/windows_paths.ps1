# Execute only the installer's path helper, never the installer itself in CI.
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot '../scripts/install.ps1'), [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$helper = $ast.Find({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-NilaBuildPaths'}, $true)
if (-not $helper) { throw 'Missing build path helper' }
Invoke-Expression $helper.Extent.Text
$reported = Get-NilaBuildPaths 'C:\Users\nadee\AppData\Local\NilaApp'
$relative = 'Lib\site-packages\_pyinstaller_hooks_contrib\stdhooks\hook-sklearn.externals.array_api_compat.dask.array.py'
if ((Join-Path $reported.Venv $relative).Length -ge 240) { throw 'Reported Windows long-path regression returned' }
$actual = Get-NilaBuildPaths (Join-Path $env:LOCALAPPDATA 'NilaPathTest')
New-Item -ItemType Directory -Force $actual.Stage | Out-Null
try {
    python -m venv $actual.Venv
    if ($LASTEXITCODE) { throw 'venv failed' }
    $python = Join-Path $actual.Venv 'Scripts/python.exe'
    & $python -m pip install --disable-pip-version-check --no-deps 'pyinstaller-hooks-contrib>=2026.7'
    if ($LASTEXITCODE) { throw 'Hook dependency install failed' }
    if (-not (Test-Path (Join-Path $actual.Venv $relative))) { throw 'Reported hook file is missing' }
} finally { Remove-Item $actual.Stage -Recurse -Force }
