param(
    [string]$Repo = ".",
    [string]$BuildCommand,
    [string]$Package,
    [string]$Port,
    [string]$Target = "craneg_modem_watch",
    [string]$Adownload,
    [switch]$NoBuild,
    [switch]$NoFlash,
    [switch]$CleanTargetOutput,
    [switch]$RequireFreshPackage,
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

function Get-Sha256Hex {
    param([string]$PathValue)
    $stream = [System.IO.File]::OpenRead($PathValue)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha256.ComputeHash($stream)
        return ([System.BitConverter]::ToString($bytes)).Replace("-", "")
    } finally {
        $sha256.Dispose()
        $stream.Dispose()
    }
}

function Resolve-Adownload {
    param([string]$RepoPath, [string]$ExplicitPath)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return Resolve-ExistingPath -PathValue $ExplicitPath -BasePath $RepoPath
    }

    $privatePathFile = Join-Path $HOME ".codex\secrets\asr3602-local-build-flash\adownload.path"
    $candidates = @((Join-Path $RepoPath "prebuilts\misc\windows-x86\adownload.exe"))
    if (-not [string]::IsNullOrWhiteSpace($env:ABOOT_DOWNLOAD_EXE)) {
        $candidates += $env:ABOOT_DOWNLOAD_EXE
    }
    if (Test-Path -LiteralPath $privatePathFile) {
        $privatePath = (Get-Content -LiteralPath $privatePathFile -Raw).Trim()
        if (-not [string]::IsNullOrWhiteSpace($privatePath)) {
            $candidates += $privatePath
        }
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $cmd = Get-Command adownload.exe -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        return $cmd.Source
    }

    throw "adownload.exe not found. Provide -Adownload, set ABOOT_DOWNLOAD_EXE, or configure ~/.codex/secrets/asr3602-local-build-flash/adownload.path."
}

function Select-FirmwarePackage {
    param([string]$RepoPath, [string]$TargetName, [string]$ExplicitPackage)
    $productDir = Join-Path $RepoPath ("out\product\{0}" -f $TargetName)
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPackage)) {
        $resolvedPackage = Resolve-ExistingPath -PathValue $ExplicitPackage -BasePath $RepoPath
        $separator = [System.IO.Path]::DirectorySeparatorChar
        $pathComparison = if ($separator -eq '\') { [System.StringComparison]::OrdinalIgnoreCase } else { [System.StringComparison]::Ordinal }
        $productRoot = [System.IO.Path]::GetFullPath($productDir).TrimEnd($separator) + $separator
        if (-not [System.IO.Path]::GetFullPath($resolvedPackage).StartsWith($productRoot, $pathComparison)) {
            throw "Normal local flashing requires the package under the selected project target: $productDir"
        }
        if ([System.IO.Path]::GetExtension($resolvedPackage) -ne ".zip" -or [System.IO.Path]::GetFileName($resolvedPackage) -match "(?i)(source|dump)") {
            throw "Normal local flashing rejects source/dump packages: $resolvedPackage"
        }
        return $resolvedPackage
    }

    if (-not (Test-Path -LiteralPath $productDir)) {
        throw "Output directory not found: $productDir"
    }

    $packages = @(
        Get-ChildItem -LiteralPath $productDir -Recurse -File -Filter "*.zip" |
            Where-Object { $_.Name -notmatch "(?i)(source|dump)" } |
            Sort-Object LastWriteTime -Descending
    )

    if (-not $packages -or $packages.Count -eq 0) {
        throw "No normal firmware zip (excluding source/dump) found under $productDir"
    }

    Write-Host "Firmware package candidates:"
    $packages | Select-Object -First 5 | ForEach-Object {
        Write-Host ("  {0:u}  {1:n0} bytes  {2}" -f $_.LastWriteTime, $_.Length, $_.FullName)
    }

    return $packages[0].FullName
}

$repoPath = Resolve-ExistingPath -PathValue $Repo -BasePath (Get-Location).Path
Write-Host "Repo: $repoPath"

if ($CleanTargetOutput) {
    if ($NoBuild) {
        throw "CleanTargetOutput cannot be combined with NoBuild"
    }
    if ($Target -notmatch '^[A-Za-z0-9_.-]+$') {
        throw "Target contains unsupported characters: $Target"
    }
    $separator = [System.IO.Path]::DirectorySeparatorChar
    $pathComparison = if ($separator -eq '\') { [System.StringComparison]::OrdinalIgnoreCase } else { [System.StringComparison]::Ordinal }
    $productRoot = [System.IO.Path]::GetFullPath((Join-Path $repoPath "out\product")).TrimEnd($separator) + $separator
    $targetOutput = [System.IO.Path]::GetFullPath((Join-Path $productRoot $Target)).TrimEnd($separator)
    if (-not $targetOutput.StartsWith($productRoot, $pathComparison) -or
        [System.IO.Path]::GetFileName($targetOutput) -ne $Target) {
        throw "Refusing to clean an output path outside the selected target: $targetOutput"
    }
    if (Test-Path -LiteralPath $targetOutput -PathType Container) {
        Write-Host "Cleaning generated target output: $targetOutput"
        if (-not $DryRun) {
            Remove-Item -LiteralPath $targetOutput -Recurse -Force
        }
    } else {
        Write-Host "Generated target output is already absent: $targetOutput"
    }
}

$branch = Get-GitLine -RepoPath $repoPath -GitArgs @("branch", "--show-current")
$commit = Get-GitLine -RepoPath $repoPath -GitArgs @("rev-parse", "--short", "HEAD")
$status = Get-GitLine -RepoPath $repoPath -GitArgs @("status", "--short")
if ($branch) { Write-Host "Branch: $branch" }
if ($commit) { Write-Host "Commit: $commit" }
if ($status) {
    Write-Host "Dirty files:"
    Write-Host $status
}

$buildStartedAt = Get-Date
if (-not $NoBuild) {
    if ([string]::IsNullOrWhiteSpace($BuildCommand)) {
        throw "BuildCommand is required unless -NoBuild is used. Read .codex-project\build.md or ask the user for the exact command."
    }
    Invoke-BuildCommand -CommandText $BuildCommand -WorkingDirectory $repoPath
} else {
    Write-Host "Build skipped by -NoBuild."
}

$packagePath = Select-FirmwarePackage -RepoPath $repoPath -TargetName $Target -ExplicitPackage $Package
$packageItem = Get-Item -LiteralPath $packagePath
if ($RequireFreshPackage) {
    if ($NoBuild) {
        throw "RequireFreshPackage cannot be combined with NoBuild. Build first so the selected artifact can be tied to this run."
    }
    if ($packageItem.LastWriteTime -lt $buildStartedAt.AddSeconds(-2)) {
        throw "Selected package was not generated or updated by this build: $packagePath"
    }
}
$packageSha256 = Get-Sha256Hex -PathValue $packagePath
Write-Host "Selected package: $packagePath"
Write-Host "Selected package SHA256: $packageSha256"
Write-Host ("Artifact: {0}" -f ([ordered]@{
    packagePath = $packagePath
    packageSha256 = $packageSha256
    sizeBytes = $packageItem.Length
    lastWriteTime = $packageItem.LastWriteTime.ToString("o")
    branch = $branch
    commit = $commit
    target = $Target
    buildCommand = $BuildCommand
} | ConvertTo-Json -Compress))

if ($NoFlash) {
    Write-Host "Flash skipped by -NoFlash."
    exit 0
}

$expectedChip = ""
if ($BuildCommand -match '(?i)\bCHIP_ID=([^\s]+)') { $expectedChip = $Matches[1] }
$preflight = Join-Path $PSScriptRoot "embedded_target_preflight.ps1"
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
