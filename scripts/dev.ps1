# Use an installed base interpreter with this project's dependencies when the local
# Windows venv launcher is unavailable. No machine security settings are changed.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvConfig = Get-Content -LiteralPath (Join-Path $projectRoot '.venv/pyvenv.cfg')
$pythonDirectory = ($venvConfig | Where-Object { $_ -like 'home = *' }) -replace '^home = ', ''
$pythonExecutable = Join-Path $pythonDirectory 'python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Run uv sync --python 3.12 first.' }
$siteDirectory = Join-Path $projectRoot '.venv/Lib/site-packages'
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = @(
        (Join-Path $projectRoot 'src'), $siteDirectory,
        (Join-Path $siteDirectory 'win32'), (Join-Path $siteDirectory 'win32/lib'),
        (Join-Path $siteDirectory 'pywin32_system32')
    ) -join ';'
    & $pythonExecutable @args
    exit $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}
