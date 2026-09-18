[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ToolArguments
)

$ErrorActionPreference = 'Stop'
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    throw 'uv is required to run the shared hidden desktop browser skill.'
}

$tool = Join-Path $PSScriptRoot 'hidden_browser.py'
& $uv.Source run --script $tool @ToolArguments
exit $LASTEXITCODE
