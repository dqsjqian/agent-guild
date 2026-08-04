# Agent Commons — Windows installer (PowerShell)
#
# Usage (one-shot):
#   iwr -useb https://raw.githubusercontent.com/dqsjqian/agent-commons/main/install.ps1 | iex
#
# Or:
#   .\install.ps1
#
# This script bootstraps %USERPROFILE%\.agent-commons\ and prints the
# agent-onboarding message. It does NOT touch any AI agent's home directory —
# agents join the system on their own by reading ONBOARDING.md (one-time
# joining flow); afterwards they use skills\agent-commons\SKILL.md as their
# runtime capability.
#
# Idempotent: re-running upgrades the protocol skeleton without touching your data.
#
# Requirements: PowerShell 5.1 or later.

# UTF-8 output (otherwise Chinese gets garbled on Windows PowerShell 5.1)
# NOTE: this file is saved as UTF-8 with BOM so PS 5.1 parses Chinese literals correctly.
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
try { chcp 65001 > $null } catch {}

$ErrorActionPreference = 'Stop'

$Central = Join-Path $env:USERPROFILE '.agent-commons'
$RepoRawUrl = if ($env:AGENT_COMMONS_REPO) { $env:AGENT_COMMONS_REPO } else { 'https://raw.githubusercontent.com/dqsjqian/agent-commons/main' }

# ── Silent bootstrap ───────────────────────────────────────────────
$null = & {
    # Directory skeleton
    #   skills\<name>\        agent-loadable capabilities
    #   skills_data\<name>\   per-skill persistent data
    #   mcp\<server>\         shared MCP server configs / local implementations
    #   plugins\<name>\       shared plugins
    #   tools\<name>\         shared scripts / utilities
    $dirs = @(
        'skills\agent-commons','skills_data','mcp','plugins','tools',
        'identity','rules','toolchain','projects',
        'log\daily','log\decisions','log\archive',
        'handoff\inbox','handoff\archive','handoff\shared-state'
    )
    foreach ($d in $dirs) {
        $full = Join-Path $Central $d
        if (-not (Test-Path $full)) {
            New-Item -ItemType Directory -Path $full -Force | Out-Null
        }
    }

    # Protocol skeleton (always overwrite — controlled by this project)
    function Download-File {
        param([string]$Url, [string]$Dest)
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Dest -ErrorAction Stop
            return $true
        } catch {
            return $false
        }
    }

    Download-File "$RepoRawUrl/docs/ONBOARDING.md"                      (Join-Path $Central 'ONBOARDING.md')                          | Out-Null
    Download-File "$RepoRawUrl/docs/CONVENTIONS.md"                     (Join-Path $Central 'CONVENTIONS.md')                         | Out-Null
    Download-File "$RepoRawUrl/SKILL.md"      (Join-Path $Central 'skills\agent-commons\SKILL.md')      | Out-Null
    Download-File "$RepoRawUrl/manifest.json" (Join-Path $Central 'skills\agent-commons\manifest.json') | Out-Null

    # User-owned templates (only seed if missing)
    function Seed-If-Missing {
        param([string]$Target, [string]$Url)
        if (-not (Test-Path $Target)) {
            Download-File $Url $Target | Out-Null
        }
    }
    Seed-If-Missing (Join-Path $Central 'identity\profile.md')   "$RepoRawUrl/docs/examples/identity-profile.template.md"
    Seed-If-Missing (Join-Path $Central 'identity\ROUTINE.md')   "$RepoRawUrl/docs/examples/identity-routine.template.md"
    Seed-If-Missing (Join-Path $Central 'rules\universal.md')    "$RepoRawUrl/docs/examples/rules-universal.template.md"
    Seed-If-Missing (Join-Path $Central 'rules\public-repo.md')  "$RepoRawUrl/docs/examples/rules-public-repo.template.md"
    Seed-If-Missing (Join-Path $Central 'rules\file-cleanup.md') "$RepoRawUrl/docs/examples/rules-file-cleanup.template.md"
    Seed-If-Missing (Join-Path $Central 'rules\safety.md')       "$RepoRawUrl/docs/examples/rules-safety.template.md"
    Seed-If-Missing (Join-Path $Central 'toolchain\paths.md')    "$RepoRawUrl/docs/examples/toolchain-paths.template.md"

    # Initial state files
    $focusFile = Join-Path $Central 'handoff\shared-state\current-focus.md'
    if (-not (Test-Path $focusFile)) {
        @"
# Current Focus

> Last updated: <date> by <agent-name>

(Empty — no active task. Update this file when you start substantive work.)
"@ | Set-Content -Path $focusFile -Encoding UTF8
    }

    $projFile = Join-Path $Central 'projects\active.md'
    if (-not (Test-Path $projFile)) {
        @"
# Active Projects

(Empty. Add the projects you are currently working on.)
"@ | Set-Content -Path $projFile -Encoding UTF8
    }

    $registry = Join-Path $Central 'registry.json'
    if (-not (Test-Path $registry)) {
        @"
{
  "protocol_version": "2.0",
  "agents": {}
}
"@ | Set-Content -Path $registry -Encoding UTF8
    }
} 2>&1

# ── User-facing output (the only thing the user sees) ──────────────
# Build Chinese strings from UTF-8 bytes to avoid PS 5.1 source-encoding pitfalls.
$utf8 = [System.Text.Encoding]::UTF8
$msg1 = $utf8.GetString([byte[]](0xE8,0xAF,0xB7,0xE5,0xA4,0x8D,0xE5,0x88,0xB6,0xE4,0xBB,0xA5,0xE4,0xB8,0x8B,0xE5,0x86,0x85,0xE5,0xAE,0xB9,0xE5,0x8F,0x91,0xE7,0xBB,0x99,0xE4,0xBD,0xA0,0xE7,0x9A,0x84,0x41,0x49))
$msg2 = $utf8.GetString([byte[]](0xEF,0xBC,0x88,0x50,0x6C,0x65,0x61,0x73,0x65,0x20,0x63,0x6F,0x70,0x79,0x20,0x74,0x68,0x65,0x20,0x6C,0x69,0x6E,0x65,0x20,0x62,0x65,0x6C,0x6F,0x77,0x20,0x74,0x6F,0x20,0x79,0x6F,0x75,0x72,0x20,0x41,0x49,0x20,0x61,0x67,0x65,0x6E,0x74,0xEF,0xBC,0x89,0xEF,0xBC,0x9A))

Write-Host ""
Write-Host ("  " + $msg1 + $msg2)
Write-Host ""
Write-Host "  Read ~/.agent-commons/docs/ONBOARDING.md"
Write-Host ""
