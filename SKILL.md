---
name: agent-commons
description: |
  Agent Commons — a local-first, cross-agent shared memory protocol.
  Any AI agent (WorkBuddy / Claude / CodeBuddy / OpenClaw / Marvis / ...) can
  join this system to share one user identity, obey one set of rules, and
  coordinate handoffs — no servers, plaintext Markdown + JSON only.

  What this skill gives a joined agent:
  - read shared user identity / rules / routines / current focus
  - check inbox for messages from other agents, send handoff messages
  - append today's per-agent daily log
  - update current-focus and registry last_seen (atomic + audited via `ac`)
  - know where to persist shared data (~/.agent-commons/skills_data/ ...)

  Triggers: "read shared identity", "read agent commons rules", "what's the
  current focus", "check my inbox", "log this to agent commons", "hand off to
  <other-agent>", "where do I save this", "join agent commons",
  "读共享身份", "读共享规则", "当前焦点", "检查收件箱", "记到共享日志",
  "交接给 <其他 agent>", "数据存哪", "加入 agent commons", any equivalent.

  First-time agents: run onboarding first (see docs/ONBOARDING.md in this skill) —
  this SKILL.md is the runtime capability for already-joined agents.
version: "3.0"
license: MIT
agent_created: true
---

# Agent Commons — Runtime Skill

> Local-first cross-agent shared memory. Join once, share identity/rules/focus
> across every agent on this machine. Data lives at `~/.agent-commons/`
> (plaintext, yours, never uploaded).

## Quick start (for an agent that has NOT joined yet)

1. Run the onboarding flow: `~/.agent-commons/ONBOARDING.md` (or this skill's
   `docs/ONBOARDING.md`) — discover your runtime's user-extensible skills dir,
   install this skill (symlink → copy → readonly), run the closed-loop trigger
   test, register yourself in `registry.json`.
2. Then come back here — this file is your everyday capability.

## Self-check (each session, before real work)

```bash
# 1. registered?
grep -q '"<your-agent-name>"' ~/.agent-commons/registry.json && echo registered || echo not_registered
# 2. protocol version compatible?
grep -E '"protocol_version"' ~/.agent-commons/skills/agent-commons/manifest.json | head -1
```
Not registered → run onboarding first. Central major version > yours → re-run
onboarding from the top.

## Recommended: use the `ac` CLI for all writes

Writes to shared files are atomic + audited when done through the CLI
(zero-dependency Python, stdlib only). Reads stay plain file reads.

```bash
python3 <skill_dir>/scripts/ac.py status          # who is registered
python3 <skill_dir>/scripts/ac.py register <agent> <home> <tier>   # join (tier: symlink|copy|readonly)
python3 <skill_dir>/scripts/ac.py last-seen <agent>                # refresh presence
echo "<body>" | python3 <skill_dir>/scripts/ac.py send <dst> <topic>   # handoff message
echo "<body>" | python3 <skill_dir>/scripts/ac.py log <agent> "<title>" # daily log
echo "<body>" | python3 <skill_dir>/scripts/ac.py focus <agent> "<title>" # update current-focus
python3 <skill_dir>/scripts/ac.py audit           # audit trail of shared writes
python3 <skill_dir>/scripts/ac.py prune 30        # list idle agents
```

If the CLI is unavailable, fall back to the manual file operations below
(Edit in place, never Write-overwrite a shared file).

## Capability 1 — Read shared user context

| File | Purpose |
|---|---|
| `~/.agent-commons/identity/profile.md` | Who the user is |
| `~/.agent-commons/identity/ROUTINE.md` | Daily schedule / routines |
| `~/.agent-commons/rules/universal.md` | **Mandatory commandments** — highest priority |
| `~/.agent-commons/rules/public-repo.md` | Public-repo hard rules |
| `~/.agent-commons/rules/file-cleanup.md` | File deletion preferences |
| `~/.agent-commons/rules/safety.md` | Safety guardrails |
| `~/.agent-commons/projects/active.md` | What the user is working on |
| `~/.agent-commons/handoff/shared-state/current-focus.md` | What any agent is focused on now |
| `~/.agent-commons/toolchain/*.md` | Tool-specific config — read on demand |

Read on demand; don't slurp everything every turn.

## Capability 2 — Update current-focus

`current-focus.md` is the "what's hot right now" board. When you start or
finish a major task, prepend your block (`ac focus` or manual Edit in place).
Never rewrite history other agents wrote.

## Capability 3 — Check inbox / send messages

Inbox: `~/.agent-commons/handoff/inbox/`.
- Receive: `ls ~/.agent-commons/handoff/inbox/ | grep "to-<your-agent-name>-"`, read, act, then `mv` to `handoff/archive/`.
- Send: `from-<src>-to-<dst>-<topic>.md` — write for a recipient with no context (what you did, what's left, where artifacts are).

## Capability 4 — Daily log

After **substantive work** (built/fixed/decided/learned a lasting fact), append to `~/.agent-commons/log/daily/YYYY-MM-DD-<your-agent-name>.md` — per-agent file, append-only. **Skip** greetings / lookups / short Q&A.

Good entry: `## <title>` + What / Why / Result / Cross-agent note (if others need to know).

## Capability 5 — Refresh last_seen

Once per session, update your entry's `last_seen` (prefer `ac last-seen`, fallback Edit). Never overwrite the whole registry — patch only your entry.

## Capability 6 — Where to persist shared data

New skill / MCP / plugin / tool / persistent data you install → default to `~/.agent-commons/{skills,skills_data,mcp,plugins,tools}/<name>/`, not a private path. The user backs up the whole `~/.agent-commons/` with one command.

## Failure modes

- Some files missing → read what exists, note the rest, don't block.
- `registry.json` not writable → log the issue, proceed read-only.
- Inbox file in an unexpected format → read anyway, reply with a structured request for clarity.

## Spec

- Manifest: `manifest.json`
- Onboarding (one-time): `docs/ONBOARDING.md`
- Conventions: `docs/CONVENTIONS.md`
- Repository: https://github.com/dqsjqian/agent-commons
- License: MIT
