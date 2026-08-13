# Agent Guild

> A protocol that lets any sufficiently intelligent AI agent join your shared memory by simply reading one file.

**English** | [中文](README_CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-MVP-blue)]()
[![Protocol](https://img.shields.io/badge/protocol-v2.0-green)]()

---

**You probably switch between multiple AI agents every day** — Claude Code, Cursor, CodeBuddy, WorkBuddy, OpenClaw, Aider, GitHub Copilot Chat… and every one of them is an isolated island. Each one has its own memory of you, none of them know what the other learned. You teach the same preferences over and over.

**Agent Guild fixes that.** It's a tiny **protocol** — not a framework, not a service, not even a library — that lets multiple AI agents on your machine share a single source of truth via plain Markdown files and Unix symlinks.

---

## The 30-second pitch

```
~/.agent-guild/                ← One central directory on your machine
│
│  ─── Protocol layer (mandatory) ───
├── ONBOARDING.md                ← One-time joining flow for new agents
├── CONVENTIONS.md               ← Optional, non-normative conventions
├── identity/                    ← Who you are (profile, routine)
├── rules/                       ← Hard rules every agent must obey
├── toolchain/                   ← Tools, paths, configs
├── projects/                    ← What you're working on
├── log/daily/                   ← Per-agent daily logs (no write conflicts)
├── handoff/                     ← Cross-agent inbox + shared state
├── skills/agent-guild/    ← Runtime skill installed from repo root (SKILL.md + manifest + scripts)
├── registry.json                ← Which agents have joined
│
│  ─── Convention layer (optional, recommended) ───
├── skills_data/<skill>/         ← Per-skill persistent data (one backup root for all)
├── mcp/<server>/                ← Shared MCP server configs
├── plugins/<name>/              ← Shared plugins
└── tools/<name>/                ← Shared CLI scripts/utilities
```

Every joined agent has a symlink:

```bash
~/.<your-agent>/skills/agent-guild → ~/.agent-guild/skills/agent-guild/
```

That's it. **No daemon. No server. No npm install. No third-party runtime. Pure filesystem.**

---

## Why this exists (and why it's different)

| Existing solution | What it does | The catch |
|---|---|---|
| ChatGPT Memory | Auto-remembers facts about you | Locked inside OpenAI |
| Claude Projects | Project-scoped context | Anthropic only |
| MemGPT / Letta | Long-term memory inside one agent | Doesn't span agents |
| Mem0 | Cross-agent memory service | Needs server, REST API, vendor lock |
| MCP | Tool/resource protocol | Not about memory |
| **Agent Guild** | **Cross-vendor, local-first, plaintext, zero-deps** | **Requires the agent to be smart enough to read a file** |

The differentiator: **we don't write adapters for each agent**. We write a single `SKILL.md` that any sufficiently intelligent LLM can read and self-onboard from. Agents that can't follow plain English instructions… don't get to join. That's the design.

---

## How a user makes any AI agent join

Tell the agent, in any language, any phrasing:

> "Read `~/.agent-guild/ONBOARDING.md` and join the Agent Guild system."

That's the entire user-side workflow. No CLI to install, no configs to edit. The agent reads the file, follows the joining flow inside, and reports back.

If the agent can't figure it out, **the agent isn't smart enough for your workflow** — and you'll know that, too. It's a built-in capability test.

---

## What the protocol actually requires of a joined agent

The protocol cleanly separates **one-time joining** from **ongoing capabilities**:

- **`ONBOARDING.md`** (one-time): discover your runtime's user-extensible skills directory, install the skill (symlink → copy → readonly fallback), run a closed-loop trigger test to prove the runtime can actually invoke it, register in `registry.json`.
- **`SKILL.md`** (recurring): read shared identity / rules / current focus; check inbox / send messages; append daily logs; refresh `last_seen`. This is the runtime capability the joined agent carries forward.

See [`ONBOARDING.md`](ONBOARDING.md) for the joining flow.
See [`SKILL.md`](../SKILL.md) for the runtime capability spec.
See [`SPEC.md`](SPEC.md) for the full normative specification.
See [`CONVENTIONS.md`](CONVENTIONS.md) for optional, non-normative conventions (e.g. recommended skill data location at `~/.agent-guild/skills_data/`).
See [`manifest.json`](../manifest.json) for the machine-readable spec.

---

## Single source of truth — automatic protocol updates

Each joined agent's `~/.<agent>/skills/agent-guild/` is a **symlink** back to the central `~/.agent-guild/skills/agent-guild/`. When this project ships a protocol update, you update the central dir; **every agent on the user's machine sees the new version on its next session start**. No push notifications, no version checks, no hash comparison. Just filesystem semantics doing what filesystem semantics do.

User-owned files (`identity/`, `rules/`, `toolchain/`, etc.) are **never overwritten by upstream** — they live next to but outside the symlinked `skills/`.

---

## Install (for users)

### macOS / Linux / WSL / Git Bash

```bash
curl -fsSL https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.sh | bash
```

### Windows (PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.ps1 | iex
```

The installer does exactly **one** thing: bootstrap the central directory at `~/.agent-guild/` (or `%USERPROFILE%\.agent-guild\`) with seed files, then print a bilingual one-liner you can paste into any AI agent. **It does not touch any agent's home directory.** Agents install themselves — that's the protocol.

### Manual install

```bash
git clone https://github.com/dqsjqian/agent-guild ~/.agent-guild
```

Then tell your agent:

> "Read `~/.agent-guild/ONBOARDING.md` and join Agent Guild."

The agent will figure out how to integrate with itself (symlink, copy, or read-only fallback — see ONBOARDING.md).

(Windows users: replace `~` with `$HOME` in PowerShell, and use `New-Item -ItemType SymbolicLink` instead of `ln -s`.)

Then talk to your agent.

---

## Platform support

| OS / Shell | Status |
|---|---|
| macOS | ✅ first-class |
| Linux | ✅ first-class (any POSIX shell) |
| Windows + PowerShell 5.1+ | ✅ first-class (Dev Mode or Admin required for symlinks) |
| Windows + WSL / Git Bash | ✅ works (set `MSYS=winsymlinks:nativestrict` for Git Bash) |
| Windows + cmd.exe | ❌ not supported (use PowerShell) |

---

## Project status & philosophy

**Phase 1 (done): Protocol + reference content.** Directory skeleton, `SKILL.md`, `manifest.json`, cross-platform installers. The README is the product.

**Phase 2 (done in 3.0): Single-file CLI** (`ag`) — `init / adopt / bootstrap / doctor / status / register / log / focus / send / audit / prune`. Pure Python stdlib, zero dependencies, Windows / macOS / Linux.

**Phase 3 (in progress): Adapters directory.** Community-contributed integration guides for specific agents.

We are deliberately **not** building:
- a daemon
- a Python/Node package on pip/npm
- a CRDT sync engine
- a cloud service
- a chat UI

This project is a **convention**, not software. Convention beats configuration. Filesystem beats database. Symlinks beat sync logic.

---

## License

MIT. See [LICENSE](LICENSE).

## Author

[@dqsjqian](https://github.com/dqsjqian) · also creator of [soul-archive](https://github.com/dqsjqian/soul-archive) and [ai-eight-creed](https://github.com/dqsjqian/ai-eight-creed).

---

> *Make your AI agents finally stop forgetting each other.*
