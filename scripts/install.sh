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
  public_skills="$(python3 -c 'import json, sys; print("\n".join(json.load(open(sys.argv[1], encoding="utf-8"))["skills"]))' "$REPO_ROOT/public-sync-manifest.json")"
  while IFS= read -r skill_name; do
    skill_source="$REPO_ROOT/skills/$skill_name"
    mkdir -p "$CODEX_HOME/skills/$skill_name"
    cp -R "$skill_source/." "$CODEX_HOME/skills/$skill_name/"
  done <<< "$public_skills"
  if [ -d "$REPO_ROOT/runtime" ]; then
    mkdir -p "$CODEX_HOME/scripts"
    cp -R "$REPO_ROOT/runtime/." "$CODEX_HOME/scripts/"
  fi
  echo "已安装 skills 到 $CODEX_HOME/skills"
  if [ -d "$REPO_ROOT/skills-index" ]; then
    mkdir -p "$CODEX_HOME/skills-index"
    cp -R "$REPO_ROOT/skills-index/." "$CODEX_HOME/skills-index/"
    echo "已安装一行式/领域 skill 索引到 $CODEX_HOME/skills-index"
  fi
fi

if [ "$INSTALL_MCP" = "1" ]; then
  mkdir -p "$CODEX_HOME/mcp"
  cp -R "$REPO_ROOT/mcp/." "$CODEX_HOME/mcp/"
  echo "已复制 MCP 到 $CODEX_HOME/mcp"
  echo "当前仓库只包含 everything-search 的公开元数据；请按示例手动配置 Codex。"
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
