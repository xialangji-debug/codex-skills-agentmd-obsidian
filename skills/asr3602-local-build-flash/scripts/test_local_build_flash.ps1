Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "local_build_flash.ps1"
$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testRoot = Join-Path $tempBase ("asr-local-build-flash-test-" + [guid]::NewGuid().ToString("N"))
$resolvedRoot = [System.IO.Path]::GetFullPath($testRoot)
if (-not $resolvedRoot.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe test directory: $resolvedRoot"
}

function Invoke-Selector {
    param([string]$Repo, [string]$Package)
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptPath,
        "-Repo", $Repo,
        "-NoBuild",
        "-NoFlash"
    )
    if ($Package) {
        $arguments += @("-Package", $Package)
    }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & powershell.exe @arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
}

function Invoke-CleanBuild {
    param([string]$Repo)
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptPath,
        "-Repo", $Repo,
        "-BuildCommand", "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL",
        "-Target", "craneg_modem_watch",
        "-CleanTargetOutput",
        "-RequireFreshPackage",
        "-NoFlash"
    )
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & powershell.exe @arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    return [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
}

try {
    & git init -q -- $resolvedRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to initialize temporary Git repository"
    }
    & git -C $resolvedRoot config user.name "Test"
    & git -C $resolvedRoot config user.email "test@example.invalid"
    New-Item -ItemType File -Path (Join-Path $resolvedRoot ".test-repo") | Out-Null
    & git -C $resolvedRoot add .test-repo
    & git -C $resolvedRoot commit -q -m "base"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create temporary Git baseline"
    }
    $productDir = Join-Path $resolvedRoot "out\product\craneg_modem_watch"
    New-Item -ItemType Directory -Path $productDir -Force | Out-Null
    $contextDir = Join-Path $resolvedRoot ".codex-project"
    $configDir = Join-Path $resolvedRoot "config"
    $sourceDir = Join-Path $resolvedRoot "src"
    New-Item -ItemType Directory -Path $contextDir, $configDir, $sourceDir -Force | Out-Null
    $buildCommand = "make craneg_modem_watch TARGET_OS=ALIOS PS_MODE=LITE_LTEONLY CHIP_ID=CRANEL"
    @(
        "- CHIP_ID：``CRANEL``",
        "- TARGET_OS：``ALIOS``",
        "- PS_MODE：``LITE_LTEONLY``",
        "- 构建目标：``craneg_modem_watch``",
        "- 构建命令：``$buildCommand``"
    ) | Set-Content -LiteralPath (Join-Path $contextDir "variant.md") -Encoding UTF8
    '[{"id":"CDF","image":"EEHandlerConfig.nvm"}]' | Set-Content -LiteralPath (Join-Path $configDir "watchdog.json") -Encoding UTF8
    '#define USE_LV_CHARGING_BATTERY 0' | Set-Content -LiteralPath (Join-Path $configDir "charge.h") -Encoding Ascii
    'int at_command;' | Set-Content -LiteralPath (Join-Path $sourceDir "at.c") -Encoding Ascii
    [ordered]@{
        schemaVersion = 1
        adapterId = "test-asr3602"
        product = "TEST"
        supportLevel = "ASR3602_BUILD_VERIFIED"
        chipId = "CRANEL"
        targetOs = "ALIOS"
        psMode = "LITE_LTEONLY"
        buildTarget = "craneg_modem_watch"
        build = [ordered]@{
            command = $buildCommand
            commandArgs = @("make", "craneg_modem_watch", "TARGET_OS=ALIOS", "PS_MODE=LITE_LTEONLY", "CHIP_ID=CRANEL")
            preBuild = [ordered]@{ command = "ninja -C out -t clean"; commandArgs = @("ninja", "-C", "out", "-t", "clean") }
        }
        watchdogConfig = [ordered]@{ path = "config/watchdog.json"; entryId = "CDF"; entryImage = "EEHandlerConfig.nvm" }
        chargingAnimation = [ordered]@{ path = "config/charge.h"; defineName = "USE_LV_CHARGING_BATTERY"; releaseValue = 0; dumpTestValue = 0; stubStrategy = "none" }
        artifacts = [ordered]@{ outputDir = "out/product/craneg_modem_watch"; zipName = "firmware_release.zip"; mdbName = "firmware.mdb.txt" }
        allowedTemporaryFiles = @("config/watchdog.json")
        forbiddenSourceMarkers = @([ordered]@{ path = "src/at.c"; marker = "ASR360X_DUMP_ACCEPTANCE_TEST" })
        dumpAcceptance = [ordered]@{ sourcePath = "src/at.c"; marker = "ASR360X_DUMP_ACCEPTANCE_TEST" }
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $contextDir "asr3602-build-profile.json") -Encoding UTF8

    $normal = Join-Path $productDir "firmware_release.zip"
    $source = Join-Path $productDir "firmware_source.zip"
    $dump = Join-Path $productDir "firmware_dump.zip"
    New-Item -ItemType File -Path $normal, $source, $dump | Out-Null
    (Get-Item -LiteralPath $normal).LastWriteTime = (Get-Date).AddMinutes(-10)
    (Get-Item -LiteralPath $source).LastWriteTime = (Get-Date).AddMinutes(-2)
    (Get-Item -LiteralPath $dump).LastWriteTime = (Get-Date).AddMinutes(-1)

    $auto = Invoke-Selector -Repo $resolvedRoot -Package ""
    if ($auto.ExitCode -ne 0) {
        throw "Automatic package selection failed:`n$($auto.Output)"
    }
    if ($auto.Output -notmatch [regex]::Escape($normal)) {
        throw "Automatic selection did not choose the normal package:`n$($auto.Output)"
    }
    if ($auto.Output -match "Selected package:.*(?:source|dump)") {
        throw "Automatic selection chose an excluded package:`n$($auto.Output)"
    }

    $explicitDump = Invoke-Selector -Repo $resolvedRoot -Package $dump
    if ($explicitDump.ExitCode -eq 0 -or $explicitDump.Output -notmatch "rejects source/dump/acceptance") {
        throw "Explicit dump package was not rejected:`n$($explicitDump.Output)"
    }
    $explicitSource = Invoke-Selector -Repo $resolvedRoot -Package $source
    if ($explicitSource.ExitCode -eq 0 -or $explicitSource.Output -notmatch "rejects source/dump/acceptance") {
        throw "Explicit source package was not rejected:`n$($explicitSource.Output)"
    }

    $otherOutput = Join-Path $resolvedRoot "out\product\another_target"
    New-Item -ItemType Directory -Path $otherOutput -Force | Out-Null
    $preservedMarker = Join-Path $otherOutput "keep.txt"
    Set-Content -LiteralPath $preservedMarker -Value "keep" -Encoding Ascii
    $staleMarker = Join-Path $productDir "stale.txt"
    Set-Content -LiteralPath $staleMarker -Value "stale" -Encoding Ascii
    $buildScript = Join-Path $resolvedRoot "make.cmd"
    @(
        "@echo off",
        "if not exist out\product\craneg_modem_watch mkdir out\product\craneg_modem_watch",
        "type nul > out\product\craneg_modem_watch\firmware_release.zip"
    ) | Set-Content -LiteralPath $buildScript -Encoding Ascii

    $cleanBuild = Invoke-CleanBuild -Repo $resolvedRoot
    if ($cleanBuild.ExitCode -ne 0) {
        throw "Target clean build failed:`n$($cleanBuild.Output)"
    }
    if (Test-Path -LiteralPath $staleMarker) {
        throw "Target clean build retained stale target output"
    }
    if (-not (Test-Path -LiteralPath $preservedMarker)) {
        throw "Target clean build removed a sibling target output"
    }
    if ($cleanBuild.Output -notmatch "Artifact:") {
        throw "Target clean build did not produce a fresh artifact record:`n$($cleanBuild.Output)"
    }
    $normalManifestPath = Join-Path $productDir "normal-test-manifest.json"
    if (-not (Test-Path -LiteralPath $normalManifestPath -PathType Leaf)) {
        throw "Target clean build did not write normal-test-manifest.json"
    }
    $normalManifest = Get-Content -LiteralPath $normalManifestPath -Raw | ConvertFrom-Json
    if ($normalManifest.build_profile -ne "normal-test" -or
        [string]::IsNullOrWhiteSpace([string]$normalManifest.adapter.sha256) -or
        [string]::IsNullOrWhiteSpace([string]$normalManifest.artifact.sha256)) {
        throw "Normal-test manifest did not bind profile, adapter, and artifact hashes"
    }

    Remove-Item -LiteralPath $normal -Force
    $none = Invoke-Selector -Repo $resolvedRoot -Package ""
    if ($none.ExitCode -eq 0 -or $none.Output -notmatch "excluding source/dump") {
        throw "Source/dump-only directory was not rejected:`n$($none.Output)"
    }

    Write-Host "local build/flash package selector tests passed"
} finally {
    if (
        (Test-Path -LiteralPath $resolvedRoot) -and
        $resolvedRoot.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase) -and
        [System.IO.Path]::GetFileName($resolvedRoot).StartsWith("asr-local-build-flash-test-")
    ) {
        Remove-Item -LiteralPath $resolvedRoot -Recurse -Force
    }
}
