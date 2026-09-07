[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'asr360x_build_runtime.ps1')

function Assert-Equal {
    param([string]$Actual, [string]$Expected, [string]$CaseName)
    if ($Actual -cne $Expected) {
        throw "$CaseName failed.`nExpected: $Expected`nActual:   $Actual"
    }
}

$commands = @(
    'make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LTEGSM CHIP_ID=CRANEG',
    'make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL',
    'make craneg_modem_watch TARGET_OS=THREADX PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL'
)

foreach ($command in $commands) {
    $effective = Add-AsrMsysBuildPathsToCommand -CommandText $command -RepoPath 'C:\work\firmware'
    Assert-Equal -Actual $effective -Expected ($command + ' ROOT_DIR=/c/work/firmware OUT=/c/work/firmware/out') -CaseName $command
}

$spaced = Add-AsrMsysBuildPathsToCommand `
    -CommandText $commands[1] `
    -RepoPath 'D:\ASR Projects\C10'
Assert-Equal `
    -Actual $spaced `
    -Expected ($commands[1] + ' "ROOT_DIR=/d/ASR Projects/C10" "OUT=/d/ASR Projects/C10/out"') `
    -CaseName 'path containing spaces'

$replaced = Add-AsrMsysBuildPathsToCommand `
    -CommandText ($commands[2] + ' ROOT_DIR=C:\old\repo OUT="C:\old repo\out"') `
    -RepoPath 'E:\new\repo'
Assert-Equal `
    -Actual $replaced `
    -Expected ($commands[2] + ' ROOT_DIR=/e/new/repo OUT=/e/new/repo/out') `
    -CaseName 'idempotent path replacement'

$nativeArguments = @(Get-AsrMsysBuildPathArguments -RepoPath 'C:\BuildRoots\builder\repo')
Assert-Equal -Actual ($nativeArguments -join '|') -Expected 'ROOT_DIR=/c/BuildRoots/builder/repo|OUT=/c/BuildRoots/builder/repo/out' -CaseName 'native arguments'

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('asr runtime test ' + [guid]::NewGuid().ToString('N'))
try {
    [System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null
    $probe = Join-Path $tempRoot 'capture.ps1'
    $captured = Join-Path $tempRoot 'captured.txt'
    @'
param([string]$RootArgument, [string]$OutArgument, [string]$ResultPath)
[System.IO.File]::WriteAllText($ResultPath, $RootArgument + '|' + $OutArgument)
'@ | Set-Content -LiteralPath $probe -Encoding UTF8
    $probeCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $probe
    $effectiveProbe = Add-AsrMsysBuildPathsToCommand -CommandText $probeCommand -RepoPath $tempRoot
    $effectiveProbe += ' "' + $captured + '"'
    $commandFile = Join-Path $tempRoot 'run.cmd'
    [System.IO.File]::WriteAllText($commandFile, "@echo off`r`n$effectiveProbe`r`nexit /b %errorlevel%`r`n", [System.Text.Encoding]::Default)
    & cmd.exe /d /c call $commandFile
    if ($LASTEXITCODE -ne 0) {
        throw "path containing spaces failed through cmd.exe with exit code $LASTEXITCODE"
    }
    $expectedRoot = Convert-ToAsrMsysPath -PathValue $tempRoot
    Assert-Equal `
        -Actual ([System.IO.File]::ReadAllText($captured)) `
        -Expected ("ROOT_DIR=$expectedRoot|OUT=$expectedRoot/out") `
        -CaseName 'cmd.exe execution with spaces'
} finally {
    if (Test-Path -LiteralPath $tempRoot -PathType Container) {
        [System.IO.Directory]::Delete($tempRoot, $true)
    }
}

Write-Host 'PASS: ASR360x build runtime preserves all three build identities and normalizes MSYS paths.'
