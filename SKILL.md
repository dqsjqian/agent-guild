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
slug: agent-guild
displayName: 智能体协会 Agent Guild
display_name: 智能体协会 Agent Guild
display_name_en: Agent Guild
description_zh: 跨 agent 共享记忆协议，本机多个 AI 共用一份身份/规则/记忆，可跨设备搬运
description_en: Cross-agent shared memory protocol — one identity, rules and memory for every AI on your devices
author: dqsjqian
category: productivity
protocol_version: "3.3"
version: "3.11.0"
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

## Quick verify — 30 seconds, copy-paste ready

Three commands exercise the full loop (create guild → read context → write
log). Run them as-is; `demo-agent` is just an example name, any kebab-case
name works:

```bash
AG="python3 $HOME/.agent-guild/skills/agent-guild/scripts/ag.py"

$AG init demo-agent                                # 1. create the guild (idempotent)
$AG bootstrap demo-agent                           # 2. read ALL shared context
echo "first session: guild verified" | $AG finish demo-agent   # 3. write today's log
```

Expected result: `init` prints the created directory layout, `bootstrap`
prints identity/rules/projects/focus, `finish` prints the log file path
(`log/daily/<date>-demo-agent.md`) — read that file back to confirm the
write landed. Two more one-liners worth trying:

```bash
$AG recall verified        # grep shared memory (exit 1 + "no matches" = empty guild, normal)
$AG doctor                 # health check: links, paths, core files
```

## Task routing — when the user asks for X, do this

| The user says… | What to run |
|---|---|
| "加入协会" / "join the guild" / "初始化" | `references/ONBOARDING.md` (one-time flow; fast path inside needs ~5 commands) |
| "帮我记住 X" / "remember this" | `echo "X" \| $AG finish <your-agent-name>` — or write the fact into `~/.agent-guild/memory/shared/` and register it in `memory/shared/INDEX.md` |
| "你记得吗 / 上次我们聊过 X" | `$AG recall <keyword> [<keyword> ...]` (AND search; `--all` = OR) |
| "告诉其他 agent X" / "hand off" | write a file into `~/.agent-guild/handoff/inbox/` (naming: `YYYYMMDD-HHMM-from-<you>-to-<target>-topic.md`) |
| "现在在做什么 / current focus" | read `~/.agent-guild/handoff/shared-state/current-focus.md` |
| "整理协会 / groom / cleanup" | `$AG groom --dry-run` first (report only), then `$AG groom` to apply (moves to archive, never deletes) |
| "这个工具在哪 / where is X" | `$AG tool <name>` (exit 3 = absent + install hint) |
| "换个电脑怎么搬 / cross-device" | `$AG port --dry-run` → `references/PORTABILITY.md` |

`<your-agent-name>` above = a short kebab-case name identifying the current
agent (e.g. `workbuddy`, `claude`, `cursor`) — pick one and reuse it.

## Session protocol — for agents on a joined machine

Once the guild exists on this machine, one pass through these steps per
session keeps shared memory coherent. All through `ag`, one command each.
No shell? Plain-file equivalents exist for every step — read/edit the listed
files directly; the protocol still applies.

- **Step 0 — ensure the guild exists**: `$AG init <name>` — idempotent;
  creates the skeleton on first run, never overwrites existing data.
- **Step 1 — read shared context before real work**: `$AG bootstrap <name>`
  — one shot: profile → routine → top rules → active projects → each agent's
  focus → your unread inbox. Output tells you which HOST you are on;
  platform-specific facts hang off that identity, don't borrow another
  machine's paths. Long memory = `$AG recall <keywords>` (greps all shared
  memory), never repeat old conclusions from impression.
  `memory/shared/INDEX.md` is the shared-facts catalog.
- **Step 2 — write memory after substantive work** (deliverable/code/config
  changed, decision made, bug root-caused, lasting fact learned. SKIP:
  greetings, lookups, short Q&A):

      echo "<summary>" | $AG finish <name>

  = summary into today's daily log + last_seen refresh + inbox report. Read
  back the output path to confirm it landed. Cross-agent-valuable facts →
  `memory/shared/` (register in `INDEX.md`); self-only → `memory/<name>/`.
  Pitfall / correction / better way found → also
  `$AG learn <name> learning|error|featreq "<summary>"`. Never log secrets;
  redact excerpts.
- **Step 3 — route skills & data into the guild (default-on)**:
  - Preferred: `$AG link-root <name>` — prints the plan first (dry-run);
    review it, then add `--apply` to turn your entire skills dir into ONE
    directory link to `~/.agent-guild/skills/`. New guild skills appear
    instantly afterwards, zero back-linking.
  - Fallback ladder: per-skill symlink → copy → readonly (ONBOARDING Step 3).
  - New skills → `~/.agent-guild/skills/<name>/`; persistent data →
    `skills_data/<name>/` (sensitive → `private/`); MCP/plugins/CLIs → their
    own dirs.
  - Sole exemption: runtime forces private paths → record the reason in
    registry.
- **Step 4 — self-audit (first join + monthly)**: `$AG adopt <name>` prints a
  dry-run report; `--apply` moves files (auto-verify, auto-rollback on
  failure, trash not delete). Health check: `$AG doctor`.

First time on this machine, or the user asked to join? →
`references/ONBOARDING.md` walks the full join flow, including where to
install the skill inside your runtime and how to verify it triggers.

## Self-check (before real work)

```bash
grep -q '"demo-agent"' ~/.agent-guild/registry.json && echo registered
grep -E '"protocol_version"' ~/.agent-guild/skills/agent-guild/manifest.json
```

Replace `demo-agent` with your own agent name. Not registered → run
onboarding first. Central major version > yours → re-run onboarding from the
top.

## The `ag` CLI — use it for all writes

Atomic + audited; concurrent appends serialized with an advisory lock (no
lost entries). Reads stay plain file reads. Full command table incl.
low-frequency ops (`register/send/log/focus/review/resolve/prune/audit/port`):
**`references/CAPABILITIES.md`**.

```bash
AG="python3 $HOME/.agent-guild/skills/agent-guild/scripts/ag.py"
$AG init demo-agent               # idempotent guild bootstrap
$AG bootstrap demo-agent          # read ALL shared context in one shot
$AG recall <kw> [...]             # grep shared memory (AND; --all=OR; --limit N)
echo "s" | $AG finish demo-agent  # close out: daily log + last_seen + inbox
$AG platform                      # which device am I on?
$AG tool <name>                   # tool path HERE (exit 3 = absent + install hint)
$AG doctor                        # dangling links / stale paths / drift
$AG status | adopt | port | groom | learn   # maintenance set
```

CLI unavailable? Every capability is reachable by plain file reads/writes —
Edit shared files in place, never Write-overwrite them.

## Capabilities at a glance

Detail for every row: `references/CAPABILITIES.md`.

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
| 10 | Cross-device | shared/platform/host scoping; `references/PORTABILITY.md` |

Cross-device hard rules (Capability 10): tool paths only via `ag tool`; no
machine-absolute paths in shared files (→ `hosts/<host-id>/host-notes.md`);
the guild is the source of truth (inbound symlinks only, internal symlinks
relative); platform-specific skills declare `"platforms"` in manifest.

## Security disclosure

Zero-dependency Python CLI + Markdown/JSON, all data local. Network use is
limited to its own release-version self-check (three fixed registry URLs,
short timeout, failure is non-fatal); deletions go to trash; every sensitive
operation is whitelisted and audited. Full mapping with source locations:
`references/SECURITY.md`.

## Spec

Manifest: `manifest.json` · Onboarding: `references/ONBOARDING.md` · Conventions:
`references/CONVENTIONS.md` · Capabilities: `references/CAPABILITIES.md` · Learnings:
`references/LEARNINGS.md` · Portability: `references/PORTABILITY.md` · Security:
`references/SECURITY.md` · Repository: https://github.com/dqsjqian/agent-guild

## Failure modes

Some files missing → read what exists, note the rest, don't block.
`registry.json` not writable → log the issue, proceed read-only.
Inbox file in unexpected format → read anyway, reply with a structured
request for clarity.
