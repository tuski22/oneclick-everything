$ErrorActionPreference = 'Stop'
$cliArgs = $args
function Find-Python {
    $ErrorActionPreference = 'Continue'
    foreach ($candidate in @('py.exe', 'python.exe')) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -notlike '*\Microsoft\WindowsApps\python.exe') {
            $prefix = @()
            if ($candidate -eq 'py.exe') { $prefix = @('-3') }
            & $cmd.Source @prefix -c 'import sys; sys.exit(sys.version_info < (3,9))' 2>$null
            if ($LASTEXITCODE -eq 0) { return @{ Path = $cmd.Source; Prefix = $prefix } }
        }
    }
}
$python = Find-Python
if (-not $python) {
    foreach ($arg in $cliArgs) {
        if ($arg -in @('--dry-run','--help','-h','doctor','list','verify')) {
            throw 'Python 3.9+ is required. Preview and diagnostics do not install dependencies.'
        }
    }
    if ('--yes' -notin $cliArgs) {
        if ((Read-Host 'Install Python 3.12 with WinGet? [y/N]') -ne 'y') { exit 1 }
    }
    $wingetArgs = @('install','--exact','--id','Python.Python.3.12','--source','winget')
    if ('--yes' -in $cliArgs) {
        $wingetArgs += @('--silent','--disable-interactivity','--accept-package-agreements','--accept-source-agreements')
    }
    & winget @wingetArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
        [Environment]::GetEnvironmentVariable('Path','User') + ';' + $env:Path
    $python = Find-Python
    if (-not $python) { throw 'Open a new terminal and try again. Python 3.9+ was not found.' }
}
$prefix = $python.Prefix
& $python.Path @prefix (Join-Path $PSScriptRoot 'oneclick.py') @cliArgs
exit $LASTEXITCODE
