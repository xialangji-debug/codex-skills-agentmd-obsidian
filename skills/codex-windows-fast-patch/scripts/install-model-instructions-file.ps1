[CmdletBinding()]
param(
  [string]$PromptSource,
  [string]$PromptDestination = (Join-Path $env:USERPROFILE '.codex\prompts\system-prompt.md'),
  [string]$ConfigPath = (Join-Path $env:USERPROFILE '.codex\config.toml'),
  [switch]$NoCopy,
  [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$LogPrefix = '[codex-model-instructions]'
$ScriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }

function Write-Log {
  param([string]$Message)
  Write-Host "$LogPrefix $Message"
}

function Write-Utf8NoBom {
  param(
    [string]$Path,
    [string]$Content
  )
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
  $encoding = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Backup-ConfigBeforeOverwrite {
  param(
    [string]$Path,
    [string]$Reason = 'model-instructions-file'
  )

  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    return
  }

  $fullPath = [System.IO.Path]::GetFullPath($Path)
  $configDir = Split-Path -Parent $fullPath
  $backupRoot = Join-Path $configDir 'backups\config'
  New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

  $safeReason = ([string]$Reason -replace '[^A-Za-z0-9_.-]', '-').Trim('-')
  if ([string]::IsNullOrWhiteSpace($safeReason)) {
    $safeReason = 'model-instructions-file'
  }

  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
  $backupPath = Join-Path $backupRoot "config.toml.$stamp.$safeReason.bak"
  Copy-Item -LiteralPath $fullPath -Destination $backupPath -Force
  Write-Log "config.toml backup before overwrite: $backupPath"
}

function Get-DefaultPromptSource {
  $skillRoot = Split-Path -Parent $ScriptRoot
  return (Join-Path $skillRoot 'assets\system-prompt.md')
}

function ConvertTo-TomlLiteralString {
  param([string]$Value)
  $escaped = [string]$Value -replace "'", "''"
  return "'$escaped'"
}

function Set-TomlTopLevelString {
  param(
    [string]$Path,
    [string]$Key,
    [string]$Value
  )

  $content = ''
  if (Test-Path -LiteralPath $Path) {
    $content = [System.IO.File]::ReadAllText($Path, [System.Text.UTF8Encoding]::new($false))
  }

  $line = "$Key = $(ConvertTo-TomlLiteralString $Value)"
  $tableMatch = [regex]::Match($content, '(?m)^\s*\[')
  if ($tableMatch.Success) {
    $prefix = $content.Substring(0, $tableMatch.Index)
    $suffix = $content.Substring($tableMatch.Index)
  } else {
    $prefix = $content
    $suffix = ''
  }

  $keyPattern = "(?m)^\s*$([regex]::Escape($Key))\s*=.*$"
  $keyRegex = [regex]::new($keyPattern)
  if ($keyRegex.IsMatch($prefix)) {
    $prefix = $keyRegex.Replace($prefix, $line, 1)
  } else {
    if ($prefix.Length -gt 0 -and -not $prefix.EndsWith("`n")) {
      $prefix += "`r`n"
    }
    $prefix += "$line`r`n"
  }

  if ($suffix.Length -gt 0 -and -not $prefix.EndsWith("`r`n`r`n") -and -not $prefix.EndsWith("`n`n")) {
    $prefix += "`r`n"
  }

  Backup-ConfigBeforeOverwrite $Path "set-$Key"
  Write-Utf8NoBom $Path ($prefix + $suffix)
}

function Get-TomlTopLevelString {
  param(
    [string]$Path,
    [string]$Key
  )

  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    return $null
  }

  $content = [System.IO.File]::ReadAllText($Path, [System.Text.UTF8Encoding]::new($false))
  $tableMatch = [regex]::Match($content, '(?m)^\s*\[')
  if ($tableMatch.Success) {
    $prefix = $content.Substring(0, $tableMatch.Index)
  } else {
    $prefix = $content
  }

  $match = [regex]::Match($prefix, "(?m)^\s*$([regex]::Escape($Key))\s*=\s*(?<value>.+?)\s*$")
  if (-not $match.Success) {
    return $null
  }

  $raw = $match.Groups['value'].Value.Trim()
  if ($raw.StartsWith("'") -and $raw.EndsWith("'") -and $raw.Length -ge 2) {
    return $raw.Substring(1, $raw.Length - 2).Replace("''", "'")
  }
  if ($raw.StartsWith('"') -and $raw.EndsWith('"') -and $raw.Length -ge 2) {
    return $raw.Substring(1, $raw.Length - 2)
  }
  return $raw
}

function Normalize-PathForCompare {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) {
    return ''
  }
  $value = [string]$Path
  if ($value.StartsWith('\\?\')) {
    $value = $value.Substring(4)
  }
  return [System.IO.Path]::GetFullPath($value).TrimEnd('\')
}

function Test-TomlSyntax {
  param([string]$Path)

  $python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $python) {
    Write-Log 'warning: python not found; skipping tomllib syntax validation'
    return
  }

  $script = @'
import pathlib
import sys
import tomllib

path = pathlib.Path(sys.argv[1])
tomllib.loads(path.read_text(encoding="utf-8"))
'@
  $temp = Join-Path $env:TEMP ('codex-toml-validate-' + [guid]::NewGuid().ToString('N') + '.py')
  try {
    Write-Utf8NoBom $temp $script
    & $python.Source $temp $Path
    if ($LASTEXITCODE -ne 0) {
      throw "tomllib validation failed for $Path"
    }
  } finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
  }
}

if ([string]::IsNullOrWhiteSpace($PromptSource)) {
  $PromptSource = Get-DefaultPromptSource
}

$destinationFullPath = [System.IO.Path]::GetFullPath($PromptDestination)

if ($VerifyOnly) {
  if (-not (Test-Path -LiteralPath $destinationFullPath -PathType Leaf)) {
    throw "model instructions file is missing: $destinationFullPath"
  }

  $configured = Get-TomlTopLevelString $ConfigPath 'model_instructions_file'
  if ([string]::IsNullOrWhiteSpace($configured)) {
    throw "config.toml is missing top-level model_instructions_file"
  }

  if ((Normalize-PathForCompare $configured) -ne (Normalize-PathForCompare $destinationFullPath)) {
    throw "model_instructions_file points to '$configured', expected '$destinationFullPath'"
  }

  Test-TomlSyntax $ConfigPath
  Write-Log "model instructions file verified: $destinationFullPath"
  exit 0
}

if ($NoCopy) {
  if (-not (Test-Path -LiteralPath $destinationFullPath -PathType Leaf)) {
    throw "PromptDestination does not exist and -NoCopy was set: $destinationFullPath"
  }
} else {
  if (-not (Test-Path -LiteralPath $PromptSource -PathType Leaf)) {
    throw "PromptSource not found: $PromptSource"
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationFullPath) | Out-Null
  Copy-Item -LiteralPath $PromptSource -Destination $destinationFullPath -Force
  Write-Log "model instructions file copied: $PromptSource -> $destinationFullPath"
}

Set-TomlTopLevelString $ConfigPath 'model_instructions_file' $destinationFullPath
Test-TomlSyntax $ConfigPath
Write-Log "configured model_instructions_file: $destinationFullPath"
Write-Log 'restart Codex CLI/Desktop or start a new session for the custom model instructions to take effect'
