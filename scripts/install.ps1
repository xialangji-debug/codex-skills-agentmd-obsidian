param(
  [string]$CodexHome = "$env:USERPROFILE\.codex",
  [string]$VaultPath = "$env:USERPROFILE\Documents\Obsidian\CodexVault",
  [switch]$SkipSkills,
  [switch]$SkipMcp,
  [switch]$SkipAgents,
  [switch]$SkipObsidian,
  [switch]$SkipObsidianInstall
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$SkillsSource = Join-Path $RepoRoot "skills"
$McpSource = Join-Path $RepoRoot "mcp"
$AgentsSource = Join-Path $RepoRoot "AGENTS.md"
$ObsidianSource = Join-Path $RepoRoot "obsidian\Codex"

function Test-ObsidianInstalled {
  $commands = @(Get-Command "Obsidian" -ErrorAction SilentlyContinue)

  $programFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
  $commonPaths = @(
    "$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe",
    "$env:ProgramFiles\Obsidian\Obsidian.exe"
  )
  if ($programFilesX86) {
    $commonPaths += (Join-Path $programFilesX86 "Obsidian\Obsidian.exe")
  }

  if ($commands.Count -gt 0) {
    return $true
  }

  foreach ($path in $commonPaths) {
    if ($path -and (Test-Path -LiteralPath $path)) {
      return $true
    }
  }

  return $false
}

function Ensure-ObsidianInstalled {
  if ($SkipObsidian -or $SkipObsidianInstall) {
    return
  }

  $obsidianInstalled = Test-ObsidianInstalled
  if ($obsidianInstalled) {
    Write-Host "Obsidian detected."
    return
  }

  $winget = Get-Command "winget" -ErrorAction SilentlyContinue
  if (-not $winget) {
    Write-Warning "Obsidian was not detected and winget is unavailable. Install Obsidian manually: https://obsidian.md/download"
    return
  }

  Write-Host "Obsidian was not detected. Installing Obsidian with winget..."
  winget install --id Obsidian.Obsidian --source winget --accept-source-agreements --accept-package-agreements
}

function Copy-DirectoryContents {
  param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Destination,
    [switch]$Overwrite
  )

  New-Item -ItemType Directory -Path $Destination -Force | Out-Null
  Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
    $target = Join-Path $Destination $_.Name
    if ($_.PSIsContainer) {
      if ($Overwrite -and (Test-Path -LiteralPath $target)) {
        Remove-Item -LiteralPath $target -Recurse -Force
      }
      Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    } else {
      if ($Overwrite -or -not (Test-Path -LiteralPath $target)) {
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
      }
    }
  }
}

function Get-PythonCommand {
  $runtimePython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
  if (Test-Path -LiteralPath $runtimePython) {
    return $runtimePython
  }

  $python = Get-Command "python" -ErrorAction SilentlyContinue
  if ($python) {
    return $python.Source
  }

  return "python"
}

function Add-McpServerConfig {
  param(
    [Parameter(Mandatory=$true)][string]$ConfigPath,
    [Parameter(Mandatory=$true)][string]$ServerName,
    [Parameter(Mandatory=$true)][string]$PythonCommand,
    [Parameter(Mandatory=$true)][string]$ScriptPath
  )

  New-Item -ItemType Directory -Path (Split-Path -Parent $ConfigPath) -Force | Out-Null
  if (-not (Test-Path -LiteralPath $ConfigPath)) {
    New-Item -ItemType File -Path $ConfigPath -Force | Out-Null
  }

  $content = Get-Content -LiteralPath $ConfigPath -Raw
  $sectionPattern = "(?m)^\[mcp_servers\.$([regex]::Escape($ServerName))\]"
  if ($content -match $sectionPattern) {
    Write-Host "MCP config already exists: $ServerName"
    return
  }

  $block = @"

[mcp_servers.$ServerName]
command = '$PythonCommand'
args = ['$ScriptPath']
startup_timeout_sec = 30
"@

  Add-Content -LiteralPath $ConfigPath -Value $block -Encoding UTF8
  Write-Host "Added MCP config: $ServerName"
}

function Install-McpTools {
  if ($SkipMcp -or -not (Test-Path -LiteralPath $McpSource)) {
    return
  }

  $mcpDest = Join-Path $CodexHome "mcp"
  New-Item -ItemType Directory -Path $mcpDest -Force | Out-Null

  Get-ChildItem -LiteralPath $McpSource -Directory | ForEach-Object {
    $targetDir = Join-Path $mcpDest $_.Name
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Get-ChildItem -LiteralPath $_.FullName -File | Where-Object { $_.Name -notmatch '_config\.json$' } | ForEach-Object {
      Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $targetDir $_.Name) -Force
    }
  }

  $pythonCommand = Get-PythonCommand
  $configToml = Join-Path $CodexHome "config.toml"
  Add-McpServerConfig -ConfigPath $configToml -ServerName "catstudio_device" -PythonCommand $pythonCommand -ScriptPath (Join-Path $mcpDest "catstudio-device\catstudio_device_mcp.py")
  Add-McpServerConfig -ConfigPath $configToml -ServerName "aboot_download" -PythonCommand $pythonCommand -ScriptPath (Join-Path $mcpDest "aboot-download\aboot_download_mcp.py")

  Write-Host "Installed MCP tools to $mcpDest"
  Write-Host "If needed, copy each *.example.json to *_config.json and edit local tool paths."
}

Ensure-ObsidianInstalled

if (-not $SkipSkills) {
  $skillsDest = Join-Path $CodexHome "skills"
  New-Item -ItemType Directory -Path $skillsDest -Force | Out-Null
  Copy-DirectoryContents -Source $SkillsSource -Destination $skillsDest -Overwrite
  Write-Host "Installed skills to $skillsDest"
}

Install-McpTools

if (-not $SkipAgents) {
  New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null
  Copy-Item -LiteralPath $AgentsSource -Destination (Join-Path $CodexHome "AGENTS.md") -Force
  Write-Host "Installed AGENTS.md to $CodexHome"
}

if (-not $SkipObsidian) {
  $codexVaultDest = Join-Path $VaultPath "Codex"
  New-Item -ItemType Directory -Path $codexVaultDest -Force | Out-Null
  Copy-DirectoryContents -Source $ObsidianSource -Destination $codexVaultDest
  Write-Host "Installed Obsidian Codex template to $codexVaultDest"
}

Write-Host "Done. Restart Codex so skills and AGENTS.md can take effect."
