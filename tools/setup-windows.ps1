param([string]$PythonPath = '')

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
# Private tools stay in this application's processes, without changing Windows PATH.
$env:PATH = "$projectRoot;$projectRoot\bin;$env:PATH"

function Find-CompatiblePython {
    param([string]$Command, [string[]]$Prefix = @())
    $probe = 'import json,struct,sys,sysconfig; print(json.dumps(dict(executable=sys.executable,version=list(sys.version_info[:3]),bits=struct.calcsize(''P'')*8,implementation=sys.implementation.name,free_threaded=bool(sysconfig.get_config_var(''Py_GIL_DISABLED'')))))'
    try {
        # Native stderr from missing versions must not stop discovery of another runtime.
        $output = & $Command @Prefix -I -c $probe 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $info = ($output -join "`n") | ConvertFrom-Json
        if ($info.implementation -ne 'cpython' -or $info.bits -ne 64 -or $info.free_threaded) { return $null }
        if ($info.version[0] -ne 3 -or $info.version[1] -lt 11 -or $info.version[1] -gt 13) { return $null }
        return $info
    } catch { return $null }
}

function Assert-NativeSuccess {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) { throw $Message }
}

try {
    Write-Host 'MixForge Studio - setup (Python 3.11, 3.12, or 3.13)'
    foreach ($toolName in @('ffmpeg.exe', 'ffprobe.exe')) {
        if (-not (Get-Command $toolName -ErrorAction SilentlyContinue)) {
            throw "Missing $toolName. Copy ffmpeg.exe and ffprobe.exe beside setup-windows.bat (or into bin), then run setup again. Your existing system PATH also works."
        }
    }

    $venvExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    $pythonInfo = $null
    if (Test-Path -LiteralPath $venvExe) {
        $pythonInfo = Find-CompatiblePython -Command $venvExe
        if ($null -eq $pythonInfo) {
            throw 'The existing .venv is broken or uses an unsupported interpreter. Rename .venv to .venv-old and run setup again. Setup will not delete it.'
        }
        Write-Host 'Reusing the existing MixForge Python environment.'
    } else {
        if ($PythonPath) { $pythonInfo = Find-CompatiblePython -Command $PythonPath }
        if ($null -eq $pythonInfo) {
            $pyLauncher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
            if ($pyLauncher) {
                foreach ($versionTag in @('-3.13', '-3.12', '-3.11', '')) {
                    $prefix = @()
                    if ($versionTag) { $prefix = @($versionTag) }
                    $pythonInfo = Find-CompatiblePython -Command $pyLauncher.Source -Prefix $prefix
                    if ($null -ne $pythonInfo) { break }
                }
            }
        }
        if ($null -eq $pythonInfo) {
            foreach ($pythonName in @('python.exe', 'python3.exe', 'python3.13.exe', 'python3.12.exe', 'python3.11.exe')) {
                $candidate = Get-Command $pythonName -ErrorAction SilentlyContinue
                if ($candidate -and $candidate.Source -notlike '*\Microsoft\WindowsApps\*') {
                    $pythonInfo = Find-CompatiblePython -Command $candidate.Source
                    if ($null -ne $pythonInfo) { break }
                }
            }
        }
        if ($null -eq $pythonInfo) {
            Write-Host ''
            Write-Host 'Your Python may be inside a PyCharm virtual environment.'
            Write-Host 'In PyCharm, open Settings > Project > Python Interpreter and copy its python.exe path.'
            $manualPath = Read-Host 'Paste that full python.exe path here (leave blank to stop)'
            if ($manualPath) {
                $manualPath = [Environment]::ExpandEnvironmentVariables($manualPath.Trim().Trim('"'))
                $pythonInfo = Find-CompatiblePython -Command $manualPath
            }
        }
        if ($null -eq $pythonInfo) {
            throw 'No compatible interpreter selected. Use an existing 64-bit standard CPython 3.11, 3.12, or 3.13. You can rerun this script with -PythonPath followed by the quoted python.exe path.'
        }
        $baseExe = [string]$pythonInfo.executable
        Write-Host ("Found Python " + ($pythonInfo.version -join '.') + ': ' + $baseExe)
        & $baseExe -I -m venv (Join-Path $projectRoot '.venv')
        Assert-NativeSuccess 'Could not create the MixForge virtual environment. The selected interpreter is shown above; check the Python error and folder permissions.'
    }
    Write-Host ("Using Python " + ($pythonInfo.version -join '.') + ' for MixForge.')
    & $venvExe -I -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pip') else 1)"
    if ($LASTEXITCODE -ne 0) {
        & $venvExe -I -m ensurepip --upgrade
        Assert-NativeSuccess 'Could not initialize pip in the MixForge virtual environment.'
    }
    & $venvExe -I -m pip install --disable-pip-version-check --prefer-binary -r (Join-Path $projectRoot 'requirements.txt')
    Assert-NativeSuccess 'Python was found, but dependency installation failed. The network or package error is shown above; fix it and run setup again.'

    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'dist\index.html'))) {
        $npmCommand = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
        if (-not $npmCommand) { throw 'The prebuilt interface is missing. Extract the complete application ZIP, or install Node.js 20.19+ to rebuild it.' }
        & $npmCommand.Source ci --no-audit --no-fund
        Assert-NativeSuccess 'Frontend dependency installation failed.'
        & $npmCommand.Source run build
        Assert-NativeSuccess 'Frontend build failed.'
    } else {
        Write-Host 'Using the included prebuilt interface. Node.js is only needed to rebuild it.'
    }
    Write-Host ''
    Write-Host 'Setup complete. Double-click launch-windows.bat to open MixForge Studio.'
    exit 0
} catch {
    Write-Host ''
    Write-Host ('Setup stopped: ' + $_.Exception.Message) -ForegroundColor Yellow
    exit 1
}
