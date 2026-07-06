#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-$HOME/Documents/Obsidian/CodexVault}"
INSTALL_SKILLS="${INSTALL_SKILLS:-1}"
INSTALL_MCP="${INSTALL_MCP:-0}"
INSTALL_AGENTS="${INSTALL_AGENTS:-1}"
INSTALL_OBSIDIAN="${INSTALL_OBSIDIAN:-1}"

if [ "$INSTALL_SKILLS" = "1" ]; then
  mkdir -p "$CODEX_HOME/skills"
  cp -R "$REPO_ROOT/skills/." "$CODEX_HOME/skills/"
  echo "已安装 skills 到 $CODEX_HOME/skills"
fi

if [ "$INSTALL_MCP" = "1" ]; then
  mkdir -p "$CODEX_HOME/mcp"
  cp -R "$REPO_ROOT/mcp/." "$CODEX_HOME/mcp/"
  echo "已复制 MCP 到 $CODEX_HOME/mcp"
  echo "这些 MCP 主要面向 Windows CATStudio/AbootDownload；请按需手动配置 Codex config.toml。"
fi

if [ "$INSTALL_AGENTS" = "1" ]; then
  mkdir -p "$CODEX_HOME"
  cp "$REPO_ROOT/AGENTS.md" "$CODEX_HOME/AGENTS.md"
  echo "已安装 AGENTS.md 到 $CODEX_HOME"
fi

if [ "$INSTALL_OBSIDIAN" = "1" ]; then
  mkdir -p "$OBSIDIAN_VAULT/Codex"
  cp -Rn "$REPO_ROOT/obsidian/Codex/." "$OBSIDIAN_VAULT/Codex/"
  echo "已补齐 Obsidian Codex 模板到 $OBSIDIAN_VAULT/Codex"
fi

echo "安装完成。请重启 Codex，让 skills 和 AGENTS.md 生效。"
