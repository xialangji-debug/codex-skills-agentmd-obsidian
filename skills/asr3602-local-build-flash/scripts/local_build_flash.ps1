param(
    [string]$Repo = ".",
    [string]$BuildCommand,
    [string]$Package,
    [string]$Port,
    [string]$Target = "craneg_modem_watch",
    [string]$Adownload,
    [switch]$NoBuild,
    [switch]$NoFlash,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ExistingPath {
    param([string]$PathValue, [string]$BasePath)
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return (Resolve-Path -LiteralPath $PathValue).Path
    }
    return (Resolve-Path -LiteralPath (Join-Path $BasePath $PathValue)).Path
}

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments)
    Write-Host ("+ {0} {1}" -f $FilePath, ($Arguments -join " "))
    if ($DryRun) {
        return
    }
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath"
    }
}

function Invoke-BuildCommand {
    param([string]$CommandText, [string]$WorkingDirectory)
    Write-Host ("+ {0}" -f $CommandText)
    if ($DryRun) {
        return
    }
    Push-Location -LiteralPath $WorkingDirectory
    try {
        & cmd.exe /d /c $CommandText
        if ($LASTEXITCODE -ne 0) {
            throw "Build command failed with exit code ${LASTEXITCODE}: $CommandText"
        }
    } finally {
        Pop-Location
    }
}

function Get-GitLine {
    param([string]$RepoPath, [string[]]$GitArgs)
    $result = & git -C $RepoPath @GitArgs 2>$null
    if ($LASTEXITCODE -ne 0) {
        return ""
    }
    return ($result -join "`n").Trim()
}

function Resolve-Adownload {
    param([string]$RepoPath, [string]$ExplicitPath)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return Resolve-ExistingPath -PathValue $ExplicitPath -BasePath $RepoPath
    }

    $candidates = @(
        (Join-Path $RepoPath "prebuilts\misc\windows-x86\adownload.exe"),
        "C:\Users\84365\Desktop\aboot-tools-2023.08.27-win-x64\adownload.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $cmd = Get-Command adownload.exe -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        return $cmd.Source
    }

    throw "adownload.exe not found. Provide -Adownload or enable the aboot-download MCP."
}

function Select-FirmwarePackage {
    param([string]$RepoPath, [string]$TargetName, [string]$ExplicitPackage)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPackage)) {
        return Resolve-ExistingPath -PathValue $ExplicitPackage -BasePath $RepoPath
    }

    $productDir = Join-Path $RepoPath ("out\product\{0}" -f $TargetName)
    if (-not (Test-Path -LiteralPath $productDir)) {
        throw "Output directory not found: $productDir"
    }

    $packages = Get-ChildItem -LiteralPath $productDir -Recurse -File -Filter "*.zip" |
        Where-Object { $_.Name -notmatch "(?i)source" } |
        Sort-Object LastWriteTime -Descending

    if (-not $packages -or $packages.Count -eq 0) {
        throw "No non-source firmware zip found under $productDir"
    }

    Write-Host "Firmware package candidates:"
    $packages | Select-Object -First 5 | ForEach-Object {
        Write-Host ("  {0:u}  {1:n0} bytes  {2}" -f $_.LastWriteTime, $_.Length, $_.FullName)
    }

    return $packages[0].FullName
}

$repoPath = Resolve-ExistingPath -PathValue $Repo -BasePath (Get-Location).Path
Write-Host "Repo: $repoPath"

$branch = Get-GitLine -RepoPath $repoPath -GitArgs @("branch", "--show-current")
$commit = Get-GitLine -RepoPath $repoPath -GitArgs @("rev-parse", "--short", "HEAD")
$status = Get-GitLine -RepoPath $repoPath -GitArgs @("status", "--short")
if ($branch) { Write-Host "Branch: $branch" }
if ($commit) { Write-Host "Commit: $commit" }
if ($status) {
    Write-Host "Dirty files:"
    Write-Host $status
}

if (-not $NoBuild) {
    if ([string]::IsNullOrWhiteSpace($BuildCommand)) {
        throw "BuildCommand is required unless -NoBuild is used. Read .codex-project\build.md or ask the user for the exact command."
    }
    Invoke-BuildCommand -CommandText $BuildCommand -WorkingDirectory $repoPath
} else {
    Write-Host "Build skipped by -NoBuild."
}

$packagePath = Select-FirmwarePackage -RepoPath $repoPath -TargetName $Target -ExplicitPackage $Package
Write-Host "Selected package: $packagePath"

if ($NoFlash) {
    Write-Host "Flash skipped by -NoFlash."
    exit 0
}

$expectedChip = ""
if ($BuildCommand -match '(?i)\bCHIP_ID=([^\s]+)') { $expectedChip = $Matches[1] }
$preflight = Join-Path $env:USERPROFILE ".codex\skills\aa-skill-router\scripts\embedded_target_preflight.ps1"
if (-not (Test-Path -LiteralPath $preflight)) { throw "Embedded target preflight not found: $preflight" }
$preflightArgs = @("-ExpectedFamily", "ASR", "-ExpectedChip", $expectedChip, "-ProjectDir", $repoPath, "-Package", $packagePath)
if (-not [string]::IsNullOrWhiteSpace($Port)) { $preflightArgs += @("-Port", $Port) }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $preflight @preflightArgs
if ($LASTEXITCODE -ne 0) { throw "Embedded target preflight blocked flashing" }

$downloadTool = Resolve-Adownload -RepoPath $repoPath -ExplicitPath $Adownload
$downloadArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Port)) {
    $downloadArgs += @("-p", $Port)
} else {
    $downloadArgs += "-u"
}
$downloadArgs += @("-a", "-s", "115200", "-r", "-q", $packagePath)
Invoke-Checked -FilePath $downloadTool -Arguments $downloadArgs
Write-Host "Flash completed."
