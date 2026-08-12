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
    $powerShellExecutable = (Get-Process -Id $PID).Path
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
        $output = & $powerShellExecutable @arguments 2>&1 | Out-String
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
    if ($explicitDump.ExitCode -eq 0 -or $explicitDump.Output -notmatch "rejects source/dump") {
        throw "Explicit dump package was not rejected:`n$($explicitDump.Output)"
    }
    $explicitSource = Invoke-Selector -Repo $resolvedRoot -Package $source
    if ($explicitSource.ExitCode -eq 0 -or $explicitSource.Output -notmatch "rejects source/dump") {
        throw "Explicit source package was not rejected:`n$($explicitSource.Output)"
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
