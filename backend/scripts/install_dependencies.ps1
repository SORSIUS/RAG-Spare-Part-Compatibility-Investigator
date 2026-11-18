$ErrorActionPreference = 'Stop'
$ragBackend = Split-Path $PSScriptRoot -Parent
$ragPython = Join-Path $ragBackend '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $ragPython)) { throw 'Create backend/.venv first: py -3 -m venv .venv' }
if (-not $ragPython.StartsWith('\\?\')) { $ragPython = '\\?\' + $ragPython }
& $ragPython -m pip install -r (Join-Path $ragBackend 'requirements.txt')
exit $LASTEXITCODE
