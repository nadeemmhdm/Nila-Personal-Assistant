# Install a verified prebuilt stable-release executable under the shared update lock.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Commit,[Parameter(Mandatory=$true)][string]$ReleaseTag,[switch]$UpdateOnly)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$Repo='nadeemmhdm/Nila-Personal-Assistant'
$Root=Join-Path $env:LOCALAPPDATA 'NilaApp'
$Headers=@{'User-Agent'='Nila-Updater';'Accept'='application/vnd.github+json'}
if ($Commit -notmatch '^[a-f0-9]{40}$' -or $ReleaseTag -notmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Invalid release identity' }
if (-not (Test-Path (Join-Path $Root 'current.txt'))) { throw 'Run the Nila installer first.' }
$lock=$null
try { $lock=[IO.File]::Open((Join-Path $Root 'install.lock'),'OpenOrCreate','ReadWrite','None') }
catch { throw 'Another Nila installation/update is running. Try again later.' }
$stage=Join-Path $Root ('u-'+[guid]::NewGuid().ToString('N').Substring(0,8))
try {
    $release=Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/tags/$ReleaseTag" -Headers $Headers
    $resolved=(Invoke-RestMethod "https://api.github.com/repos/$Repo/commits/$ReleaseTag" -Headers $Headers).sha
    if ($release.draft -or $release.prerelease -or $resolved -ne $Commit) { throw 'Release changed or is not stable. Retry update.' }
    $asset=@($release.assets | Where-Object { $_.name -eq 'nila-Windows.exe' })
    if ($asset.Count -ne 1 -or $asset[0].digest -notmatch '^sha256:[a-f0-9]{64}$') { throw 'Verified Windows release asset is not available yet. Retry after publication completes.' }
    if ($asset[0].size -gt 300MB) { throw 'Release asset exceeds size limit.' }
    $expectedUrl="https://github.com/$Repo/releases/download/$ReleaseTag/nila-Windows.exe"
    if ($asset[0].browser_download_url -ne $expectedUrl) { throw 'Unexpected release asset origin.' }
    New-Item -ItemType Directory $stage | Out-Null
    $exe=Join-Path $stage 'nila.exe'
    Write-Output "Downloading $ReleaseTag..."
    Invoke-WebRequest $expectedUrl -OutFile $exe -UseBasicParsing
    if ((Get-Item $exe).Length -ne $asset[0].size -or (Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $asset[0].digest.Substring(7)) { throw 'Release checksum mismatch. Current installation retained.' }
    try { $version=(& $exe --version | Out-String).Trim() }
    catch {
        if ($_.Exception.Message -match '(?i)application control policy has blocked|blocked by group policy|blocked by your system administrator') { throw 'NILA-021: Windows application-control policy blocked the executable. Update activation stopped.' }
        throw
    }
    if ($LASTEXITCODE -ne 0 -or $version -notmatch [regex]::Escape($ReleaseTag.Substring(1))) { throw 'Release executable failed its version smoke check.' }
    $target=Join-Path $Root "versions\$Commit"
    New-Item -ItemType Directory -Force $target | Out-Null
    Copy-Item $exe (Join-Path $target 'nila.exe') -Force
    $pending=Join-Path $Root 'current.pending'
    [IO.File]::WriteAllText($pending,$Commit)
    [IO.File]::Replace($pending,(Join-Path $Root 'current.txt'),(Join-Path $Root 'previous.txt'))
    Write-Output "$ReleaseTag installed. Restart Nila."
} finally {
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    if ($lock) { $lock.Dispose() }
}
