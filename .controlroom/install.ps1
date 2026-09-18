# Controlroom Windows entrypoint. Uses the same update transaction as other OSes.
[CmdletBinding()]
param([string]$Agent, [string]$Gbrain, [string]$Project, [string]$ProfileName, [switch]$Help)
$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
if ($Gbrain) { if ($Agent -and $Agent -ne $Gbrain) { throw 'Conflicting role names.' }; $Agent = $Gbrain }
if ($Project -or $ProfileName) { throw 'Projects are physical folders under ~/projects. Use controlroom pull to update them.' }
$python = Get-Command python.exe -ErrorAction SilentlyContinue
$pythonArgs = @()
if (-not $python) { $python = Get-Command py.exe -ErrorAction SilentlyContinue; $pythonArgs = @('-3') }
if (-not $python) { throw 'Python 3.12 or newer is required.' }
& $python.Source @pythonArgs -c 'import sys; raise SystemExit(sys.version_info < (3,12))'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 or newer is required.' }
$corePath = if ($PSScriptRoot) { Join-Path $PSScriptRoot 'scripts\controlroom.py' } else { '' }
$bootstrapPath = $null
$exitCode = 1
try {
    $coreArgs = @('install')
    if ($Help) { $coreArgs += '--help' }
    elseif ($Agent) { $coreArgs += $Agent }
    if (-not $corePath -or -not (Test-Path -LiteralPath $corePath)) {
        $git = Get-Command git.exe -ErrorAction Stop
        $cachePath = Join-Path $env:USERPROFILE '.local\share\controlroom\tmp'
        New-Item -ItemType Directory -Path $cachePath -Force | Out-Null
        $bootstrapPath = Join-Path $cachePath ('bootstrap-' + [guid]::NewGuid().ToString('N'))
        & $git.Source clone --branch main --single-branch https://github.com/chaconne67/controlroom.git $bootstrapPath
        if ($LASTEXITCODE -ne 0) { throw 'Controlroom download failed.' }
        $corePath = Join-Path $bootstrapPath '.controlroom\scripts\controlroom.py'
        $coreArgs += @('--source', $bootstrapPath)
    }
    & $python.Source @pythonArgs -X utf8 $corePath @coreArgs
    $exitCode = $LASTEXITCODE
} finally {
    if ($bootstrapPath -and (Test-Path -LiteralPath $bootstrapPath)) {
        $resolvedBootstrap = [System.IO.Path]::GetFullPath($bootstrapPath)
        $resolvedCache = [System.IO.Path]::GetFullPath($cachePath).TrimEnd('\') + '\'
        if (-not $resolvedBootstrap.StartsWith($resolvedCache, 'OrdinalIgnoreCase')) { throw 'Unsafe temporary directory.' }
        Remove-Item -LiteralPath $resolvedBootstrap -Recurse -Force
    }
}
exit $exitCode
