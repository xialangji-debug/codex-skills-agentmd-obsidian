param(
    [string]$Repo = ".",
    [string]$BuildCommand,
    [string]$Package,
    [string]$Port,
    [string]$Target = "craneg_modem_watch",
    [string]$BuildProfileAdapter,
    [string]$ManifestOut,
    [string]$Adownload,
    [switch]$NoBuild,
    [switch]$NoFlash,
    [switch]$CleanTargetOutput,
    [switch]$RequireFreshPackage,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$buildRuntime = Join-Path $env:USERPROFILE ".codex\scripts\asr360x_build_runtime.ps1"
if (-not (Test-Path -LiteralPath $buildRuntime -PathType Leaf)) {
    throw "Shared ASR360x build runtime is missing: $buildRuntime"
}
. $buildRuntime

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

function Normalize-CommandText {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    return (($Value -split '\s+') -join ' ').Trim()
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
        $productRoot = [System.IO.Path]::GetFullPath($productDir).TrimEnd('\') + '\'
        if (-not [System.IO.Path]::GetFullPath($resolvedPackage).StartsWith($productRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Normal local flashing requires the package under the selected project target: $productDir"
        }
        if ([System.IO.Path]::GetExtension($resolvedPackage) -ne ".zip" -or [System.IO.Path]::GetFileName($resolvedPackage) -match "(?i)(source|dump|acceptance)") {
            throw "Normal local flashing rejects source/dump/acceptance packages: $resolvedPackage"
        }
        return $resolvedPackage
    }

    if (-not (Test-Path -LiteralPath $productDir)) {
        throw "Output directory not found: $productDir"
    }

    $packages = @(
        Get-ChildItem -LiteralPath $productDir -Recurse -File -Filter "*.zip" |
            Where-Object { $_.Name -notmatch "(?i)(source|dump|acceptance)" } |
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

if ([string]::IsNullOrWhiteSpace($BuildProfileAdapter)) {
    $BuildProfileAdapter = Join-Path $repoPath ".codex-project\asr3602-build-profile.json"
}
$BuildProfileAdapter = Resolve-ExistingPath -PathValue $BuildProfileAdapter -BasePath $repoPath
$profileScript = Join-Path $HOME ".codex\scripts\asr3602_build_profile.py"
if (-not (Test-Path -LiteralPath $profileScript -PathType Leaf)) {
    throw "Shared ASR3602 build profile script not found: $profileScript"
}
$profileEvidence = Join-Path $env:TEMP ("asr3602-normal-test-preflight-{0}.json" -f ([guid]::NewGuid().ToString("N")))
try {
    & python -X utf8 $profileScript preflight --profile normal-test --repo $repoPath --adapter $BuildProfileAdapter --json-out $profileEvidence
    if ($LASTEXITCODE -ne 0) { throw "normal-test build profile preflight blocked the operation" }
    $profileResult = Get-Content -LiteralPath $profileEvidence -Raw -Encoding UTF8 | ConvertFrom-Json
} finally {
    if (Test-Path -LiteralPath $profileEvidence) { Remove-Item -LiteralPath $profileEvidence -Force }
}
$adapter = Get-Content -LiteralPath $BuildProfileAdapter -Raw -Encoding UTF8 | ConvertFrom-Json
$adapterSha256 = Get-Sha256Hex -PathValue $BuildProfileAdapter
if ($Target -ne [string]$adapter.buildTarget) {
    throw "Target differs from the project build profile: requested=$Target adapter=$($adapter.buildTarget)"
}
$adapterBuildCommand = [string]$adapter.build.command
if ([string]::IsNullOrWhiteSpace($BuildCommand)) {
    $BuildCommand = $adapterBuildCommand
} elseif ((Normalize-CommandText $BuildCommand) -ne (Normalize-CommandText $adapterBuildCommand)) {
    throw "BuildCommand differs from the project build profile: $adapterBuildCommand"
}
Write-Host "Build profile: normal-test"
Write-Host "Build profile adapter: $BuildProfileAdapter"
Write-Host "Build profile adapter SHA256: $adapterSha256"

if ($CleanTargetOutput) {
    if ($NoBuild) {
        throw "CleanTargetOutput cannot be combined with NoBuild"
    }
    if ($Target -notmatch '^[A-Za-z0-9_.-]+$') {
        throw "Target contains unsupported characters: $Target"
    }
    $productRoot = [System.IO.Path]::GetFullPath((Join-Path $repoPath "out\product")).TrimEnd('\') + '\'
    $targetOutput = [System.IO.Path]::GetFullPath((Join-Path $productRoot $Target)).TrimEnd('\')
    if (-not $targetOutput.StartsWith($productRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
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
    $effectiveBuildCommand = Add-AsrMsysBuildPathsToCommand -CommandText $BuildCommand -RepoPath $repoPath
    Invoke-BuildCommand -CommandText $effectiveBuildCommand -WorkingDirectory $repoPath
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
    buildProfile = "normal-test"
    buildProfileAdapter = $BuildProfileAdapter
    buildProfileAdapterSha256 = $adapterSha256
} | ConvertTo-Json -Compress))

if ([string]::IsNullOrWhiteSpace($ManifestOut)) {
    $ManifestOut = Join-Path ([System.IO.Path]::GetDirectoryName($packagePath)) "normal-test-manifest.json"
} elseif (-not [System.IO.Path]::IsPathRooted($ManifestOut)) {
    $ManifestOut = Join-Path $repoPath $ManifestOut
}
$normalManifest = [ordered]@{
    schemaVersion = 1
    kind = "asr3602-normal-test"
    build_profile = "normal-test"
    generatedAt = (Get-Date).ToString("o")
    adapter = [ordered]@{ path = $BuildProfileAdapter; sha256 = $adapterSha256; id = [string]$adapter.adapterId }
    source = [ordered]@{
        repo = $repoPath
        branch = $branch
        head = (Get-GitLine -RepoPath $repoPath -GitArgs @("rev-parse", "HEAD"))
        dirty = @($status -split "`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        dirtySummarySha256 = [string]$profileResult.source.dirtySummarySha256
    }
    build = [ordered]@{ command = $BuildCommand; target = $Target; chipId = [string]$adapter.chipId; targetOs = [string]$adapter.targetOs; psMode = [string]$adapter.psMode }
    artifact = [ordered]@{ path = $packagePath; sha256 = $packageSha256; sizeBytes = $packageItem.Length }
}
if ($DryRun) {
    Write-Host "Normal-test manifest planned: $ManifestOut"
} else {
    $manifestParent = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetFullPath($ManifestOut))
    if (-not (Test-Path -LiteralPath $manifestParent)) { New-Item -ItemType Directory -Path $manifestParent -Force | Out-Null }
    $manifestTemp = "$ManifestOut.partial-$PID"
    [System.IO.File]::WriteAllText($manifestTemp, (($normalManifest | ConvertTo-Json -Depth 8) + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $manifestTemp -Destination $ManifestOut -Force
    Write-Host "Normal-test manifest: $ManifestOut"
}

if ($NoFlash) {
    Write-Host "Flash skipped by -NoFlash."
    exit 0
}

if ((Get-Sha256Hex -PathValue $BuildProfileAdapter) -ne $adapterSha256) {
    throw "Build profile adapter changed after build; flashing blocked"
}
if ((Get-Sha256Hex -PathValue $packagePath) -ne $packageSha256) {
    throw "Firmware package changed after manifest creation; flashing blocked"
}
& python -X utf8 $profileScript preflight --profile normal-test --repo $repoPath --adapter $BuildProfileAdapter | Out-Host
if ($LASTEXITCODE -ne 0) { throw "normal-test preflight changed after build; flashing blocked" }

$expectedChip = ""
$expectedChip = [string]$adapter.chipId
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
