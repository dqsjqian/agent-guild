# Agent Guild — Capabilities Reference

> Full detail behind SKILL.md's one-liners. SKILL.md keeps the mandatory
> contract; everything here is read-on-demand.

## The `ag` CLI — full reference

```bash
AG="python3 <SKILL_DIR>/scripts/ag.py"

$AG init <agent>                    # bootstrap the guild (idempotent)
$AG bootstrap <agent>               # read ALL shared context in one shot
$AG recall <kw> [...]               # grep shared memory (AND; --all = OR,
                                    #   --limit N; exit 1 on no match)
echo "<summary>" | $AG finish <agent>   # close out: daily log + last_seen +
                                    #   inbox report (--archive-inbox to file)
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

After **substantive work** (built/fixed/decided/learned a lasting fact), append
to `~/.agent-guild/log/daily/YYYY-MM-DD-<your-agent-name>.md` — per-agent file,
append-only. **Skip** greetings / lookups / short Q&A.

Prefer `ag finish` (auto-locates today's file + last_seen + inbox report);
`ag log <agent> "<title>"` works too.

Good entry: `## <title>` + What / Why / Result / Cross-agent note (if others need to know).

## Capability 5 — Refresh last_seen

Once per session, update your entry's `last_seen` (prefer `ag last-seen`,
fallback Edit). Never overwrite the whole registry — patch only your entry.

## Capability 6 — Where to persist shared data

New skill / MCP / plugin / tool / persistent data you install → **MUST** go
under `~/.agent-guild/{skills,skills_data,mcp,plugins,tools}/<name>/`, not a
private path (sole exemption in SKILL.md M3). The user backs up the whole
`~/.agent-guild/` with one command.

Directory-symlink runtimes (`ag link-root`): new skills installed into
`skills/` instantly appear in your runtime — no back-link action needed.

## Capability 7 — Cross-agent memory

| Path | What goes there |
|---|---|
| `~/.agent-guild/memory/<agent>/` | 该 agent 的私有记忆文件（`ag adopt` 搬进来后软链回原位，runtime 照常读写） |
| `~/.agent-guild/memory/shared/` | 跨 agent 都该知道的事实（用户偏好、项目约定、踩过的坑） |

写之前先读：别把别人已经记过的东西重复记一遍。新主题文件登记进
`memory/shared/INDEX.md`（目录索引，bootstrap/recall 的入口）；查旧事用
`ag recall <关键词>`，引用时给出文件路径。

## Capability 8 — Learning ledger (self-improvement loop)

三本跨 agent 台账在 `~/.agent-guild/learnings/`：`LEARNINGS.md`（纠正/知识盲区/最佳实践）·
`ERRORS.md`（命令/集成失败）· `FEATURE_REQUESTS.md`（用户想要但不存在的能力）。
完整规范（schema/触发词/晋升阈值/萃取流程）：`references/LEARNINGS.md`（权威）。

**触发速查**：

| 情况 | 动作 |
|---|---|
| 命令失败/异常/超时 | `ag learn <agent> error "<summary>"` |
| 用户纠正你（"不对"/"其实是"/"you're wrong"） | `ag learn <agent> learning "<summary>"`（category correction） |
| 你的知识过时 / API 行为和认知不符 | 同上（knowledge_gap） |
| 发现更好做法 | 同上（best_practice） |
| 用户想要不存在的能力 | `ag learn <agent> featreq "<summary>"` |

**复发追踪**：相同 `Pattern-Key` 的条目跨 agent 计数；`ag review` 报告达到阈值的组。

**晋升**（达到阈值后 MUST，详见 references/LEARNINGS.md）：
行为/偏好 → `rules/<topic>.md`；工具坑 → `toolchain/<tool>.md` 或 `memory/shared/`；
通用可复用解法 → 萃取为 skill 放 `skills/<name>/`（共享 skill bus，全 agent 即刻可用），
条目状态改 `promoted` / `promoted_to_skill`。

**红线**：不记 secrets/token/原始报文；条目只增不改，仅 `Status`/`Resolution` 可由任何 agent 更新。

## Capability 9 — Data hygiene (`ag groom`, protocol 3.2+)

协会用得越久，数据越容易劣化：current-focus 只增不减、daily log 无限堆积、
audit 越滚越大、resolved 台账条目永远躺在 live 文件里。groom 是自动防线：

- **自动触发**：`ag bootstrap` 尾部挂钩（速率限制默认 24h 一次），skill 正常
  触发即自动维护，无需用户点名。
- **版本自检**（3.9.0+）：bootstrap 尾部同样速率限制地对比三平台发布版本；
  默认 `check` 只提示，UPGRADE.md 里 `mode = apply` 则自动下载安装
  （仅替换 skill 本体，用户数据分毫不动），`mode = off` 关闭。
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

### 例行动作

```bash
$AG platform          # 我在哪台设备、能不能建软链
$AG port              # 便携性体检（DRY-RUN，只报告）
$AG port --apply      # 只做机械修复：host 状态归位、registry 按设备分块、
                      # 出站软链内化、绝对软链转相对、工具补平台声明
```

用户换新设备时：把目录搬过去 → `ag init <agent>`（自动认领新 host-id）→
`ag port` 看差异 → 按提示装缺的平台工具。老设备的数据一个字节都不用改。

完整规则（四条硬规矩、迁移流程）：`references/PORTABILITY.md`。

## What this skill does on your machine (capability disclosure)

一份零依赖 Python CLI（`scripts/ag.py`，只用标准库）+ 一堆 Markdown/JSON。
数据全部留在本机 `~/.agent-guild/`：无遥测、无统计、无账号、无后台进程。

| 敏感操作 | 干什么用 | 边界 |
|---|---|---|
| 网络请求 | `ag upgrade` 查版本 / 下载本 skill 自己的发布包；`ag bootstrap` 尾部的升级自检（3.9.0+，默认 24h 一次，UPGRADE.md 可调/可关） | 固定的公开版本接口 + 本项目 release 地址；请求不带任何本机数据；`--apply` 或 UPGRADE.md `mode=apply` 才下载，用户数据永不触碰 |
| 创建进程 | 回收站工具（`trash` / `gio trash` / PowerShell）、Windows `mklink /J` | 固定白名单命令 + 参数数组，全程无 shell 拼接 |
| 临时文件 | 原子写（写临时文件再 `os.replace`），探测本机能否建软链；并发追加用 sidecar `.ag-lock` 咨询锁串行化，防止同时写入丢条目 | `tempfile`，用完即清；锁文件不含数据，留在目标文件旁边 |
| 读环境变量 | `AGENT_GUILD_DIR` / `AG_AGENT` / `AG_HOST_ID` / `AG_PLATFORM` 等配置与平台探测 | 不读任何凭据，读到的东西不出网 |
| 删除文件 | 清理失效软链、轮转过期数据 | **从不硬删**：进系统回收站或 `~/.agent-guild/.trash/`；软链只解链不删目标 |
| 写文件 / 移动复制 | 把散落资产收敛进协会、归档过期数据 | 默认 dry-run，`--apply` 才动；写入限于 `~/.agent-guild/`；搬完校验、失败回滚；凭据目录不参与 |
| 修改权限 | 安装脚本给本项目自己的 CLI 加可执行位 | 仅 `scripts/ag.py` 与 `scripts/install.sh` |
| 采集系统信息 | 区分设备：OS / 架构 / 主机名 / 能否建软链 | 只写本机 `hosts/<host-id>/host.json`，不外传；`AG_HOST_ID` 可自定义替换主机名 |

逐条对应源码位置、验证命令与"刻意不做的事"清单见 `references/SECURITY.md`。
本 skill 不要求任何 agent 隐藏行为、绕过宿主确认或提升权限。

## Failure modes

- Some files missing → read what exists, note the rest, don't block.
- `registry.json` not writable → log the issue, proceed read-only.
- Inbox file in an unexpected format → read anyway, reply with a structured request for clarity.
