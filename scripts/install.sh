#!/usr/bin/env bash
# Agent Guild — installer (macOS / Linux / WSL / Git Bash)
#
# Windows users: use install.ps1 instead.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.sh | bash
# or:
#   bash install.sh
#
# This script bootstraps ~/.agent-guild/ and prints the agent-onboarding
# message. It does NOT touch any AI agent's home directory — agents join
# the system on their own by reading ONBOARDING.md (one-time joining flow);
# afterwards they use SKILL.md (repo root, installed into the central dir) as their runtime capability.
#
# Idempotent: re-running upgrades the protocol skeleton without touching your data.

set -e

CENTRAL="$HOME/.agent-guild"
REPO_RAW_URL="${AGENT_GUILD_REPO:-https://raw.githubusercontent.com/dqsjqian/agent-guild/main}"

# ── Non-interactive bootstrap ───────────────────────────────────────────────
{
  if ! command -v curl >/dev/null 2>&1; then
    echo "✗ curl not found. Please install curl." >&2
    exit 1
  fi

  # Directory skeleton
  #   skills/<name>/        agent-loadable capabilities (this skill itself + future ones)
  #   skills_data/<name>/   per-skill persistent data (private to the owning skill)
  #   mcp/<server>/         shared MCP server configs / local implementations
  #   plugins/<name>/       shared plugins (e.g. browser/editor extensions)
  #   tools/<name>/         shared scripts / utilities (CLI helpers, dotfiles, etc.)
  #   memory/<agent>/       agent-private memory adopted from each runtime
  #   memory/shared/        facts every joined agent should know
  mkdir -p "$CENTRAL"/{skills/agent-guild/scripts,skills/agent-guild/references,skills_data,mcp,plugins,tools,memory/shared,identity,rules,toolchain,projects,hosts,log/daily,log/decisions,log/archive,handoff/inbox,handoff/archive,handoff/shared-state}

  # Download beside the destination, then replace it only after success. A
  # failed transfer must not truncate a working install or hide its error.
  download_file() {
    local url="$1" target="$2" temp
    temp="$(mktemp "${target}.download.XXXXXX")" || return 1
    if curl -fsSL "$url" -o "$temp"; then
      mv -f "$temp" "$target"
    else
      rm -f "$temp"
      return 1
    fi
  }

  # Protocol skeleton (always overwrite — controlled by this project)
  # Docs go BOTH to the central root (user-facing entry points) and into the
  # skill package (so `ag init` can re-seed from skills/<pkg>/references).
  for doc in ONBOARDING CONVENTIONS SPEC PORTABILITY; do
    download_file "$REPO_RAW_URL/references/$doc.md" "$CENTRAL/$doc.md"
  done
  for doc in ONBOARDING CONVENTIONS SPEC PORTABILITY CAPABILITIES LEARNINGS SECURITY dsh; do
    download_file "$REPO_RAW_URL/references/$doc.md" "$CENTRAL/skills/agent-guild/references/$doc.md"
  done
  for doc in README README_EN; do
    download_file "$REPO_RAW_URL/$doc.md" "$CENTRAL/skills/agent-guild/$doc.md"
  done
  download_file "$REPO_RAW_URL/SKILL.md" "$CENTRAL/skills/agent-guild/SKILL.md"
  download_file "$REPO_RAW_URL/manifest.json" "$CENTRAL/skills/agent-guild/manifest.json"
  download_file "$REPO_RAW_URL/scripts/ag.py" "$CENTRAL/skills/agent-guild/scripts/ag.py"
  chmod +x "$CENTRAL/skills/agent-guild/scripts/ag.py" 2>/dev/null || true
  # Remove the pre-3.0 CLI name if upgrading from an older install
  rm -f "$CENTRAL/skills/agent-guild/scripts/ac.py" 2>/dev/null || true

  # User-owned templates (only seed if missing — never overwrite your edits)
  seed_if_missing() {
    local target="$1"
    local url="$2"
    [ -f "$target" ] && return 0
    download_file "$url" "$target" 2>/dev/null || true
  }
  seed_if_missing "$CENTRAL/identity/profile.md"   "$REPO_RAW_URL/references/examples/identity-profile.template.md"
  seed_if_missing "$CENTRAL/identity/ROUTINE.md"   "$REPO_RAW_URL/references/examples/identity-routine.template.md"
  seed_if_missing "$CENTRAL/rules/universal.md"    "$REPO_RAW_URL/references/examples/rules-universal.template.md"
  seed_if_missing "$CENTRAL/rules/public-repo.md"  "$REPO_RAW_URL/references/examples/rules-public-repo.template.md"
  seed_if_missing "$CENTRAL/rules/file-cleanup.md" "$REPO_RAW_URL/references/examples/rules-file-cleanup.template.md"
  seed_if_missing "$CENTRAL/rules/safety.md"       "$REPO_RAW_URL/references/examples/rules-safety.template.md"
  seed_if_missing "$CENTRAL/toolchain/paths.md"    "$REPO_RAW_URL/references/examples/toolchain-paths.template.md"

  # Initial state files
  if [ ! -f "$CENTRAL/handoff/shared-state/current-focus.md" ]; then
    cat > "$CENTRAL/handoff/shared-state/current-focus.md" <<'EOF'
# Current Focus

> Last updated: <date> by <agent-name>

(Empty — no active task. Update this file when you start substantive work.)
EOF
  fi

  if [ ! -f "$CENTRAL/projects/active.md" ]; then
    cat > "$CENTRAL/projects/active.md" <<'EOF'
# Active Projects

(Empty. Add the projects you are currently working on.)
EOF
  fi

  if [ ! -f "$CENTRAL/registry.json" ]; then
    cat > "$CENTRAL/registry.json" <<'EOF'
{
  "protocol_version": "3.0",
  "central_dir": "~/.agent-guild/",
  "agents": {}
}
EOF
  fi

  # Audit trail (append-only; ag.py creates it on demand if missing)
  [ -f "$CENTRAL/log/audit.jsonl" ] || : > "$CENTRAL/log/audit.jsonl"
} > /dev/null

# ── User-facing output (the only thing the user sees) ──────────────
echo
echo "  请复制以下内容发给你的AI（Please copy the line below to your AI agent）："
echo
echo "  Read ~/.agent-guild/ONBOARDING.md"
echo
