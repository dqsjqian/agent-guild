---
name: agent-guild
description: |
  智能体协会（agent-guild）— cross-agent shared memory. 本机多个 AI agent 共享
  同一份身份、规则、记忆与交接消息 — 纯本地 Markdown/JSON，无服务器。

  触发（任何自然等价表达都算）：
  · 身份/习惯："我是谁" "我的身份/习惯/偏好" "who am I" "my routine"
  · 回忆/历史："你记得吗" "之前聊过" "上次我们" "what did we discuss"
  · 写记忆："帮我记住" "记一下" "沉淀一下" "remember this" "记到日志"
  · 跨 agent："告诉其他 agent" "交接给" "让 XX 也知道" "hand off to"
  · 当前状态："现在在做什么" "当前任务/焦点/进度" "current focus"
  · 数据卫生："整理一下协会" "清理过期数据" "协会瘦身/归档" "防止数据劣化"
    "groom" "cleanup" "archive old data"
  · 跨设备："换了台电脑" "另一台机器" "Windows/Linux 上用不了" "这台设备"
    "这个工具在哪" "cross-device" "another machine" "which platform"
  · 加入："加入协会" "初始化协会" "join agent guild" "install this skill"

  能力：读/写共享身份、规则、焦点；收件箱交接；每日日志；跨 agent 学习台账
  （错误/纠正/特性请求 → 复发追踪 → 晋升为规则或共享 skill）；数据卫生
  （bootstrap 后自动 groom 归档过期数据）；跨设备可移植（shared/platform/host
  三层作用域，`ag platform` / `ag tool <name>` / `ag port`）；
  `ag init/adopt/link-root/bootstrap/doctor/groom/upgrade/learn/review/resolve`。
  未加入？先跑 docs/ONBOARDING.md。
slug: agent-guild
displayName: 智能体协会 Agent Guild
display_name: 智能体协会 Agent Guild
display_name_en: Agent Guild
description_zh: 跨 agent 共享记忆协议，本机多个 AI 共用一份身份/规则/记忆，可跨设备搬运
description_en: Cross-agent shared memory protocol — one identity, rules and memory for every AI on your devices
author: dqsjqian
protocol_version: "3.3"
version: "3.8.0"
platforms: ["macos", "windows", "linux", "android", "ios"]
license: MIT
homepage: https://github.com/dqsjqian/agent-guild
repository: https://github.com/dqsjqian/agent-guild
agent_created: true
---

# Agent Guild — Runtime Skill

> Local-first cross-agent shared memory. Join once, share identity/rules/focus
> across every agent on this machine. Data lives at `~/.agent-guild/`
> (plaintext, yours, never uploaded).
>
> The directory is also safe to carry between devices: facts are scoped as
> shared / platform / host, so a second machine reads what applies to it and
> recognises the rest as belonging elsewhere (Capability 10).

`SKILL_DIR` below means the directory containing this file. CLI entry point:
`python3 <SKILL_DIR>/scripts/ag.py` (referred to as `ag`). Requires Python 3.9+
(stdlib only, no third-party packages). On Windows use `python` instead of
`python3` if that is what your PATH exposes.

## Quick start (for an agent that has NOT joined yet)

1. Run the onboarding flow: `~/.agent-guild/ONBOARDING.md` (or this skill's
   `docs/ONBOARDING.md`) — discover your runtime's user-extensible skills dir,
   consolidate it into the guild with ONE directory link
   (`ag link-root <me> --apply`; fallbacks: per-skill symlink → copy →
   readonly), run the closed-loop trigger test, register yourself in
   `registry.json`.
2. Then come back here — this file is your everyday capability.

## Mandatory Session Contract (once per session, MUST)

> ⛔ 这些是**强制动作**，不是建议。每次会话开始（或首次需要用户上下文时）执行，不要等用户点名。
> 全部通过 `ag` 一条命令完成，别手工开五个文件。
>
> **No shell / no Python?** Every step below has a plain-file equivalent — read
> the listed files directly and Edit them in place. The contract still applies;
> only the mechanism changes. On Windows, use `python` if `python3` is not on PATH.

### M0 — Ensure the guild exists (first use / every session start)

```bash
python3 <SKILL_DIR>/scripts/ag.py init <your-agent-name>
```

幂等：目录不存在则建全套骨架 + 落地本 skill；已存在则只补缺失项，**绝不覆盖已有数据**。
输出 `initialized` = 首次自举，`verified` = 已存在。

### M1 — Bootstrap: read shared context BEFORE real work

```bash
python3 <SKILL_DIR>/scripts/ag.py bootstrap <your-agent-name>
```

一次读全：用户画像 → 日程 → 最高优先级戒律 → 在做的项目 → 各 agent 当前焦点 → 你的未读收件箱。

输出开头会先告诉你**你在哪台设备上**（host-id / 平台 / 软链能力 / 本机专属笔记）——
平台或机器相关的东西都挂在这个身份上，别拿别的设备的路径当本机的用。

| 文件 | 内容 |
|---|---|
| `identity/profile.md` | 用户是谁 |
| `identity/ROUTINE.md` | 日程 / 习惯 |
| `rules/universal.md` | 最高优先级戒律 |
| `projects/active.md` | 用户当前在做什么 |
| `handoff/shared-state/current-focus.md` | 各 agent 当前焦点 |
| `hosts/<host-id>/host-notes.md` | 只在本设备成立的事实（本机路径、本机装了什么） |

读到什么就按什么做。**没读就动手 = 违反协议。** 之后按需再读 `toolchain/*.md`、其他 `rules/*.md`。

### M2 — Write memory after substantive work

完成**实质工作**后 MUST 追加 daily log（见 Capability 4）。满足任一即"实质工作"：
产出交付物（代码/文档/报告/网站/脚本）・改了代码或配置・做了技术决策・修复错误并定位根因・学到可复用的长期事实（用户偏好/项目约定/坑）。

**跳过**：寒暄、简单查询、短问答、纯检索。

跨 agent 有价值的事实 → 也写 `memory/shared/`；只对你自己有意义的 → 留在 `memory/<你的名字>/`。

**踩坑/被纠正/发现更好做法 → 同时记学习台账**（Capability 8，`ag learn`）。
用户纠正了你・命令非预期失败・用户想要不存在的能力・发现某任务更优解 ——
这些是全 guild 的免疫素材，别只留在当天日志里。**绝不记录 secrets/原始报文**，摘录要脱敏。

### M3 — Route skills & data into the guild (default-on)

- **接入形态（首选）**：你的 skills 目录 = 协会 skills 目录。跑
  `ag link-root <me> --apply` 把整个 user-extensible skills 目录换成指向
  `~/.agent-guild/skills/` 的**一条目录级软链**（外部源软链收编进协会、
  旧的 per-skill 软链清理）。此后协会每多一个 skill，你**零操作**立即可见。
- **降级阶梯**：runtime 不跟随目录级软链、或 skills 目录里混有平台托管条目
  （`__skillhub` / connector 等）→ per-skill 软链 → copy → readonly（见
  ONBOARDING.md Step 3）。
- **装新 skill**：MUST 装到 `~/.agent-guild/skills/<name>/`（目录级软链下
  装完即全 runtime 可见；per-skill 模式下再从那里链回自己 runtime）。
- **写持久化数据**：MUST 写 `~/.agent-guild/skills_data/<skill>/`（敏感数据拆 `private/`）。
- **MCP / 插件 / CLI 工具**：分别进 `mcp/`、`plugins/`、`tools/`。
- **唯一豁免**：你的 runtime 强制私有路径（如 platform-managed）——在 registry 里记录原因即可，不算违反。

### M4 — Self-audit: adopt what's still scattered (first join + monthly)

```bash
python3 <SKILL_DIR>/scripts/ag.py adopt <your-agent-name>            # DRY-RUN, 只报告
python3 <SKILL_DIR>/scripts/ag.py adopt <your-agent-name> --apply    # 真的搬 + 软链回来
```

扫五类资产：`skills` / `skills_data` / `mcp` / `tools` / `memory`。
**默认 dry-run**，先把清单给用户看；`--apply` 才动手（搬完自动验证软链，失败自动回滚，删除走废纸篓）。

自动排除：可重建缓存（`.venv`/`node_modules`/`__pycache__`）、凭证、runtime 内部元数据、平台托管包（`__skillhub`/`connector-*`）、connector 型 skill。

健康检查（发现悬空软链 / 旧路径残留 / registry 漂移）：

```bash
python3 <SKILL_DIR>/scripts/ag.py doctor
```

## Self-check (each session, before real work)

```bash
# 1. registered?
grep -q '"<your-agent-name>"' ~/.agent-guild/registry.json && echo registered || echo not_registered
# 2. protocol version compatible?
grep -E '"protocol_version"' ~/.agent-guild/skills/agent-guild/manifest.json | head -1
```
Not registered → run onboarding first. Central major version > yours → re-run
onboarding from the top.

## The `ag` CLI — use it for all writes

Writes to shared files are atomic + audited when done through the CLI
(zero-dependency Python, stdlib only). Reads stay plain file reads.

```bash
AG="python3 <SKILL_DIR>/scripts/ag.py"

$AG init <agent>                    # bootstrap the guild (idempotent)
$AG bootstrap <agent>               # read ALL shared context in one shot
$AG platform                        # which device am I on? os/arch/host-id/links
$AG tool <name>                     # resolve a tool's path HERE (exit 3 = not
                                    #   available on this platform + how to install)
$AG tools                           # declared tools x availability on this device
$AG port [--apply]                  # portability audit for multi-device guilds
$AG adopt <agent>                   # dry-run: what of mine belongs in the guild?
$AG adopt <agent> --apply           # move it in + symlink back
$AG doctor                          # dangling links / stale paths / drift
$AG status                          # who is registered
$AG register <agent> <home> <tier>  # join (tier: symlink|copy|readonly)
$AG last-seen <agent>               # refresh presence
echo "<body>" | $AG send <dst> <topic>        # handoff message
echo "<body>" | $AG log <agent> "<title>"     # daily log
echo "<body>" | $AG focus <agent> "<title>"   # update current-focus
echo "<body>" | $AG learn <agent> <kind> "<summary>"  # learning ledger entry
                                             #   kind: learning|error|featreq
                                             #   opts: --area X --priority Y --pattern-key K
$AG review                          # pending stats + promotion candidates
$AG resolve <ID> ["note"]           # mark entry resolved (+ note)
$AG groom [--dry-run]               # data hygiene: archive expired data
                                    #   (auto-runs after bootstrap, 1/day)
$AG audit                           # audit trail of shared writes
$AG prune 30                        # list idle agents
```

If the CLI is unavailable (no Python, sandboxed runtime), fall back to the
manual file operations below — Edit in place, never Write-overwrite a shared
file. Every capability in this skill is reachable by plain file reads/writes;
the CLI only adds atomicity and an audit trail.

## Capability 1 — Read shared user context

| File | Purpose |
|---|---|
| `~/.agent-guild/identity/profile.md` | Who the user is |
| `~/.agent-guild/identity/ROUTINE.md` | Daily schedule / routines |
| `~/.agent-guild/rules/universal.md` | **Mandatory commandments** — highest priority |
| `~/.agent-guild/rules/public-repo.md` | Public-repo hard rules |
| `~/.agent-guild/rules/file-cleanup.md` | File deletion preferences |
| `~/.agent-guild/rules/safety.md` | Safety guardrails |
| `~/.agent-guild/projects/active.md` | What the user is working on |
| `~/.agent-guild/handoff/shared-state/current-focus.md` | What any agent is focused on now |
| `~/.agent-guild/toolchain/*.md` | Tool-specific config — read on demand |

Read on demand; don't slurp everything every turn.

## Capability 2 — Update current-focus

`current-focus.md` is the "what's hot right now" board. When you start or
finish a major task, prepend your block (`ag focus` or manual Edit in place).
Never rewrite history other agents wrote.

## Capability 3 — Check inbox / send messages

Inbox: `~/.agent-guild/handoff/inbox/`.
- Receive: `ls ~/.agent-guild/handoff/inbox/ | grep "to-<your-agent-name>-"`, read, act, then `mv` to `handoff/archive/`.
- Send: `from-<src>-to-<dst>-<topic>.md` — write for a recipient with no context (what you did, what's left, where artifacts are).

## Capability 4 — Daily log

After **substantive work** (built/fixed/decided/learned a lasting fact), append to `~/.agent-guild/log/daily/YYYY-MM-DD-<your-agent-name>.md` — per-agent file, append-only. **Skip** greetings / lookups / short Q&A.

Good entry: `## <title>` + What / Why / Result / Cross-agent note (if others need to know).

## Capability 5 — Refresh last_seen

Once per session, update your entry's `last_seen` (prefer `ag last-seen`, fallback Edit). Never overwrite the whole registry — patch only your entry.

## Capability 6 — Where to persist shared data

New skill / MCP / plugin / tool / persistent data you install → **MUST** go under `~/.agent-guild/{skills,skills_data,mcp,plugins,tools}/<name>/`, not a private path (唯一豁免见 M3). The user backs up the whole `~/.agent-guild/` with one command.

目录级软链（`ag link-root`）接入的 runtime：装进 `skills/` 的新 skill 自动出现在你的技能列表里，不需要任何回链动作。

## Capability 7 — Cross-agent memory

| Path | What goes there |
|---|---|
| `~/.agent-guild/memory/<agent>/` | 该 agent 的私有记忆文件（`ag adopt` 搬进来后软链回原位，runtime 照常读写） |
| `~/.agent-guild/memory/shared/` | 跨 agent 都该知道的事实（用户偏好、项目约定、踩过的坑） |

写之前先读：别把别人已经记过的东西重复记一遍。

## Capability 8 — Learning ledger (self-improvement loop)

三本跨 agent 台账在 `~/.agent-guild/learnings/`：`LEARNINGS.md`（纠正/知识盲区/最佳实践）·
`ERRORS.md`（命令/集成失败）· `FEATURE_REQUESTS.md`（用户想要但不存在的能力）。
完整规范（schema/触发词/晋升阈值/萃取流程）：`docs/LEARNINGS.md`（权威）。

**触发速查**：

| 情况 | 动作 |
|---|---|
| 命令失败/异常/超时 | `ag learn <agent> error "<summary>"` |
| 用户纠正你（"不对"/"其实是"/"you're wrong"） | `ag learn <agent> learning "<summary>"`（category correction） |
| 你的知识过时 / API 行为和认知不符 | 同上（knowledge_gap） |
| 发现更好做法 | 同上（best_practice） |
| 用户想要不存在的能力 | `ag learn <agent> featreq "<summary>"` |

**复发追踪**：相同 `Pattern-Key` 的条目跨 agent 计数；`ag review` 报告达到阈值的组。

**晋升**（达到阈值后 MUST，详见 docs/LEARNINGS.md）：
行为/偏好 → `rules/<topic>.md`；工具坑 → `toolchain/<tool>.md` 或 `memory/shared/`；
通用可复用解法 → 萃取为 skill 放 `skills/<name>/`（共享 skill bus，全 agent 即刻可用），
条目状态改 `promoted` / `promoted_to_skill`。

**红线**：不记 secrets/token/原始报文；条目只增不改，仅 `Status`/`Resolution` 可由任何 agent 更新。

## Capability 9 — Data hygiene (`ag groom`, protocol 3.2+)

协会用得越久，数据越容易劣化：current-focus 只增不减、daily log 无限堆积、
audit 越滚越大、resolved 台账条目永远躺在 live 文件里。groom 是自动防线：

- **自动触发**：`ag bootstrap` 尾部挂钩（速率限制默认 24h 一次），skill 正常
  触发即自动维护，无需用户点名。
- **保真原则**：只搬不删 —— 过期数据进 `log/archive/`、
  `handoff/shared-state/archive/`、`learnings/archive/` 或可恢复的 `.trash/`；
  手写的、无时间戳的 focus 块永远不动；未读收件箱永远只报告不搬。
- **策略可调**：所有阈值在 `~/.agent-guild/RETENTION.md`（用户文件，升级不覆盖）。
- **可审计**：每次 groom 写 `log/audit.jsonl` + `.groom.json` 状态。

## Capability 10 — Cross-device portability (protocol 3.3+)

一份协会目录可能被搬到好几台设备上（Win / mac / Linux / 安卓 / iOS）。
协会**自己不做同步**，它只保证：被任何载体搬过去之后，每台设备都分得清
"这条对我成立 / 这条不属于我"。三层作用域：

| 作用域 | 判定 | 放哪 |
|---|---|---|
| **shared** | 换设备照样成立 | 原样：`identity/` `rules/` `projects/` `memory/` `learnings/` `skills/` |
| **platform** | 只对某个 OS+架构成立 | `tools/<name>/tool.json` 声明各平台，二进制放 `tools/<name>/bin/<os>-<arch>/` |
| **host** | 只对本机成立 | `hosts/<host-id>/`：`host.json`、`host-notes.md`、`VERSION`、`groom.json` |

判定口诀：**这条信息换台设备还成立吗？** 成立 → shared；同 OS 才成立 → platform；只有本机成立 → host。

### 四条硬规矩

1. **取工具路径只走 `ag tool <name>`**，不要写死 `~/.agent-guild/tools/...` ——
   那个路径在别的平台是死的。exit 3 表示"本平台没有"，顺带给安装指引。
2. **共享文件里不写机器绝对路径**（`/Users/xxx/`、`C:\Users\xxx\`）。
   本机专属路径写 `hosts/<host-id>/host-notes.md`。
3. **协会是本体，软链只许进不许出。** 协会内的软链指向外部路径 = 违规：
   其他设备只能看到断链。把 payload 搬进协会，让外部路径软链回来
   （`ag port --apply` 自动做这件事）。协会内部的软链用相对路径。
4. **平台专属 skill 要声明**：manifest 里写 `"platforms": ["windows"]` 之类；
   不写 = 全平台可用。

### 例行动作

```bash
$AG platform          # 我在哪台设备、能不能建软链
$AG port              # 便携性体检（DRY-RUN，只报告）
$AG port --apply      # 只做机械修复：host 状态归位、registry 按设备分块、
                      # 出站软链内化、绝对软链转相对、工具补平台声明
```

用户换新设备时：把目录搬过去 → `ag init <agent>`（自动认领新 host-id）→
`ag port` 看差异 → 按提示装缺的平台工具。老设备的数据一个字节都不用改。

## Failure modes

- Some files missing → read what exists, note the rest, don't block.
- `registry.json` not writable → log the issue, proceed read-only.
- Inbox file in an unexpected format → read anyway, reply with a structured request for clarity.

## Spec

- Manifest: `manifest.json`
- Onboarding (one-time): `docs/ONBOARDING.md`
- Conventions: `docs/CONVENTIONS.md`
- Learning ledger (self-improvement): `docs/LEARNINGS.md`
- Cross-device portability: `docs/PORTABILITY.md`
- Repository: https://github.com/dqsjqian/agent-guild
- License: MIT
