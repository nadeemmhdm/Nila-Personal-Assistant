# Nila Windows installer. Source-pinned, staged, per-user installation.
[CmdletBinding()]
param([string]$Commit = '', [switch]$UpdateOnly, [switch]$NoStartup)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Repo = 'nadeemmhdm/Nila-Personal-Assistant'
$Root = Join-Path $env:LOCALAPPDATA 'NilaApp'
$Headers = @{ 'User-Agent' = 'Nila-Installer'; 'Accept' = 'application/vnd.github+json' }
New-Item -ItemType Directory -Force $Root | Out-Null
# Keep app executables writable only by this account, SYSTEM and administrators.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls.exe $Root /inheritance:r /grant:r "${identity}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not secure NilaApp directory.' }
$Lock = $null
try { $Lock = [IO.File]::Open((Join-Path $Root 'install.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
catch { throw 'Another Nila installation/update is running. Try again later.' }
function Get-NilaBuildPaths([string]$AppRoot) {
    $stagePath = Join-Path $AppRoot ('b-' + [guid]::NewGuid().ToString('N').Substring(0,8))
    $venvPath = Join-Path $stagePath 'v'
    if ($venvPath.Length -gt 120) { throw 'Nila build path is too long. Use a shorter LOCALAPPDATA directory for this installation.' }
    return @{ Stage = $stagePath; Source = (Join-Path $stagePath 's'); Venv = $venvPath }
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}
function Install-NilaRequirement([string]$Id) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        Write-Host 'Nila: bootstrapping Microsoft WinGet for the current user...'
        try {
            Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force | Out-Null
            Install-Module -Name Microsoft.WinGet.Client -Scope CurrentUser -Force -Repository PSGallery | Out-Null
            Import-Module Microsoft.WinGet.Client -Force
            Repair-WinGetPackageManager -Force -Latest
            Refresh-Path
        } catch { throw 'WinGet bootstrap failed. Install/update Microsoft App Installer from Microsoft Store, then retry.' }
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'WinGet is not available yet. Reopen PowerShell and rerun the installer.' }
    }
    & winget.exe install --id $Id --exact --source winget --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Could not install $Id (exit $LASTEXITCODE). Complete any Windows permission prompt, then retry." }
    Refresh-Path
}
function Find-Python {
    $candidates = @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { $candidates += $cmd.Source }
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            & $candidate -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
    return $null
}
try {
    Write-Host 'Nila: checking requirements...'
    $Python = Find-Python
    if (-not $Python) { Install-NilaRequirement 'Python.Python.3.12'; $Python = Find-Python }
    if (-not $Python) { throw 'Python 3.11–3.13 could not be located. Reopen PowerShell and retry.' }
    $Node = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $Node) { Install-NilaRequirement 'OpenJS.NodeJS.LTS' }
    else {
        $major = [int]((& node.exe --version).TrimStart('v').Split('.')[0])
        if ($major -lt 22) { Install-NilaRequirement 'OpenJS.NodeJS.LTS' }
    }
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'npm is not available. Reopen PowerShell and retry.' }
    if (-not $UpdateOnly -and -not (Get-Command ollama.exe -ErrorAction SilentlyContinue)) {
        $ollamaPath = Join-Path $env:LOCALAPPDATA 'Programs\Ollama'
        if (Test-Path (Join-Path $ollamaPath 'ollama.exe')) { $env:Path += ";$ollamaPath" }
        else { Install-NilaRequirement 'Ollama.Ollama'; $env:Path += ";$ollamaPath" }
    }
    if (-not $Commit) { $Commit = (Invoke-RestMethod "https://api.github.com/repos/$Repo/commits/main" -Headers $Headers).sha }
    if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'Invalid upstream commit.' }
    $Versions = Join-Path $Root 'versions'
    New-Item -ItemType Directory -Force $Versions | Out-Null
    $Target = Join-Path $Versions $Commit
    if (-not (Test-Path (Join-Path $Target 'nila.exe')) -or -not (Test-Path (Join-Path $Root 'launcher.ps1'))) {
        $BuildPaths = Get-NilaBuildPaths $Root
        $Stage = $BuildPaths.Stage
        New-Item -ItemType Directory $Stage | Out-Null
        try {
            $Zip = Join-Path $Stage 'source.zip'
            Write-Host "Nila: downloading commit $($Commit.Substring(0,8))..."
            Invoke-WebRequest "https://codeload.github.com/$Repo/zip/$Commit" -OutFile $Zip -UseBasicParsing
            if ((Get-Item $Zip).Length -gt 100MB) { throw 'Source archive exceeds size limit.' }
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $archive = [IO.Compression.ZipFile]::OpenRead($Zip)
            try {
                $total = 0L
                foreach ($entry in $archive.Entries) {
                    $total += $entry.Length
                    if ($entry.FullName -match '(^|[\\/])\.\.([\\/]|$)' -or [IO.Path]::IsPathRooted($entry.FullName) -or $entry.FullName.Contains(':')) { throw 'Unsafe archive entry.' }
                }
                if ($total -gt 250MB) { throw 'Expanded archive exceeds size limit.' }
            } finally { $archive.Dispose() }
            Expand-Archive $Zip (Join-Path $Stage 'source')
            $Extracted = @(Get-ChildItem (Join-Path $Stage 'source') -Directory)
            if ($Extracted.Count -ne 1) { throw 'Unexpected source archive layout.' }
            # Do not nest dependencies inside the long repository/commit archive name.
            $Source = $BuildPaths.Source
            Move-Item $Extracted[0].FullName $Source
            $Venv = $BuildPaths.Venv
            # Verify every source file against the pinned Git tree before executing build code.
            $tree = Invoke-RestMethod "https://api.github.com/repos/$Repo/git/trees/${Commit}?recursive=1" -Headers $Headers
            if ($tree.truncated) { throw 'Source integrity tree is incomplete.' }
            $known = @{}
            foreach ($entry in $tree.tree) { if ($entry.type -eq 'blob') { $known[$entry.path] = $entry.sha } }
            foreach ($file in Get-ChildItem $Source -File -Recurse -Force) {
                $relative = $file.FullName.Substring($Source.Length + 1).Replace('\','/')
                if (-not $known.ContainsKey($relative)) { throw "Untracked archive file: $relative" }
                $bytes = [IO.File]::ReadAllBytes($file.FullName)
                $prefix = [Text.Encoding]::UTF8.GetBytes("blob $($bytes.Length)`0")
                $sha1 = [Security.Cryptography.SHA1]::Create()
                try { $hash = [BitConverter]::ToString($sha1.ComputeHash([byte[]]($prefix + $bytes))).Replace('-','').ToLowerInvariant() }
                finally { $sha1.Dispose() }
                if ($hash -ne $known[$relative]) { throw "Integrity check failed: $relative" }
                $known.Remove($relative)
            }
            if ($known.Count -ne 0) { throw 'Archive is missing tracked files.' }
            Push-Location $Source
            try {
                & $Python -m venv $Venv
                if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
                $BuildPython = Join-Path $Venv 'Scripts\python.exe'
                & $BuildPython -m pip install --disable-pip-version-check -e '.[dev]'
                if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
                Push-Location web
                try {
                    & npm.cmd ci --no-audit --no-fund
                    if ($LASTEXITCODE -ne 0) { throw 'Web dependency installation failed.' }
                    & npm.cmd run build
                    if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' }
                } finally { Pop-Location }
                & $BuildPython scripts/build_binary.py
                if ($LASTEXITCODE -ne 0) { throw 'Nila binary build failed.' }
                & .\dist\nila.exe --version
                if ($LASTEXITCODE -ne 0) { throw 'New binary did not start.' }
                New-Item -ItemType Directory -Force $Target | Out-Null
                Copy-Item .\dist\nila.exe (Join-Path $Target 'nila.exe')
                Copy-Item scripts\launcher.ps1 (Join-Path $Root 'launcher.ps1')
                Copy-Item scripts\install.ps1 (Join-Path $Root 'installer.ps1')
            } finally { Pop-Location }
        } finally { if ($Stage -and (Test-Path $Stage)) { Remove-Item $Stage -Recurse -Force } }
    }
    & (Join-Path $Target 'nila.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Staged binary validation failed. Previous version retained.' }
    $Pointer = Join-Path $Root 'current.txt'
    $Pending = Join-Path $Root 'current.pending'
    [IO.File]::WriteAllText($Pending,$Commit)
    if (Test-Path $Pointer) { [IO.File]::Replace($Pending,$Pointer,(Join-Path $Root 'previous.txt')) }
    else { [IO.File]::Move($Pending,$Pointer) }
    $Bin = Join-Path $Root 'bin'
    New-Item -ItemType Directory -Force $Bin | Out-Null
    $wrapper = '@echo off' + "`r`n" + 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\NilaApp\launcher.ps1" %*' + "`r`n" + 'exit /b %ERRORLEVEL%'
    [IO.File]::WriteAllText((Join-Path $Bin 'nila.cmd'),$wrapper,[Text.Encoding]::ASCII)
    $UserPath = [string][Environment]::GetEnvironmentVariable('Path','User')
    if (($UserPath -split ';') -notcontains $Bin) { [Environment]::SetEnvironmentVariable('Path',($UserPath.TrimEnd(';')+';'+$Bin),'User') }
    $env:Path += ";$Bin"
    if (-not $UpdateOnly) {
        Write-Host 'Nila: checking the local model...'
        try { Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 | Out-Null }
        catch { Start-Process ollama.exe -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 3 }
        $models = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 10
        if ($models.models.name -notcontains 'llama3.2:1b') {
            & ollama.exe pull llama3.2:1b
            if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Rerun installer to resume.' }
        }
        if (-not $NoStartup) {
            try {
                $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+(Join-Path $Root 'launcher.ps1')+'" worker')
                $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
                $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
                $options = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
                Register-ScheduledTask -TaskName 'Nila Personal Assistant' -Action $action -Trigger $trigger -Principal $principal -Settings $options -Force | Out-Null
                Start-ScheduledTask -TaskName 'Nila Personal Assistant'
            } catch { Write-Warning 'Automatic startup could not be registered. Run nila worker to enable scheduled tasks.' }
        }
    }
    Write-Host 'Nila is ready. Open a new terminal: nila | nila web | nila doctor'
    Write-Host 'Updates use main-branch commits. Profile and chat data are preserved.'
} finally { if ($Lock) { $Lock.Dispose() } }
