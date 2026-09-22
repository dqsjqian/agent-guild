---
name: agent-guild
description: |
  智能体协会（agent-guild）— cross-agent shared memory. 本机多个 AI agent 共享
  同一份身份、规则、记忆与交接消息 — 纯本地 Markdown/JSON，无服务器。

  触发（任何自然等价表达都算）：
  · 身份/习惯："我是谁" "我的偏好" "who am I" "my routine"
  · 回忆/历史："你记得吗" "上次我们聊过" "what did we discuss"
  · 写记忆："帮我记住" "记一下" "remember this" "记到日志"
  · 跨 agent："告诉其他 agent" "交接给" "hand off"
  · 当前状态："现在在做什么" "当前焦点" "current focus"
  · 数据卫生："整理协会" "清理过期数据" "groom" "cleanup"
  · 跨设备："换了台电脑" "这个工具在哪" "cross-device"
  · 加入："加入协会" "初始化" "join agent guild"

  能力：共享身份/规则/焦点读写；收件箱交接；每日日志；会话闭环
  （ag recall / ag finish）；并发锁防丢写；学习台账；自动 groom 归档；
  跨设备三层作用域（shared/platform/host）。
  未加入？先跑 docs/ONBOARDING.md。
slug: agent-guild
displayName: 智能体协会 Agent Guild
display_name: 智能体协会 Agent Guild
display_name_en: Agent Guild
description_zh: 跨 agent 共享记忆协议，本机多个 AI 共用一份身份/规则/记忆，可跨设备搬运
description_en: Cross-agent shared memory protocol — one identity, rules and memory for every AI on your devices
author: dqsjqian
category: productivity
protocol_version: "3.3"
version: "3.9.1"
platforms: ["macos", "windows", "linux", "android", "ios"]
license: MIT
homepage: https://github.com/dqsjqian/agent-guild
repository: https://github.com/dqsjqian/agent-guild
agent_created: true
---

# Agent Guild — Runtime Skill

> Local-first cross-agent shared memory. Join once, share identity/rules/focus
> across every agent on this machine. Data lives at `~/.agent-guild/`
> (plaintext, yours, never uploaded), safe to carry between devices — facts
> are scoped shared / platform / host.

`SKILL_DIR` = the directory containing this file. CLI:
`python3 <SKILL_DIR>/scripts/ag.py` (referred to as `ag`).
Python 3.9+ stdlib only. On Windows use `python` if `python3` is not on PATH.

**Context budget note**: this file is the whole mandatory load (~6KB).
Everything else is read-on-demand: full CLI reference + capability detail →
`docs/CAPABILITIES.md`; join flow → `docs/ONBOARDING.md`.

## Quick start (NOT joined yet)

Run the onboarding flow: `~/.agent-guild/ONBOARDING.md` (or this skill's
`docs/ONBOARDING.md`), then come back here — this file is your everyday
capability.

## Mandatory Session Contract (once per session, MUST)

> 强制动作，本 skill 被触发时就执行一遍，不必等用户点名。All through `ag`,
> one command each. No shell? Plain-file equivalents exist for every step —
> read/edit the listed files directly; the contract still applies.

**M0 — Ensure the guild exists**: `ag init <agent>` — idempotent; creates
skeleton on first run, NEVER overwrites existing data.

**M1 — Read shared context BEFORE real work**: `ag bootstrap <agent>` — one
shot: profile → routine → top rules → active projects → each agent's focus →
your unread inbox. Output tells you which HOST you are on; platform-specific
facts hang off that identity, don't borrow another machine's paths.
Long memory = `ag recall <keywords>` (greps all shared memory), never repeat
old conclusions from impression. `memory/shared/INDEX.md` is the shared-facts
catalog.

**M2 — Write memory after substantive work** (deliverable/code/config changed,
decision made, bug root-caused, lasting fact learned. SKIP: greetings,
lookups, short Q&A):

    echo "<summary>" | ag finish <agent>

= summary into today's daily log + last_seen refresh + inbox report. Read
back the output path to confirm it landed. Cross-agent-valuable facts →
`memory/shared/` (register in `INDEX.md`); self-only → `memory/<agent>/`.
Pitfall / correction / better way found → also
`ag learn <agent> learning|error|featreq "<summary>"`. Never log secrets;
redact excerpts.

**M3 — Route skills & data into the guild (default-on)**:
- Preferred: `ag link-root <me> --apply` — your entire skills dir becomes ONE
  directory symlink to `~/.agent-guild/skills/`; new guild skills appear
  instantly, zero back-linking.
- Fallback ladder: per-skill symlink → copy → readonly (ONBOARDING Step 3).
- New skills → `~/.agent-guild/skills/<name>/`; persistent data →
  `skills_data/<name>/` (sensitive → `private/`); MCP/plugins/CLIs → their
  own dirs.
- Sole exemption: runtime forces private paths → record the reason in registry.

**M4 — Self-audit (first join + monthly)**: `ag adopt <me>` dry-run report,
`--apply` to actually move (auto-verify, auto-rollback on failure, trash not
delete). Health check: `ag doctor`.

## Self-check (before real work)

```bash
grep -q '"<your-agent-name>"' ~/.agent-guild/registry.json && echo registered
grep -E '"protocol_version"' ~/.agent-guild/skills/agent-guild/manifest.json
```

Not registered → run onboarding first. Central major version > yours →
re-run onboarding from the top.

## The `ag` CLI — use it for all writes

Atomic + audited; concurrent appends serialized with an advisory lock (no
lost entries). Reads stay plain file reads. Full command table incl.
low-frequency ops (`register/send/log/focus/review/resolve/prune/audit/port`):
**`docs/CAPABILITIES.md`**.

```bash
AG="python3 <SKILL_DIR>/scripts/ag.py"
$AG init <agent>                  # idempotent guild bootstrap
$AG bootstrap <agent>             # read ALL shared context in one shot
$AG recall <kw> [...]             # grep shared memory (AND; --all=OR; --limit N)
echo "s" | $AG finish <agent>     # close out: daily log + last_seen + inbox
$AG platform                      # which device am I on?
$AG tool <name>                   # tool path HERE (exit 3 = absent + install hint)
$AG doctor                        # dangling links / stale paths / drift
$AG status | adopt | port | groom | learn   # maintenance set
```

CLI unavailable? Every capability is reachable by plain file reads/writes —
Edit shared files in place, never Write-overwrite them.

## Capabilities at a glance

Detail for every row: `docs/CAPABILITIES.md`.

| # | Capability | One-liner |
|---|---|---|
| 1 | Shared user context | `identity/ rules/ projects/` — read on demand, don't slurp |
| 2 | current-focus | prepend your block on major tasks; never rewrite others' |
| 3 | Inbox handoff | `handoff/inbox/` → read, act → `handoff/archive/` |
| 4 | Daily log | via `ag finish` / `ag log`; append-only, per-agent file |
| 5 | last_seen | once per session; patch only your registry entry |
| 6 | Data placement | everything under `~/.agent-guild/{skills,skills_data,mcp,plugins,tools}/` |
| 7 | Cross-agent memory | `memory/<agent>/` private; `memory/shared/` + `INDEX.md` |
| 8 | Learning ledger | `learnings/{LEARNINGS,ERRORS,FEATURE_REQUESTS}.md`; promotes to rules/skills |
| 9 | Data hygiene | `ag groom` auto after bootstrap (rate-limited); moves, never deletes |
| 10 | Cross-device | shared/platform/host scoping; `docs/PORTABILITY.md` |

Cross-device hard rules (Capability 10): tool paths only via `ag tool`; no
machine-absolute paths in shared files (→ `hosts/<host-id>/host-notes.md`);
the guild is the source of truth (inbound symlinks only, internal symlinks
relative); platform-specific skills declare `"platforms"` in manifest.

## Security disclosure

Zero-dependency Python CLI + Markdown/JSON, all data local. Network use is
limited to its own release-version self-check; deletions go to trash; every
sensitive operation is whitelisted and audited. Full mapping:
`docs/SECURITY.md`.

## Spec

Manifest: `manifest.json` · Onboarding: `docs/ONBOARDING.md` · Conventions:
`docs/CONVENTIONS.md` · Capabilities: `docs/CAPABILITIES.md` · Learnings:
`docs/LEARNINGS.md` · Portability: `docs/PORTABILITY.md` · Security:
`docs/SECURITY.md` · Repository: https://github.com/dqsjqian/agent-guild

## Failure modes

Some files missing → read what exists, note the rest, don't block.
`registry.json` not writable → log the issue, proceed read-only.
Inbox file in unexpected format → read anyway, reply with a structured
request for clarity.
