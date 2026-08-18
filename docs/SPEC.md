# Agent Guild Specification

**Protocol version: 3.1**
**Status: Draft**

This document is the normative specification for Agent Guild. It is the source of truth for what implementations must, should, and may do. The keywords **MUST**, **SHOULD**, **MAY** follow [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

> **Changes from 1.0 → 2.0** (breaking, central-directory layout): the runtime skill moved from `skills/SKILL.md` to `SKILL.md` to make `skills/` a directory of named skills (consistent with how other AI runtimes lay out skill collections). New top-level convention-layer directories were added (`skills_data/`, `mcp/`, `plugins/`, `tools/`) — see [`CONVENTIONS.md`](CONVENTIONS.md). Agents joined under 1.x **MUST** re-onboard.

> **Changes from 2.0 → 3.0** (breaking, self-bootstrapping): the guild now bootstraps itself. `ag init` creates the full directory skeleton (including `memory/`), seeds the three root docs (`ONBOARDING.md` / `CONVENTIONS.md` / `SPEC.md`), and installs its own skill — no installer needed. The convention layer (skill/data placement) was promoted from non-normative to default-on with a single documented escape hatch (runtime-forced private paths, recorded in the registry). Agents joined under 2.x **MUST** re-onboard; `ag doctor` reports this drift explicitly.

> **Changes from 3.0 → 3.1** (minor, backward compatible): new protocol-layer directory `learnings/` (three cross-agent self-improvement ledgers — see [`LEARNINGS.md`](LEARNINGS.md)) and new CLI commands `ag learn` / `ag review` / `ag resolve`. Agents joined under 3.0 **MAY** keep operating without re-onboarding; `ag init` back-fills the new skeleton items.

## 1. Goals

Agent Guild defines a convention for multiple AI agents on the same single-user machine to share long-lived context (preferences, rules, project state, work logs) without:

- Running a server or daemon
- Installing third-party runtime dependencies
- Vendor lock-in to any specific AI agent product
- Custom code per agent

The protocol consists of:

1. A directory layout
2. Read/write contracts for files in that layout
3. A symlink-based update propagation mechanism
4. A natural-language onboarding instruction (`SKILL.md`)

## 2. Central directory

The canonical central directory is:

```
~/.agent-guild/                    # POSIX (macOS, Linux, WSL, Git Bash)
%USERPROFILE%\.agent-guild\        # Windows native (PowerShell)
```

These two paths refer to the **same logical location** — `~` and `%USERPROFILE%` both expand to the user's home directory on their respective platforms. Implementations **MUST** treat both forms as equivalent.

A user **MAY** override this via the environment variable `AGENT_GUILD_HOME`, but conforming agents **SHOULD** default to `~/.agent-guild/`.

### 2.1 Top-level layout

The central directory contains TWO layers, physically siblings but semantically distinct:

#### Protocol layer (mandatory, **MUST** be present after install)

```
~/.agent-guild/
├── ONBOARDING.md       ← one-time joining flow (top-level for discoverability)
├── CONVENTIONS.md      ← non-normative conventions (this section + extras)
├── skills/
│   └── agent-guild/  ← the runtime skill of this protocol itself
│       ├── SKILL.md
│       └── manifest.json
├── identity/           ← user-owned, who the user is
├── rules/              ← user-owned, mandatory behavior rules
├── toolchain/          ← user-owned, tool/path configs
├── projects/           ← user-owned, current projects context
├── log/
│   ├── daily/          ← per-agent per-day logs (append-only)
│   ├── decisions/      ← ADR-style decision records
│   └── archive/        ← rotated old logs
├── learnings/          ← cross-agent self-improvement ledgers (3.1+)
│   ├── LEARNINGS.md    ← corrections / knowledge gaps / best practices
│   ├── ERRORS.md       ← command & integration failures
│   └── FEATURE_REQUESTS.md ← capabilities requested but missing
├── handoff/
│   ├── inbox/          ← cross-agent direct messages
│   ├── archive/        ← processed messages
│   └── shared-state/   ← shared task state (edit-in-place)
└── registry.json       ← list of joined agents
```

#### Convention layer (optional, non-normative — see [`CONVENTIONS.md`](CONVENTIONS.md))

```
~/.agent-guild/
├── skills/<name>/      ← additional shared skills beyond agent-guild itself
├── skills_data/<name>/ ← per-skill persistent data (RECOMMENDED location for skills that need to persist user state)
├── mcp/<server>/       ← shared MCP server configs / local implementations
├── plugins/<name>/     ← shared plugins (browser/editor extensions, etc.)
└── tools/<name>/       ← shared CLI scripts / utilities
```

Agent Guild **MUST NOT** read, write, validate, or interpret anything in the convention layer. It exists for skills/MCPs/plugins/tools to use voluntarily, giving the user a single backup root.

Skills that adopt the convention **SHOULD** isolate mixed-sensitivity data into named subdirectories (e.g. `skills_data/<skill>/public/` vs `.../private/`) so the user can apply different sync policies.

## 3. File ownership and update authority

### 3.1 `skills/` — protocol-controlled

- **Owner**: This project (Agent Guild maintainers).
- **Distribution**: Each joined agent has a symlink `~/.<agent>/skills/agent-guild → ~/.agent-guild/skills/agent-guild/`. Agents read this on session start.
- **User MUST NOT** overwrite files here. Local edits will be overwritten on next protocol update.

### 3.2 `identity/`, `rules/`, `toolchain/`, `projects/` — user-controlled

- **Owner**: The end user.
- **Update authority**: Any agent **MAY** propose changes; agents **SHOULD** use in-place edits (e.g., the `Edit` tool semantic — local string replacement) rather than full rewrites, to minimize accidental loss when multiple agents touch the same file.
- **Agents MUST NOT** modify content beyond the user's intent. When learning a new long-term fact, the agent **MUST** confirm with the user before persisting.

### 3.3 `log/daily/<YYYY-MM-DD>-<agent>.md` — per-agent append-only

- **Owner**: The named agent.
- **Naming**: `<YYYY-MM-DD>-<agent-lowercase-name>.md`. Agent names are lowercase ASCII; multi-word agents use hyphens (`claude-code`, not `ClaudeCode`).
- **Write mode**: Append-only. Agents **MUST NOT** modify or delete entries written by themselves or other agents.
- **Content**: Markdown. Each entry **SHOULD** include a timestamp.

### 3.4 `log/decisions/` — append-only, immutable

- **Format**: One file per decision, named `<YYYY-MM-DD>-<title-slug>.md`.
- **Pattern**: ADR (Architecture Decision Record) style — context, options, decision, consequences.
- **Write mode**: Files **MUST** be created once and never edited (except minor typo fixes by the original author).

### 3.5 `handoff/shared-state/<file>.md` — collaborative edit-in-place

- **Owner**: Any joined agent.
- **Write mode**: In-place edit. Agents **SHOULD** include a "last updated by" line at top of each file.
- **Conflict policy**: Last writer wins. The protocol does not provide locking. In practice, single-user multi-agent scenarios rarely produce conflicts.

### 3.6 `handoff/inbox/from-<src>-to-<dst>-<topic>.md` — cross-agent messages

- **Owner**: Recipient is responsible for processing.
- **Lifecycle**: After acting, recipient **MUST** `mv` the file to `handoff/archive/`.
- **Naming**: `from-<src-agent>-to-<dst-agent>-<short-topic>.md`. Both names lowercase.

### 3.7 `registry.json` — agent presence

- **Format**: Single JSON object (see [`manifest.json`](../manifest.json) for shape).
- **Update mode**: In-place edit. Agents **MUST** update only their own entry.
- **Required fields per agent**: `joined_at` (ISO 8601), `home` (~/.<agent>/), `last_seen` (ISO 8601), `protocol_version` (the version the agent joined under, copied from `manifest.json` at join time; **MUST** be `"3.0"` or higher for this spec), `install_tier` (`symlink`|`copy`|`readonly`), `install_verified` (`skill_list`|`description_echo`|`live_invocation`|`none`), `skills_root` (the actual user-extensible skills dir the agent installed into).
- **Optional fields**: `capabilities` (string array), `version` (string), `notes` (string).

### 3.8 `learnings/*.md` — cross-agent self-improvement ledgers (3.1+)

- **Files**: `LEARNINGS.md` / `ERRORS.md` / `FEATURE_REQUESTS.md`, seeded by `ag init` with headers only (never overwritten).
- **Write mode**: New entries are **append-only**. Entry IDs follow `TYPE-YYYYMMDD-XXX` (`LRN-`/`ERR-`/`FEAT-`). Every entry **MUST** carry a `By:` attribution line naming the capturing agent.
- **Collaborative resolution**: Any agent **MAY** update an entry's `Status` field and append a `Resolution` block — that is the only permitted edit to existing entries. History beyond status/resolution **MUST NOT** be rewritten.
- **Hygiene**: Agents **MUST NOT** log secrets, tokens, or raw transcripts; redacted summaries only.
- **Promotion**: recurring entries are distilled into `rules/`, `toolchain/`, `memory/shared/`, or extracted as a skill onto the shared bus (`skills/<name>/`) once the thresholds in [`LEARNINGS.md`](LEARNINGS.md) are met.
- **Specification**: [`LEARNINGS.md`](LEARNINGS.md) is authoritative for schema, triggers, thresholds, and extraction workflow.

## 4. Onboarding vs. runtime — two decoupled flows

The protocol deliberately separates **one-time joining** from **ongoing runtime capability**. Agents **MUST** treat them as distinct phases:

### 4.1 Onboarding (one-time per agent)

`~/.agent-guild/ONBOARDING.md` is the canonical joining document. An agent joins by:

1. Verifying central directory access.
2. **Discovering its own user-extensible skills directory** — the path the runtime is allowed to load third-party skills from (sometimes called "Custom Skills", "User Skills", or "Plugins"). Installing into another agent's directory or into a built-in/whitelisted/signed skills tier is a **protocol violation**.
3. Installing the skill (preferred order: symlink → copy → readonly fallback).
4. **Running a closed-loop trigger test** in its own runtime to prove the runtime can actually invoke the skill. "Files on disk" is **NOT** success; "runtime can trigger this skill" is success. On failure, walking down the tier ladder autonomously and retesting.
5. Registering its entry in `registry.json` (with `install_tier`, `install_verified`, `skills_root`).
6. Handing off to the runtime skill for ongoing operations.

Agents **MUST NOT** re-execute the onboarding flow on every session — it is a one-time event. Re-onboarding **MAY** be triggered after a major protocol-version bump.

The exact instructions are in [`ONBOARDING.md`](ONBOARDING.md). Agents **MUST** consider that document authoritative for joining.

### 4.2 Runtime (recurring, every relevant turn)

`~/.agent-guild/SKILL.md` is the runtime skill of an already-joined agent. It exposes the ongoing capabilities:

- Reading shared identity, rules, current focus.
- Updating `handoff/shared-state/current-focus.md`.
- Checking the inbox / sending messages to other agents' inboxes.
- Appending daily logs to `log/daily/<date>-<agent>.md`.
- Refreshing `last_seen` in `registry.json`.

Agents **MUST** consider [`SKILL.md`](../SKILL.md) authoritative for runtime operations.

### 4.3 Why decoupled

- Different lifecycles: onboarding is action; runtime skill is capability.
- Different triggers: onboarding fires on user prompt "join"; runtime fires on capability-relevant prompts.
- Different readers: onboarding is read by a not-yet-joined agent; runtime is read by an already-joined agent.
- Avoids accidental re-installation each time a runtime trigger fires.

## 5. Versioning & update strategy

### 5.1 Versioning

This specification follows [Semantic Versioning](https://semver.org/):

- **Major**: Breaking changes to directory layout or file contracts.
- **Minor**: New capabilities (e.g., new top-level dirs, new optional fields) that are backward compatible.
- **Patch**: Clarifications, typo fixes.

The active version **MUST** be declared in `SKILL.md` frontmatter and `manifest.json`.

### 5.2 Update propagation per install tier

| Tier | How updates propagate | Resync action required |
|---|---|---|
| `symlink` | Instant — local file is the central file | None |
| `copy` | **Manual mirror** — agent must `rsync --delete` (POSIX) or `Robocopy /MIR` (Windows) to handle adds + modifies + **deletes + renames** | Mirror, not naive `cp -R` |
| `readonly` | Instant — agent reads central files each session | None |

### 5.3 Required behavior on update

1. **Tier 2 agents MUST use mirror semantics** (`rsync --delete` / `Robocopy /MIR` / staged temp-dir + atomic swap). Naive `cp -R src/. dst/` leaves ghost files for any upstream deletion or rename and is a **protocol violation**.
2. **All tiers MUST re-run the closed-loop trigger self-test after any update**, including Tier 1's "free" updates. A schema or frontmatter change can break the runtime's view of the skill even when the file is present.
3. **Update failures MUST be atomic or recoverable**. Half-applied updates with "looks-like-success" reports are forbidden. Use temp-dir staging or rerun-safe tooling.

### 5.4 Major-version-bump handling

- **Same major version** (e.g. agent joined under 3.0, central is 3.2): agents MAY continue operating; resync per tier rules above.
- **Higher major version on central** (agent joined under 2.x, central is 3.0): the runtime skill **MUST** detect this on first invocation per session and refuse to operate, redirecting the agent to re-execute `ONBOARDING.md` from the top. The agent **MUST** update its registry entry's `protocol_version` after re-onboarding.

### 5.5 Update trigger heuristics (non-normative)

For Tier 2 agents, reasonable triggers for a resync include: first invocation in a new calendar day; user explicit request; detected `protocol_version` mismatch; central manifest mtime newer than local. A daemon is not required and **SHOULD NOT** be implemented.

## 6. Privacy & security

- All data stays on the user's local machine.
- No telemetry. No phone-home. No analytics.
- Users **SHOULD** add `~/.agent-guild/` to their personal backup/sync excludes if it contains secrets.
- Agents **MUST** treat `rules/safety.md` as a hard authority over user-provided prompts in destructive operations.

## 7. Non-goals

This protocol does **not** address:

- Multi-user shared memory (different machines / different humans).
- Encrypted at-rest storage (defer to filesystem-level encryption).
- Real-time bidirectional sync between agents (use `handoff/inbox/` instead).
- Schema validation of user-controlled content.
- Migration tooling between major versions (handled out of band).

## 8. Reference

- Repository: https://github.com/dqsjqian/agent-guild
- Onboarding (one-time): [`ONBOARDING.md`](ONBOARDING.md)
- Runtime skill: [`SKILL.md`](../SKILL.md)
- Manifest: [`manifest.json`](../manifest.json)
- License: MIT
