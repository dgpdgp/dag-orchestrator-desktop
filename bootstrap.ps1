# PowerShell 5.1 bootstrap for Windows 10/11.
# Detect Python without relying on native stderr behavior of PowerShell 5.1.
[CmdletBinding()]
param(
    [ValidateSet('Install','Verify','Uninstall','Check')]
    [string]$Mode = 'Install'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$engine = Join-Path $root 'installer_engine.py'
if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) {
    Write-Host 'ERROR: installer_engine.py missing. Extract all archive files.' -ForegroundColor Red
    exit 2
}

function Resolve-Python([string]$Executable, [bool]$IsLauncher = $false) {
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }
    if ($Executable -match '(?i)[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $null }
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Executable
        $probe = '-c "import sys; print(sys.executable) if sys.version_info >= (3,10) else None"'
        if ($IsLauncher) { $probe = '-3 ' + $probe }
        $psi.Arguments = $probe
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        try {
            if (-not $proc.WaitForExit(15000)) {
                $proc.Kill()
                return $null
            }
            $stdout = $proc.StandardOutput.ReadToEnd().Trim()
            if ($proc.ExitCode -ne 0) { return $null }
            $path = ($stdout -split "`r?`n" | Select-Object -Last 1).Trim()
            if ($path -and (Test-Path -LiteralPath $path -PathType Leaf)) { return $path }
        } finally { $proc.Dispose() }
    } catch { return $null }
    return $null
}

$candidates = New-Object 'System.Collections.Generic.List[string]'
# Optional explicit override for troubleshooting and managed installations.
if ($env:DAG_PYTHON_EXE) { [void]$candidates.Add($env:DAG_PYTHON_EXE) }
foreach ($cmd in @('python', 'python.exe', 'python3', 'python3.exe')) {
    foreach ($item in @(Get-Command -Name $cmd -All -ErrorAction SilentlyContinue)) {
        if ($item.Source) { [void]$candidates.Add([string]$item.Source) }
    }
}
# python.org typically installs in one of these locations even when PATH is not configured.
foreach ($pattern in @(
    "$env:SystemDrive\Python3*\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
    "$env:ProgramFiles\Python3*\python.exe",
    "$env:ProgramFiles\Python\*\python.exe"
)) {
    foreach ($file in @(Get-ChildItem -Path $pattern -File -ErrorAction SilentlyContinue)) {
        [void]$candidates.Add([string]$file.FullName)
    }
}
# Standard Python registry locations (PEP 514).
foreach ($base in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore', 'HKLM:\Software\WOW6432Node\Python\PythonCore')) {
    foreach ($version in @(Get-ChildItem $base -ErrorAction SilentlyContinue)) {
        $installKey = Join-Path $version.PSPath 'InstallPath'
        try {
            $key = Get-ItemProperty -LiteralPath $installKey -ErrorAction Stop
            if ($key.ExecutablePath) { [void]$candidates.Add([string]$key.ExecutablePath) }
        } catch { }
    }
}
$found = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $found = Resolve-Python $candidate
    if ($found) { break }
}
if (-not $found) {
    foreach ($cmd in @('py', 'py.exe')) {
        foreach ($item in @(Get-Command -Name $cmd -All -ErrorAction SilentlyContinue)) {
            $found = Resolve-Python ([string]$item.Source) $true
            if ($found) { break }
        }
        if ($found) { break }
    }
}
if (-not $found) {
    Write-Host 'ERROR: Python 3.10+ not detected.' -ForegroundColor Red
    Write-Host 'Python may be installed but not visible to this installer.'
    Write-Host 'If you know its full path, run from PowerShell:'
    Write-Host '  $env:DAG_PYTHON_EXE = "C:\Path\To\python.exe"'
    Write-Host 'Then launch the installer from that same PowerShell session.'
    Write-Host 'No Claude settings were changed.'
    exit 2
}
Write-Host "Using Python: $found"
& $found -B $engine ($Mode.ToLowerInvariant())
exit $LASTEXITCODE
