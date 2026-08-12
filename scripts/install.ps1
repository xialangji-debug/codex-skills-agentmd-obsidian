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
$SkillsIndexSource = Join-Path $RepoRoot "skills-index"
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

  Write-Host "Installed MCP tools to $mcpDest"
  Write-Host "This repo only ships metadata/example files for everything-search."
  Write-Host "Configure the MCP server manually from everything_search_config.example.json when needed."
}

Ensure-ObsidianInstalled

if (-not $SkipSkills) {
  $skillsDest = Join-Path $CodexHome "skills"
  New-Item -ItemType Directory -Path $skillsDest -Force | Out-Null
  Copy-DirectoryContents -Source $SkillsSource -Destination $skillsDest -Overwrite
  Write-Host "Installed skills to $skillsDest"
  if (Test-Path -LiteralPath $SkillsIndexSource) {
    $skillsIndexDest = Join-Path $CodexHome "skills-index"
    Copy-DirectoryContents -Source $SkillsIndexSource -Destination $skillsIndexDest -Overwrite
    Write-Host "Installed one-line/domain skill indexes to $skillsIndexDest"
  }
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
