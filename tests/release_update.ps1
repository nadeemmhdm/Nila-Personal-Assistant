# Real staged activation with a locally built binary; network responses are fixtures.
$ErrorActionPreference='Stop'
$originalLocal=$env:LOCALAPPDATA
$testRoot=Join-Path $env:RUNNER_TEMP ('nila-release-'+[guid]::NewGuid().ToString('N'))
$fixtureBinary=(Resolve-Path (Join-Path $PSScriptRoot '../dist/nila.exe')).Path
$version=(python -c 'from nila import __version__;print(__version__)').Trim()
$script:fixtureTag="v$version"
$script:fixtureCommit='b'*40
$script:fixtureDigest='sha256:'+(Get-FileHash $fixtureBinary -Algorithm SHA256).Hash.ToLowerInvariant()
$script:fixtureSize=(Get-Item $fixtureBinary).Length
function Invoke-RestMethod($Uri,$Headers) {
    if ($Uri -match '/commits/') { return @{sha=$script:fixtureCommit} }
    return @{draft=$false;prerelease=$false;assets=@(@{name='nila-Windows.exe';digest=$script:fixtureDigest;size=$script:fixtureSize;browser_download_url="https://github.com/nadeemmhdm/Nila-Personal-Assistant/releases/download/$script:fixtureTag/nila-Windows.exe"})}
}
function Invoke-WebRequest($Uri,$OutFile,[switch]$UseBasicParsing) { Copy-Item $fixtureBinary $OutFile }
try {
    $env:LOCALAPPDATA=$testRoot
    $root=Join-Path $testRoot 'NilaApp'
    New-Item -ItemType Directory -Force $root | Out-Null
    [IO.File]::WriteAllText((Join-Path $root 'current.txt'),('a'*40))
    & (Join-Path $PSScriptRoot '../scripts/update-release.ps1') -Commit $script:fixtureCommit -ReleaseTag $script:fixtureTag
    if ((Get-Content (Join-Path $root 'current.txt') -Raw) -ne ('b'*40)) { throw 'Successful release was not activated.' }
    if ((Get-Content (Join-Path $root 'previous.txt') -Raw) -ne ('a'*40)) { throw 'Previous release was lost.' }
    $script:fixtureCommit='c'*40
    $script:fixtureDigest='sha256:'+('0'*64)
    $rejected=$false
    try { & (Join-Path $PSScriptRoot '../scripts/update-release.ps1') -Commit $script:fixtureCommit -ReleaseTag $script:fixtureTag }
    catch { if ($_.Exception.Message -notmatch 'checksum mismatch') { throw };$rejected=$true }
    if (-not $rejected -or (Get-Content (Join-Path $root 'current.txt') -Raw) -ne ('b'*40)) { throw 'Invalid checksum changed the active installation.' }
    $lock=[IO.File]::Open((Join-Path $root 'install.lock'),'OpenOrCreate','ReadWrite','None')
    try {
        $blocked=$false
        try { & (Join-Path $PSScriptRoot '../scripts/update-release.ps1') -Commit $script:fixtureCommit -ReleaseTag $script:fixtureTag }
        catch { if ($_.Exception.Message -notmatch 'Another Nila') { throw };$blocked=$true }
        if (-not $blocked) { throw 'Concurrent installation was not blocked.' }
    } finally { $lock.Dispose() }
    Write-Output 'PASS: release activation, checksum rejection, previous pointer and exclusive lock'
} finally {
    $env:LOCALAPPDATA=$originalLocal
    Remove-Item $testRoot -Recurse -Force -ErrorAction SilentlyContinue
}
