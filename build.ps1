$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python scripts/build_android.py
exit $LASTEXITCODE
