param(
    [string]$Repo = (Get-Location).Path,
    [string]$Port = "",
    [string]$Baud = "115200",
    [switch]$AtFallback,
    [switch]$NoFlash,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host ">>> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath"
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Text
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Get-Sha256Hex {
    param([Parameter(Mandatory = $true)][string]$Path)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        $hash = $sha.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "")
    } finally {
        $sha.Dispose()
    }
}

function Resolve-MakeTool {
    $candidates = @(
        "C:\msys64\usr\bin\make.exe",
        "C:\Program Files\Git\usr\bin\make.exe",
        "C:\Program Files\DS-5 v5.26.2\bin\make.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $cmd = Get-Command make -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        return $cmd.Source
    }

    throw "Could not find make.exe. Install MSYS2 make or add make to PATH."
}

function To-ForwardSlashPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return $Path.Replace("\", "/")
}

function Invoke-ReleasePackage {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][string]$OutDir
    )

    $arelease = Join-Path $RepoPath "prebuilts\misc\windows-x86\arelease.exe"
    if (-not (Test-Path -LiteralPath $arelease)) {
        throw "Missing release tool: $arelease"
    }

    $releaseConfig = To-ForwardSlashPath -Path (Join-Path $RepoPath "releasepack")
    $productDir = Join-Path $RepoPath "product\craneg_modem"
    $imagesDir = Join-Path $RepoPath "releasepack\images"

    $requiredImages = @(
        (Join-Path $OutDir "craneg_modem_watch.bin"),
        (Join-Path $OutDir "resource.bin"),
        (Join-Path $productDir "dsp\CRANEL\ALIOS\LITE_LTEONLY\dsp.bin"),
        (Join-Path $productDir "dsp\CRANEL\ALIOS\LITE_LTEONLY\rf.bin"),
        (Join-Path $productDir "tavor\Arbel\build\boot33_lite.bin"),
        (Join-Path $imagesDir "logo.bin"),
        (Join-Path $productDir "tavor\Arbel\build\apn.bin"),
        (Join-Path $productDir "wcn\ASR5801_BTDM\build_ram_only.bin"),
        (Join-Path $productDir "wcn\ASR5801_BTDM\bt_update_26M.lst"),
        (Join-Path $imagesDir "null_fw.bin"),
        (Join-Path $productDir "wcn\ASR5311_GNSS\jacana_fw.bin")
    )
    foreach ($image in $requiredImages) {
        if (-not (Test-Path -LiteralPath $image)) {
            throw "Missing image required for release package: $image"
        }
    }

    $packageZip = Join-Path $OutDir "craneg_modem_watch_asr3602_8+8mb.zip"
    $sourceZip = Join-Path $OutDir "craneg_modem_watch_asr3602_8+8mb_source.zip"
    Remove-Item -LiteralPath $packageZip, $sourceZip -Force -ErrorAction SilentlyContinue

    $args = @(
        "-c", $releaseConfig,
        "-g",
        "-p", "ASR_CRANE_EVB",
        "-v", "ASR3602_8+8MB",
        "-i", ("cp=" + (To-ForwardSlashPath -Path (Join-Path $OutDir "craneg_modem_watch.bin"))),
        "-i", ("dsp=" + (To-ForwardSlashPath -Path (Join-Path $productDir "dsp\CRANEL\ALIOS\LITE_LTEONLY\dsp.bin"))),
        "-i", ("rfbin=" + (To-ForwardSlashPath -Path (Join-Path $productDir "dsp\CRANEL\ALIOS\LITE_LTEONLY\rf.bin"))),
        "-i", ("boot33_bin=" + (To-ForwardSlashPath -Path (Join-Path $productDir "tavor\Arbel\build\boot33_lite.bin"))),
        "-i", ("logo=" + (To-ForwardSlashPath -Path (Join-Path $imagesDir "logo.bin"))),
        "-i", ("apn=" + (To-ForwardSlashPath -Path (Join-Path $productDir "tavor\Arbel\build\apn.bin"))),
        "-i", ("resource=" + (To-ForwardSlashPath -Path (Join-Path $OutDir "resource.bin"))),
        "-i", ("bt_btbin=" + (To-ForwardSlashPath -Path (Join-Path $productDir "wcn\ASR5801_BTDM\build_ram_only.bin"))),
        "-i", ("bt_btlst=" + (To-ForwardSlashPath -Path (Join-Path $productDir "wcn\ASR5801_BTDM\bt_update_26M.lst"))),
        "-i", ("heron_califw=" + (To-ForwardSlashPath -Path (Join-Path $imagesDir "null_fw.bin"))),
        "-i", ("heron_fmacfw=" + (To-ForwardSlashPath -Path (Join-Path $imagesDir "null_fw.bin"))),
        "-i", ("jacana_fw=" + (To-ForwardSlashPath -Path (Join-Path $productDir "wcn\ASR5311_GNSS\jacana_fw.bin"))),
        "-i", "boardid=",
        "--release-pack", "craneg_modem_watch_asr3602_8+8mb_source.zip",
        "craneg_modem_watch_asr3602_8+8mb.zip"
    )

    Push-Location $OutDir
    try {
        Invoke-Checked -FilePath $arelease -Arguments $args
    } finally {
        Pop-Location
    }

    if (-not (Test-Path -LiteralPath $packageZip)) {
        throw "Release package was not generated: $packageZip"
    }
}

$repoPath = (Resolve-Path -LiteralPath $Repo).Path
$configRel = "releasepack\reliabledata\asr3602_evb\config.json"
$configPath = Join-Path $repoPath $configRel
$outDir = Join-Path $repoPath "out\product\craneg_modem_watch"
$expectedZip = Join-Path $outDir "craneg_modem_watch_asr3602_8+8mb.zip"
$downloadTool = Join-Path $repoPath "prebuilts\misc\windows-x86\adownload.exe"
$makeTool = Resolve-MakeTool
$makeDir = Split-Path -Parent $makeTool
if ($env:PATH -notlike "*$makeDir*") {
    $env:PATH = "$makeDir;$env:PATH"
}

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Missing config file: $configPath"
}

$originalBytes = [System.IO.File]::ReadAllBytes($configPath)
$originalText = [System.IO.File]::ReadAllText($configPath)
$originalHash = Get-Sha256Hex -Path $configPath
$backupPath = Join-Path ([System.IO.Path]::GetTempPath()) ("asr3602_config_{0}_{1}.json" -f $PID, (Get-Date -Format "yyyyMMddHHmmss"))
[System.IO.File]::WriteAllBytes($backupPath, $originalBytes)

$buildSucceeded = $false

try {
    $watchdogObjectPattern = '(?s)\{\s*"id"\s*:\s*"CDF"\s*,\s*"image"\s*:\s*"EEHandlerConfig\.nvm"\s*\}'
    $watchdogMatches = [System.Text.RegularExpressions.Regex]::Matches($originalText, $watchdogObjectPattern)
    if ($watchdogMatches.Count -ne 1) {
        throw "Expected exactly one watchdog entry CDF/EEHandlerConfig.nvm, found $($watchdogMatches.Count)."
    }

    $removeLastItemPattern = '(?s),\s*\{\s*"id"\s*:\s*"CDF"\s*,\s*"image"\s*:\s*"EEHandlerConfig\.nvm"\s*\}\s*(?=\])'
    $modifiedText = [System.Text.RegularExpressions.Regex]::Replace($originalText, $removeLastItemPattern, [Environment]::NewLine, 1)
    if ($modifiedText -eq $originalText) {
        throw "Watchdog entry was found but could not be removed as the last JSON item."
    }

    Write-Utf8NoBom -Path $configPath -Text $modifiedText
    Write-Host "Removed watchdog entry from $configRel for dump firmware packaging."

    if ($SkipBuild) {
        Write-Host "SkipBuild set; not running make."
        $buildSucceeded = $true
    } else {
        Push-Location $repoPath
        try {
            Invoke-Checked -FilePath $makeTool -Arguments @("craneg_modem_watch", "TARGET_OS=ALIOS", "PS_MODE=LITE_LTEONLY", "CHIP_ID=CRANEL")
            Invoke-ReleasePackage -RepoPath $repoPath -OutDir $outDir
            $buildSucceeded = $true
        } finally {
            Pop-Location
        }
    }
} finally {
    [System.IO.File]::WriteAllBytes($configPath, $originalBytes)
    $restoredHash = Get-Sha256Hex -Path $configPath
    if ($restoredHash -ne $originalHash) {
        throw "Failed to restore $configRel byte-for-byte. Backup remains at $backupPath"
    }
    Remove-Item -LiteralPath $backupPath -Force -ErrorAction SilentlyContinue
    Write-Host "Restored $configRel; watchdog deletion is not left in the worktree."
}

if (-not $buildSucceeded) {
    throw "Build did not complete; not flashing."
}

if (Test-Path -LiteralPath $expectedZip) {
    $zipPath = (Resolve-Path -LiteralPath $expectedZip).Path
} else {
    $zip = Get-ChildItem -LiteralPath $outDir -Filter "*asr3602*8+8mb*.zip" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "*_source.zip" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $zip) {
        throw "Could not find dump firmware package under $outDir"
    }
    $zipPath = $zip.FullName
}

Write-Host "Firmware package: $zipPath"

if ($NoFlash) {
    Write-Host "NoFlash set; package was not flashed."
    exit 0
}

if (-not (Test-Path -LiteralPath $downloadTool)) {
    throw "Missing download tool: $downloadTool"
}

$downloadArgs = @()
if ($Port.Trim().Length -gt 0) {
    $downloadArgs += @("-p", $Port.Trim(), "-a")
} else {
    $downloadArgs += @("-u", "-a")
}
if ($AtFallback) {
    $downloadArgs += "-f"
}
$downloadArgs += @("-s", $Baud, "-r", "-q", $zipPath)

Invoke-Checked -FilePath $downloadTool -Arguments $downloadArgs
Write-Host "Flash completed."
