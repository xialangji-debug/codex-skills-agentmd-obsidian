[CmdletBinding()]
param(
  [ValidateSet('Backup', 'List', 'Restore')]
  [string]$Action = 'Backup',
  [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex'),
  [string]$BackupRoot,
  [string]$BackupPath,
  [switch]$IncludeSystemSkills,
  [switch]$IncludeDependencyDirs,
  [switch]$IncludePluginCache,
  [switch]$IncludeTmpBundledMarketplaces
)

$ErrorActionPreference = 'Stop'
$LogPrefix = '[codex-backup]'
if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
  $BackupRoot = Join-Path $CodexHome 'backups\portable-state'
}

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

function Write-JsonFile {
  param(
    [string]$Path,
    [object]$Value
  )
  Write-Utf8NoBom $Path (($Value | ConvertTo-Json -Depth 40) + "`n")
}

function Resolve-OrCreateDirectory {
  param([string]$Path)
  New-Item -ItemType Directory -Force -Path $Path | Out-Null
  return (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Resolve-ExistingDirectory {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
    throw "missing required directory: $Path"
  }
  return (Resolve-Path -LiteralPath $Path).ProviderPath
}

function Assert-UnderPath {
  param(
    [string]$Path,
    [string]$Parent
  )
  $full = [System.IO.Path]::GetFullPath($Path)
  $root = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
  if (-not $full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "refusing to modify path outside expected root: $full"
  }
}

function Copy-FileIfExists {
  param(
    [string]$Source,
    [string]$Destination
  )
  if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
    return $false
  }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
  Copy-Item -LiteralPath $Source -Destination $Destination -Force
  return $true
}

function Invoke-RobocopyDirectory {
  param(
    [string]$Source,
    [string]$Destination,
    [string[]]$ExcludeDirs = @()
  )
  if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    return $false
  }

  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  $args = @($Source, $Destination, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
  if ($ExcludeDirs.Count -gt 0) {
    $args += '/XD'
    foreach ($dir in $ExcludeDirs) {
      if ([System.IO.Path]::IsPathRooted($dir)) {
        $args += $dir
      } else {
        $args += $dir
      }
    }
  }

  & robocopy.exe @args | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed while copying $Source -> $Destination (exit code $LASTEXITCODE)"
  }
  return $true
}

function Get-PortableDirectoryExcludes {
  if ($IncludeDependencyDirs) {
    return @()
  }

  return @(
    '.git',
    'node_modules',
    '.venv',
    'venv',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.next',
    '.turbo',
    'dist',
    'build',
    'target',
    'coverage'
  )
}

function Export-McpServers {
  param(
    [string]$ConfigPath,
    [string]$TargetPath
  )
  if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    return $false
  }

  $python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $python) {
    Write-Log 'warning: python not found; skipping mcp_servers.json export'
    return $false
  }

  $script = @'
import json
import pathlib
import sys
import tomllib

config_path = pathlib.Path(sys.argv[1])
target_path = pathlib.Path(sys.argv[2])
data = tomllib.loads(config_path.read_text(encoding="utf-8"))
mcp_servers = data.get("mcp_servers", {})
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path.write_text(json.dumps(mcp_servers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
'@
  $temp = Join-Path $env:TEMP ('codex-mcp-export-' + [guid]::NewGuid().ToString('N') + '.py')
  try {
    Write-Utf8NoBom $temp $script
    & $python.Source $temp $ConfigPath $TargetPath
    if ($LASTEXITCODE -ne 0) {
      Write-Log 'warning: failed to export mcp_servers.json from config.toml'
      return $false
    }
    return $true
  } finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
  }
}

function Test-TomlSyntax {
  param([string]$ConfigPath)
  if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    return
  }

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
    & $python.Source $temp $ConfigPath
    if ($LASTEXITCODE -ne 0) {
      throw "tomllib validation failed for $ConfigPath"
    }
  } finally {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
  }
}

function New-CodexStateBackup {
  $codexHomeResolved = Resolve-ExistingDirectory $CodexHome
  $backupRootResolved = Resolve-OrCreateDirectory $BackupRoot
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  $backupDir = Join-Path $backupRootResolved $stamp
  if (Test-Path -LiteralPath $backupDir) {
    $backupDir = Join-Path $backupRootResolved "$stamp-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
  }
  New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

  $configCopied = Copy-FileIfExists (Join-Path $codexHomeResolved 'config.toml') (Join-Path $backupDir 'config.toml')
  $mcpExported = Export-McpServers (Join-Path $codexHomeResolved 'config.toml') (Join-Path $backupDir 'mcp_servers.json')
  $chromeStateCopied = Copy-FileIfExists (Join-Path $codexHomeResolved 'chrome-native-hosts.json') (Join-Path $backupDir 'chrome-native-hosts.json')

  $skillExcludes = @()
  if (-not $IncludeSystemSkills) {
    $skillExcludes += '.system'
  }
  $portableExcludes = Get-PortableDirectoryExcludes
  $skillExcludes += $portableExcludes
  $skillsCopied = Invoke-RobocopyDirectory (Join-Path $codexHomeResolved 'skills') (Join-Path $backupDir 'skills') $skillExcludes
  $marketplacesCopied = Invoke-RobocopyDirectory (Join-Path $codexHomeResolved 'marketplaces') (Join-Path $backupDir 'marketplaces') $portableExcludes

  $tmpBundledCopied = $false
  if ($IncludeTmpBundledMarketplaces) {
    $tmpBundledCopied = Invoke-RobocopyDirectory (Join-Path $codexHomeResolved '.tmp\bundled-marketplaces') (Join-Path $backupDir 'tmp-bundled-marketplaces')
  }

  $pluginCacheCopied = $false
  if ($IncludePluginCache) {
    $pluginCacheCopied = Invoke-RobocopyDirectory (Join-Path $codexHomeResolved 'plugins\cache') (Join-Path $backupDir 'plugins-cache')
  }

  $manifest = [ordered]@{
    created_at = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    codex_home = $codexHomeResolved
    backup_path = $backupDir
    included = [ordered]@{
      config_toml = $configCopied
      mcp_servers_json = $mcpExported
      skills = $skillsCopied
      system_skills = [bool]$IncludeSystemSkills
      marketplaces = $marketplacesCopied
      dependency_dirs = [bool]$IncludeDependencyDirs
      chrome_native_hosts = $chromeStateCopied
      tmp_bundled_marketplaces = $tmpBundledCopied
      plugin_cache = $pluginCacheCopied
    }
  }
  Write-JsonFile (Join-Path $backupDir 'manifest.json') $manifest
  Write-Log "backup created: $backupDir"
}

function Get-BackupInfo {
  param([string]$Dir)
  $manifestPath = Join-Path $Dir 'manifest.json'
  $manifest = $null
  if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
    try {
      $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    } catch {
      $manifest = $null
    }
  }

  [pscustomobject]@{
    Name = Split-Path -Leaf $Dir
    CreatedAt = if ($manifest) { $manifest.created_at } else { (Get-Item -LiteralPath $Dir).LastWriteTime.ToString('s') }
    Config = Test-Path -LiteralPath (Join-Path $Dir 'config.toml') -PathType Leaf
    MCP = Test-Path -LiteralPath (Join-Path $Dir 'mcp_servers.json') -PathType Leaf
    Skills = Test-Path -LiteralPath (Join-Path $Dir 'skills') -PathType Container
    Marketplaces = Test-Path -LiteralPath (Join-Path $Dir 'marketplaces') -PathType Container
    Path = $Dir
  }
}

function Show-CodexStateBackups {
  $backupRootResolved = Resolve-OrCreateDirectory $BackupRoot
  $items = Get-ChildItem -LiteralPath $backupRootResolved -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    ForEach-Object { Get-BackupInfo $_.FullName }

  if (-not $items) {
    Write-Log "no backups found under $backupRootResolved"
    return
  }
  $items | Format-Table -AutoSize
}

function Backup-CurrentStateBeforeRestore {
  param(
    [string]$CodexHomeResolved,
    [string]$BackupRootResolved
  )

  $rollbackDir = Join-Path $BackupRootResolved ('restore-rollback-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
  New-Item -ItemType Directory -Force -Path $rollbackDir | Out-Null

  Copy-FileIfExists (Join-Path $CodexHomeResolved 'config.toml') (Join-Path $rollbackDir 'config.toml') | Out-Null
  Copy-FileIfExists (Join-Path $CodexHomeResolved 'chrome-native-hosts.json') (Join-Path $rollbackDir 'chrome-native-hosts.json') | Out-Null
  Invoke-RobocopyDirectory (Join-Path $CodexHomeResolved 'skills') (Join-Path $rollbackDir 'skills') | Out-Null
  Invoke-RobocopyDirectory (Join-Path $CodexHomeResolved 'marketplaces') (Join-Path $rollbackDir 'marketplaces') | Out-Null

  Write-JsonFile (Join-Path $rollbackDir 'manifest.json') ([ordered]@{
    created_at = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    codex_home = $CodexHomeResolved
    reason = 'automatic rollback snapshot before restore'
  })
  return $rollbackDir
}

function Restore-CodexStateBackup {
  if ([string]::IsNullOrWhiteSpace($BackupPath)) {
    throw 'Restore requires -BackupPath <path>'
  }

  $backupResolved = Resolve-ExistingDirectory $BackupPath
  $codexHomeResolved = Resolve-OrCreateDirectory $CodexHome
  $backupRootResolved = Resolve-OrCreateDirectory $BackupRoot

  Assert-UnderPath (Join-Path $codexHomeResolved 'skills') $codexHomeResolved
  Assert-UnderPath (Join-Path $codexHomeResolved 'marketplaces') $codexHomeResolved
  Assert-UnderPath (Join-Path $codexHomeResolved 'plugins\cache') $codexHomeResolved

  $rollbackDir = Backup-CurrentStateBeforeRestore $codexHomeResolved $backupRootResolved

  Copy-FileIfExists (Join-Path $backupResolved 'config.toml') (Join-Path $codexHomeResolved 'config.toml') | Out-Null
  Copy-FileIfExists (Join-Path $backupResolved 'chrome-native-hosts.json') (Join-Path $codexHomeResolved 'chrome-native-hosts.json') | Out-Null
  Invoke-RobocopyDirectory (Join-Path $backupResolved 'skills') (Join-Path $codexHomeResolved 'skills') | Out-Null
  Invoke-RobocopyDirectory (Join-Path $backupResolved 'marketplaces') (Join-Path $codexHomeResolved 'marketplaces') | Out-Null

  if ($IncludeTmpBundledMarketplaces) {
    Invoke-RobocopyDirectory (Join-Path $backupResolved 'tmp-bundled-marketplaces') (Join-Path $codexHomeResolved '.tmp\bundled-marketplaces') | Out-Null
  }
  if ($IncludePluginCache) {
    Invoke-RobocopyDirectory (Join-Path $backupResolved 'plugins-cache') (Join-Path $codexHomeResolved 'plugins\cache') | Out-Null
  }

  Test-TomlSyntax (Join-Path $codexHomeResolved 'config.toml')
  Write-Log "restore completed from: $backupResolved"
  Write-Log "rollback snapshot before restore: $rollbackDir"
}

switch ($Action) {
  'Backup' { New-CodexStateBackup }
  'List' { Show-CodexStateBackups }
  'Restore' { Restore-CodexStateBackup }
}
