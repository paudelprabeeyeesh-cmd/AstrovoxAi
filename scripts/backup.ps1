param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $root '..')
Set-Location -LiteralPath $projectRoot

$env:PYTHONPATH = $projectRoot.Path
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error 'Python is not installed or not on PATH'
    exit 1
}
& python (Join-Path $root 'run_backup.py')

