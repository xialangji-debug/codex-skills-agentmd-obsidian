param(
  [string]$Repo = ".",
  [string]$ReleaseTime = "",
  [string]$Target = "craneg_modem_watch",
  [string]$PSMode = "LITE_LTEONLY",
  [string]$TargetOS = "ALIOS",
  [string]$ChipId = "CRANEL",
  [string]$Readme = "",
  [string]$RemoteProductFolder = "",
  [switch]$NoPreflight,
  [switch]$NoUpload,
  [switch]$ForceCleanBuild,
  [switch]$TrustExistingPackage,
  [switch]$NoReadme,
  [switch]$KeepYlVersion,
  [switch]$AllowUntrackedSource,
  [switch]$DryRun,
  [switch]$ReplaceExisting,
  [switch]$Headed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-ExistingOrFullPath {
  param([string]$PathValue)
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }
  return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
}

function Invoke-Checked {
  param(
    [string]$Command,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [hashtable]$Environment = @{}
  )

  $oldEnv = @{}
  foreach ($key in $Environment.Keys) {
    $oldEnv[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
    Set-Item -LiteralPath "Env:$key" -Value ([string]$Environment[$key])
  }

  Push-Location -LiteralPath $WorkingDirectory
  try {
    Write-Host (">> " + $Command + " " + ($Arguments -join " "))
    & $Command @Arguments
    $exitCode = $LASTEXITCODE
    if ($null -ne $exitCode -and $exitCode -ne 0) {
      throw "Command failed with exit code ${exitCode}: $Command"
    }
  } finally {
    Pop-Location
    foreach ($key in $Environment.Keys) {
      if ($null -eq $oldEnv[$key]) {
        Remove-Item -LiteralPath "Env:$key" -ErrorAction SilentlyContinue
      } else {
        Set-Item -LiteralPath "Env:$key" -Value $oldEnv[$key]
      }
    }
  }
}

function Get-GitText {
  param(
    [string]$RepoPath,
    [string[]]$Arguments
  )
  $psi = [Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = "git"
  $psi.Arguments = ($Arguments -join " ")
  $psi.WorkingDirectory = $RepoPath
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $process = [Diagnostics.Process]::Start($psi)
  $stdout = $process.StandardOutput.ReadToEnd()
  [void]$process.StandardError.ReadToEnd()
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) {
    return ""
  }
  return $stdout.Trim()
}

function Get-SourceHash {
  param([string]$RepoPath)
  $status = Get-GitText -RepoPath $RepoPath -Arguments @("status", "--short", "--untracked-files=no")
  $diff = Get-GitText -RepoPath $RepoPath -Arguments @("diff", "--binary", "HEAD", "--")
  $payload = $status + "`n" + $diff
  $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    return (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join "")
  } finally {
    $sha.Dispose()
  }
}

function Get-GitStatusLines {
  param([string]$RepoPath)
  $text = Get-GitText -RepoPath $RepoPath -Arguments @("status", "--short")
  if ([string]::IsNullOrWhiteSpace($text)) {
    return @()
  }
  return @($text -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Convert-CodePointsToString {
  param([int[]]$CodePoints)
  $builder = New-Object System.Text.StringBuilder
  foreach ($codePoint in $CodePoints) {
    [void]$builder.Append([char]$codePoint)
  }
  return $builder.ToString()
}

function Get-ZhReleaseText {
  param([string]$Key)
  switch ($Key) {
    "VersionFixRecord" { return Convert-CodePointsToString @(0x7248, 0x672C, 0x4FEE, 0x590D, 0x8BB0, 0x5F55) }
    "VersionTime" { return Convert-CodePointsToString @(0x7248, 0x672C, 0x65F6, 0x95F4, 0xFF1A) }
    "VersionNumber" { return Convert-CodePointsToString @(0x7248, 0x672C, 0x53F7, 0xFF1A) }
    "Branch" { return Convert-CodePointsToString @(0x5206, 0x652F, 0xFF1A) }
    "ReleaseCommit" { return Convert-CodePointsToString @(0x53D1, 0x7248, 0x63D0, 0x4EA4, 0xFF1A) }
    "ReadmeLatest" { return "README " + (Convert-CodePointsToString @(0x6700, 0x65B0, 0x8BB0, 0x5F55, 0xFF1A)) }
    "RecentCommits" { return Convert-CodePointsToString @(0x6700, 0x8FD1, 0x63D0, 0x4EA4, 0xFF1A) }
    "Unavailable" { return Convert-CodePointsToString @(0x4E0D, 0x53EF, 0x7528) }
    "MiniProgram" { return Convert-CodePointsToString @(0x5C0F, 0x7A0B, 0x5E8F) }
    "IotCard" { return Convert-CodePointsToString @(0x7269, 0x5361) }
    "Public" { return Convert-CodePointsToString @(0x516C, 0x7248) }
    "MiniProgramIotPublic" { return Convert-CodePointsToString @(0x5C0F, 0x7A0B, 0x5E8F, 0x7269, 0x5361, 0x516C, 0x7248) }
    "MiniProgramPublic" { return Convert-CodePointsToString @(0x5C0F, 0x7A0B, 0x5E8F, 0x516C, 0x7248) }
    default { throw "Unknown zh release text key: $Key" }
  }
}

function Read-TextFile {
  param([string]$PathValue)
  $bytes = [System.IO.File]::ReadAllBytes($PathValue)
  if ($bytes.Length -eq 0) {
    return ""
  }
  $utf8Strict = New-Object System.Text.UTF8Encoding -ArgumentList $false, $true
  try {
    return $utf8Strict.GetString($bytes)
  } catch {
    return [System.Text.Encoding]::Default.GetString($bytes)
  }
}

function Write-Utf8BomTextFile {
  param(
    [string]$PathValue,
    [string]$Content
  )
  $utf8Bom = New-Object System.Text.UTF8Encoding -ArgumentList $true
  [System.IO.File]::WriteAllText($PathValue, $Content, $utf8Bom)
}

function Test-IsSourceLikePath {
  param([string]$PathValue)
  $normalized = $PathValue -replace '\\', '/'
  if ($normalized -match '^(out|build|\.cache|release_upload|logs?)/') {
    return $false
  }
  if ($normalized -match '^(gui|app|apps|product|services|middleware|driver|drivers|hal|inc|include|src|platform|components|custom|config)/') {
    return $true
  }
  if ($normalized -match '(^|/)(CMakeLists\.txt|Kconfig|Makefile)$') {
    return $true
  }
  return ($normalized -match '\.(c|h|cc|cpp|cxx|hpp|s|S|asm|ld|cmake|mk|json|bin)$')
}

function Assert-NoUntrackedSourceBeforeClean {
  param(
    [string]$RepoPath,
    [bool]$Allow
  )
  if ($Allow) {
    return
  }
  $untrackedSource = @()
  foreach ($line in Get-GitStatusLines -RepoPath $RepoPath) {
    if ($line.StartsWith("?? ")) {
      $pathValue = $line.Substring(3).Trim()
      if (Test-IsSourceLikePath -PathValue $pathValue) {
        $untrackedSource += $pathValue
      }
    }
  }
  if ($untrackedSource.Count -gt 0) {
    $listing = ($untrackedSource | ForEach-Object { "  $_" }) -join "`n"
    throw "Untracked source-like files exist and may be lost or omitted during clean release builds. Commit/stage them first, or rerun with -AllowUntrackedSource only if intentional.`n$listing"
  }
}

function Convert-MarkdownReleaseNotesToPlainText {
  param([string]$Markdown)
  $text = $Markdown
  $text = $text -replace '\r\n', "`n"
  $text = $text -replace '\r', "`n"
  $text = $text -replace '```[a-zA-Z0-9_-]*\n([\s\S]*?)```', '$1'
  $text = $text -replace '\|', ' '
  $text = $text -replace '`([^`]*)`', '$1'
  $text = $text -replace '\*\*([^*]*)\*\*', '$1'
  $text = $text -replace '(?m)^\s*\|?\s*-+\s*(\|\s*-+\s*)+\|?\s*$', ''
  $text = $text -replace '(?m)^\s*#+\s*', ''
  $text = $text -replace '\n{3,}', "`n`n"
  return $text.Trim()
}

function Get-TopReadmeSection {
  param([string]$RepoPath)
  $readmePath = Join-Path $RepoPath "README.md"
  if (-not (Test-Path -LiteralPath $readmePath -PathType Leaf)) {
    return ""
  }
  $text = Read-TextFile -PathValue $readmePath
  $matches = [regex]::Matches($text, "(?ms)^##\s+.*?(?=^##\s+|\z)")
  if ($matches.Count -lt 1) {
    return ""
  }
  return $matches[0].Value.Trim()
}

function Get-ReleaseReadmeTitle {
  param(
    [string]$DeviceVer,
    [string]$Branch,
    [string]$RemoteProductFolder
  )
  $model = ""
  if (-not [string]::IsNullOrWhiteSpace($DeviceVer)) {
    $model = @($DeviceVer -split "_")[0]
  }
  if ([string]::IsNullOrWhiteSpace($model)) {
    $model = "Firmware"
  }

  $profile = ""
  if (-not [string]::IsNullOrWhiteSpace($RemoteProductFolder)) {
    $parts = @($RemoteProductFolder -split "_" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $modelIndex = [Array]::IndexOf($parts, $model)
    if ($modelIndex -ge 0 -and $modelIndex -lt ($parts.Count - 1)) {
      $profile = (@($parts[($modelIndex + 1)..($parts.Count - 1)]) -join "")
    } elseif ($parts.Count -gt 0) {
      $profile = $parts[$parts.Count - 1]
    }
  }

  if ([string]::IsNullOrWhiteSpace($profile) -and -not [string]::IsNullOrWhiteSpace($Branch)) {
    $miniProgram = Get-ZhReleaseText "MiniProgram"
    $iotCard = Get-ZhReleaseText "IotCard"
    $public = Get-ZhReleaseText "Public"
    if ($Branch.Contains($miniProgram) -and $Branch.Contains($iotCard) -and $Branch.Contains($public)) {
      $profile = Get-ZhReleaseText "MiniProgramIotPublic"
    } elseif ($Branch.Contains($miniProgram) -and $Branch.Contains($public)) {
      $profile = Get-ZhReleaseText "MiniProgramPublic"
    } elseif ($Branch.Contains("APP") -and $Branch.Contains($public)) {
      $profile = "APP" + $public
    }
  }

  if ([string]::IsNullOrWhiteSpace($profile)) {
    return "$model $(Get-ZhReleaseText "VersionFixRecord")"
  }
  return "$model $profile$(Get-ZhReleaseText "VersionFixRecord")"
}

function New-DefaultReleaseReadme {
  param(
    [string]$RepoPath,
    [string]$OutputPath,
    [string]$ReleaseTimeValue,
    [string]$DeviceVer,
    [string]$Branch,
    [string]$Commit,
    [string]$RemoteProductFolder
  )
  $section = Get-TopReadmeSection -RepoPath $RepoPath
  $commitLines = Get-GitText -RepoPath $RepoPath -Arguments @("log", "--oneline", "-5")
  $content = @()
  $content += Get-ReleaseReadmeTitle -DeviceVer $DeviceVer -Branch $Branch -RemoteProductFolder $RemoteProductFolder
  $content += ""
  $content += "$(Get-ZhReleaseText "VersionTime")$ReleaseTimeValue"
  $content += "$(Get-ZhReleaseText "VersionNumber")$DeviceVer"
  $content += "$(Get-ZhReleaseText "Branch")$Branch"
  $content += "$(Get-ZhReleaseText "ReleaseCommit")$Commit"
  $content += ""
  if (-not [string]::IsNullOrWhiteSpace($section)) {
    $content += Get-ZhReleaseText "ReadmeLatest"
    $content += Convert-MarkdownReleaseNotesToPlainText -Markdown $section
    $content += ""
  }
  $content += Get-ZhReleaseText "RecentCommits"
  if ([string]::IsNullOrWhiteSpace($commitLines)) {
    $content += "(" + (Get-ZhReleaseText "Unavailable") + ")"
  } else {
    $content += @($commitLines -split "`r?`n")
  }

  $dir = Split-Path -Parent $OutputPath
  if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
  }
  Write-Utf8BomTextFile -PathValue $OutputPath -Content ($content -join "`r`n")
  Write-Host "Generated release readme: $OutputPath"
}

function Get-JsonProperty {
  param(
    [object]$ObjectValue,
    [string]$Name
  )
  if ($null -eq $ObjectValue) {
    return $null
  }
  $prop = $ObjectValue.PSObject.Properties[$Name]
  if ($null -eq $prop) {
    return $null
  }
  return $prop.Value
}

function Read-ReleaseState {
  param([string]$StatePath)
  if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
    return $null
  }
  return Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
}

function Test-StatePlanMatch {
  param(
    [object]$State,
    [string]$RepoPath,
    [string]$Branch,
    [string]$Commit,
    [string]$ReleaseTimeValue,
    [string]$DeviceVer,
    [string]$TargetValue,
    [string]$PSModeValue,
    [string]$TargetOSValue,
    [string]$ChipIdValue
  )
  if ($null -eq $State) {
    return $false
  }
  return (
    (Get-JsonProperty $State "repo") -eq $RepoPath -and
    (Get-JsonProperty $State "branch") -eq $Branch -and
    (Get-JsonProperty $State "commit") -eq $Commit -and
    (Get-JsonProperty $State "release_time") -eq $ReleaseTimeValue -and
    (Get-JsonProperty $State "device_ver") -eq $DeviceVer -and
    (Get-JsonProperty $State "target") -eq $TargetValue -and
    (Get-JsonProperty $State "ps_mode") -eq $PSModeValue -and
    (Get-JsonProperty $State "target_os") -eq $TargetOSValue -and
    (Get-JsonProperty $State "chip_id") -eq $ChipIdValue
  )
}

function Test-StateStage {
  param(
    [object]$State,
    [string]$StageName,
    [string]$SourceHash
  )
  if ($null -eq $State) {
    return $false
  }
  if ((Get-JsonProperty $State "source_hash") -ne $SourceHash) {
    return $false
  }
  return ((Get-JsonProperty $State $StageName) -eq $true)
}

function Save-ReleaseState {
  param(
    [string]$StatePath,
    [object]$OldState,
    [string]$StageName,
    [string]$RepoPath,
    [string]$Branch,
    [string]$Commit,
    [string]$SourceHash,
    [string]$ReleaseTimeValue,
    [string]$DeviceVer,
    [string]$TargetValue,
    [string]$PSModeValue,
    [string]$TargetOSValue,
    [string]$ChipIdValue,
    [string]$UploadDir,
    [string[]]$Files
  )

  $buildSucceeded = (Get-JsonProperty $OldState "build_succeeded") -eq $true
  $packageSucceeded = (Get-JsonProperty $OldState "package_succeeded") -eq $true
  $uploadSucceeded = (Get-JsonProperty $OldState "upload_succeeded") -eq $true

  if ($StageName -eq "build") {
    $buildSucceeded = $true
    $packageSucceeded = $false
    $uploadSucceeded = $false
  } elseif ($StageName -eq "package") {
    $buildSucceeded = $true
    $packageSucceeded = $true
    $uploadSucceeded = $false
  } elseif ($StageName -eq "upload") {
    $buildSucceeded = $true
    $packageSucceeded = $true
    $uploadSucceeded = $true
  }

  $state = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    repo = $RepoPath
    branch = $Branch
    commit = $Commit
    source_hash = $SourceHash
    release_time = $ReleaseTimeValue
    device_ver = $DeviceVer
    target = $TargetValue
    ps_mode = $PSModeValue
    target_os = $TargetOSValue
    chip_id = $ChipIdValue
    build_succeeded = $buildSucceeded
    package_succeeded = $packageSucceeded
    upload_succeeded = $uploadSucceeded
    upload_dir = $UploadDir
    files = $Files
  }

  $stateDir = Split-Path -Parent $StatePath
  if (-not (Test-Path -LiteralPath $stateDir -PathType Container)) {
    New-Item -ItemType Directory -Path $stateDir | Out-Null
  }
  $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

$RepoPath = Resolve-ExistingOrFullPath $Repo
if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
  throw "Repo does not exist: $RepoPath"
}

if ([string]::IsNullOrWhiteSpace($ReleaseTime)) {
  $ReleaseTime = Get-Date -Format "yyyyMMdd_HHmm"
}
if ($ReleaseTime -notmatch '^\d{8}_\d{4}$') {
  throw "ReleaseTime must be YYYYMMDD_HHMM: $ReleaseTime"
}

$SkillDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$PrepareScript = Join-Path $SkillDir "scripts\prepare_release_package.py"
$UploadScript = Join-Path $SkillDir "scripts\fnos_upload_release.js"
$BundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$BundledNodePath = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"
$BundledPnpmNodePath = Join-Path $BundledNodePath ".pnpm\node_modules"
$BundledNodePathEntries = @($BundledNodePath)
if (Test-Path -LiteralPath $BundledPnpmNodePath -PathType Container) {
  $BundledNodePathEntries += $BundledPnpmNodePath
}
$BundledNodePathValue = $BundledNodePathEntries -join [System.IO.Path]::PathSeparator
$Node = if (Test-Path -LiteralPath $BundledNode -PathType Leaf) { $BundledNode } else { "node" }
$Python = "python"

$Branch = Get-GitText -RepoPath $RepoPath -Arguments @("branch", "--show-current")
$Commit = Get-GitText -RepoPath $RepoPath -Arguments @("rev-parse", "--short", "HEAD")
if ([string]::IsNullOrWhiteSpace($Branch)) { $Branch = "(unknown)" }
if ([string]::IsNullOrWhiteSpace($Commit)) { $Commit = "(unknown)" }

$YlH = Join-Path $RepoPath "gui\lv_watch\lv_apps\yl\yl.h"
if (-not (Test-Path -LiteralPath $YlH -PathType Leaf)) {
  throw "Missing yl.h: $YlH"
}
$YlText = Get-Content -LiteralPath $YlH -Raw
$DeviceMatch = [regex]::Match($YlText, '#define\s+yl_device_ver\s+"([^"]+)"')
if (-not $DeviceMatch.Success) {
  throw "Could not find yl_device_ver in $YlH"
}
$CurrentDeviceVer = $DeviceMatch.Groups[1].Value
$ReleaseToken = "_" + $ReleaseTime + "_"
$RewrittenDeviceVer = [regex]::Replace($CurrentDeviceVer, '_(\d{8}_\d{4})_', $ReleaseToken, 1)
if ($RewrittenDeviceVer -eq $CurrentDeviceVer -and -not $CurrentDeviceVer.Contains($ReleaseToken)) {
  throw "Could not replace timestamp in yl_device_ver: $CurrentDeviceVer"
}
$IntendedDeviceVer = if ($KeepYlVersion) { $CurrentDeviceVer } else { $RewrittenDeviceVer }

$ProductDir = Join-Path $RepoPath "out\product\$Target"
$UploadDir = Join-Path $ProductDir "release_upload\$ReleaseTime"
$ExpectedZip = Join-Path $UploadDir "$IntendedDeviceVer.zip"
$ExpectedMdb = Join-Path $UploadDir "$IntendedDeviceVer.mdb.txt"
$ExpectedReadme = Join-Path $UploadDir "readme.txt"
$StatePath = Join-Path $UploadDir ".akq_release_state.json"
$IncludeReadme = -not $NoReadme
$State = Read-ReleaseState -StatePath $StatePath
$StatePlanMatches = Test-StatePlanMatch -State $State -RepoPath $RepoPath -Branch $Branch -Commit $Commit -ReleaseTimeValue $ReleaseTime -DeviceVer $IntendedDeviceVer -TargetValue $Target -PSModeValue $PSMode -TargetOSValue $TargetOS -ChipIdValue $ChipId
$StateSaysUploaded = $StatePlanMatches -and ((Get-JsonProperty $State "upload_succeeded") -eq $true)

Write-Host "repo: $RepoPath"
Write-Host "branch: $Branch"
Write-Host "commit: $Commit"
Write-Host "release_time: $ReleaseTime"
Write-Host "yl_device_ver: $IntendedDeviceVer"
if ($KeepYlVersion) {
  Write-Host "keep_yl_version: true; release_time is used only for release folder and local upload directory."
}
Write-Host "target: $Target"
Write-Host "build_env: PS_MODE=$PSMode TARGET_OS=$TargetOS CHIP_ID=$ChipId"
Write-Host "upload_dir: $UploadDir"

$UploadBaseArgs = @($UploadScript, "--repo", $RepoPath, "--release-time", $ReleaseTime)
if ($KeepYlVersion) {
  $UploadBaseArgs += "--keep-device-ver"
}
if (-not [string]::IsNullOrWhiteSpace($RemoteProductFolder)) {
  $UploadBaseArgs += @("--remote-product-folder", $RemoteProductFolder)
}
if (-not [string]::IsNullOrWhiteSpace($Readme)) {
  $UploadBaseArgs += "--include-readme"
} elseif ($IncludeReadme) {
  $UploadBaseArgs += "--include-readme"
}
if ($Headed) {
  $UploadBaseArgs += "--headed"
}

if (-not $NoPreflight -and -not $StateSaysUploaded -and -not $TrustExistingPackage) {
  $preflightArgs = @($UploadBaseArgs + "--preflight")
  Invoke-Checked -Command $Node -Arguments $preflightArgs -WorkingDirectory $RepoPath -Environment @{ NODE_PATH = $BundledNodePathValue }
} elseif ($StateSaysUploaded) {
  Write-Host "resume: previous state says upload already succeeded; final upload step will verify identical remote files."
} elseif ($TrustExistingPackage) {
  Write-Host "resume: trusting existing package; skipping collision-only preflight and verifying in upload step."
}

$updateArgs = @($PrepareScript, "--repo", $RepoPath, "--release-time", $ReleaseTime, "--update-yl-only")
if ($KeepYlVersion) {
  $updateArgs += @("--no-update-yl", "--keep-device-ver")
}
if ($DryRun) {
  $updateArgs += "--dry-run"
}
Invoke-Checked -Command $Python -Arguments $updateArgs -WorkingDirectory $RepoPath

if ($DryRun) {
  Write-Host "dry_run: no build, package, or upload performed."
  exit 0
}

$SourceHash = Get-SourceHash -RepoPath $RepoPath
$State = Read-ReleaseState -StatePath $StatePath
$StatePlanMatches = Test-StatePlanMatch -State $State -RepoPath $RepoPath -Branch $Branch -Commit $Commit -ReleaseTimeValue $ReleaseTime -DeviceVer $IntendedDeviceVer -TargetValue $Target -PSModeValue $PSMode -TargetOSValue $TargetOS -ChipIdValue $ChipId
if (-not $StatePlanMatches) {
  $State = $null
}

$packageExists = (Test-Path -LiteralPath $ExpectedZip -PathType Leaf) -and (Test-Path -LiteralPath $ExpectedMdb -PathType Leaf)
$packageStateOk = $packageExists -and (Test-StateStage -State $State -StageName "package_succeeded" -SourceHash $SourceHash)
$buildStateOk = (Test-StateStage -State $State -StageName "build_succeeded" -SourceHash $SourceHash)
$stateSourceHash = Get-JsonProperty $State "source_hash"

if ($packageExists -and $StatePlanMatches -and $null -ne $stateSourceHash -and $stateSourceHash -ne $SourceHash -and -not $ForceCleanBuild -and -not $TrustExistingPackage) {
  throw "Existing release package/checkpoint uses the same release time but a different source state. Use a new -ReleaseTime for a new build, pass -TrustExistingPackage to verify/upload the existing package, or pass -ForceCleanBuild only if rebuilding this same timestamp is intentional."
}

if ($packageStateOk -and -not $ForceCleanBuild) {
  Write-Host "resume: package already prepared for the same source state; skipping clean/build/package."
} elseif ($packageExists -and $TrustExistingPackage -and -not $ForceCleanBuild) {
  Write-Host "resume: trusting existing package files by request; skipping clean/build/package."
} else {
  $buildEnv = @{
    PS_MODE = $PSMode
    TARGET_OS = $TargetOS
    CHIP_ID = $ChipId
  }

  if ($buildStateOk -and -not $ForceCleanBuild) {
    Write-Host "resume: build already succeeded for the same source state; skipping clean/build."
  } else {
    Assert-NoUntrackedSourceBeforeClean -RepoPath $RepoPath -Allow ([bool]$AllowUntrackedSource)
    Invoke-Checked -Command "make" -Arguments @("clean") -WorkingDirectory $RepoPath -Environment $buildEnv
    Invoke-Checked -Command "make" -Arguments @($Target) -WorkingDirectory $RepoPath -Environment $buildEnv
    $stateFiles = @($ExpectedZip, $ExpectedMdb)
    if ($IncludeReadme) { $stateFiles += $ExpectedReadme }
    Save-ReleaseState -StatePath $StatePath -OldState $State -StageName "build" -RepoPath $RepoPath -Branch $Branch -Commit $Commit -SourceHash $SourceHash -ReleaseTimeValue $ReleaseTime -DeviceVer $IntendedDeviceVer -TargetValue $Target -PSModeValue $PSMode -TargetOSValue $TargetOS -ChipIdValue $ChipId -UploadDir $UploadDir -Files $stateFiles
    $State = Read-ReleaseState -StatePath $StatePath
  }

  $packageArgs = @($PrepareScript, "--repo", $RepoPath, "--release-time", $ReleaseTime, "--product-dir", $ProductDir, "--overwrite")
  if ($KeepYlVersion) {
    $packageArgs += @("--no-update-yl", "--keep-device-ver")
  }
  if (-not [string]::IsNullOrWhiteSpace($Readme)) {
    $ReadmePath = Resolve-ExistingOrFullPath $Readme
    $packageArgs += @("--readme", $ReadmePath)
  }
  Invoke-Checked -Command $Python -Arguments $packageArgs -WorkingDirectory $RepoPath
  $stateFiles = @($ExpectedZip, $ExpectedMdb)
  if ($IncludeReadme) { $stateFiles += $ExpectedReadme }
  Save-ReleaseState -StatePath $StatePath -OldState $State -StageName "package" -RepoPath $RepoPath -Branch $Branch -Commit $Commit -SourceHash $SourceHash -ReleaseTimeValue $ReleaseTime -DeviceVer $IntendedDeviceVer -TargetValue $Target -PSModeValue $PSMode -TargetOSValue $TargetOS -ChipIdValue $ChipId -UploadDir $UploadDir -Files $stateFiles
  $State = Read-ReleaseState -StatePath $StatePath
}

if ($IncludeReadme -and [string]::IsNullOrWhiteSpace($Readme)) {
  New-DefaultReleaseReadme -RepoPath $RepoPath -OutputPath $ExpectedReadme -ReleaseTimeValue $ReleaseTime -DeviceVer $IntendedDeviceVer -Branch $Branch -Commit $Commit -RemoteProductFolder $RemoteProductFolder
}

if ($NoUpload) {
  Write-Host "no_upload: package is ready at $UploadDir"
  exit 0
}

$uploadArgs = @($UploadBaseArgs + "--allow-existing-identical")
if ($ReplaceExisting) {
  $uploadArgs += "--replace-existing"
}
Invoke-Checked -Command $Node -Arguments $uploadArgs -WorkingDirectory $RepoPath -Environment @{ NODE_PATH = $BundledNodePathValue }

$stateFiles = @($ExpectedZip, $ExpectedMdb)
if ($IncludeReadme) { $stateFiles += $ExpectedReadme }
Save-ReleaseState -StatePath $StatePath -OldState $State -StageName "upload" -RepoPath $RepoPath -Branch $Branch -Commit $Commit -SourceHash $SourceHash -ReleaseTimeValue $ReleaseTime -DeviceVer $IntendedDeviceVer -TargetValue $Target -PSModeValue $PSMode -TargetOSValue $TargetOS -ChipIdValue $ChipId -UploadDir $UploadDir -Files $stateFiles
Write-Host "done: release uploaded and verified."
