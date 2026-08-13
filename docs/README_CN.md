# Agent Guild

> 一个协议——让任何足够聪明的 AI agent 只需读一个文件，就能加入你的共享记忆。

[English](README.md) | **中文**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-MVP-blue)]()
[![Protocol](https://img.shields.io/badge/protocol-v2.0-green)]()

---

**你大概率每天都在多个 AI agent 之间切换** —— Claude Code、Cursor、CodeBuddy、WorkBuddy、OpenClaw、Aider、GitHub Copilot Chat……每一个都是孤岛。每一个都各自有它对你的记忆，谁也不知道别人学到了什么。同样的偏好你要反复教。

**Agent Guild 终结这件事。** 它是一个**协议**——不是框架、不是服务、甚至不是库——让你机器上的多个 AI agent 通过纯 Markdown 文件 + Unix 软链共享一份记忆真相源。

---

## 30 秒理解

```
~/.agent-guild/                ← 你机器上的中央目录
│
│  ─── 协议层（强制）───
├── ONBOARDING.md                ← 新 agent 一次性入会流程
├── CONVENTIONS.md               ← 可选的、非规范性约定
├── identity/                    ← 你是谁（profile / 作息）
├── rules/                       ← 所有 agent 必须遵守的硬规则
├── toolchain/                   ← 工具 / 路径 / 配置
├── projects/                    ← 你在做什么
├── log/daily/                   ← 按 agent 分文件的日志（无写冲突）
├── handoff/                     ← 跨 agent 收件箱 + 共享状态
├── skills/agent-guild/    ← 从仓库根安装的 runtime skill（SKILL.md + manifest + scripts）
├── registry.json                ← 哪些 agent 加入了
│
│  ─── 约定层（可选，推荐）───
├── skills_data/<skill>/         ← 各 skill 自己的持久化数据（一个备份根管所有）
├── mcp/<server>/                ← 共享 MCP server 配置
├── plugins/<name>/              ← 共享插件
└── tools/<name>/                ← 共享 CLI 脚本/工具
```

每个加入的 agent 都有一个软链：

```bash
~/.<your-agent>/skills/agent-guild → ~/.agent-guild/skills/agent-guild/
```

就这。**没有 daemon。没有服务器。没有 npm install。没有第三方运行时。纯文件系统。**

---

## 为什么需要它（以及它跟别的方案有啥不同）

| 已有方案 | 它做什么 | 死穴 |
|---|---|---|
| ChatGPT Memory | 自动记住关于你的事实 | 锁死在 OpenAI 生态 |
| Claude Projects | 项目级上下文 | Anthropic 独享 |
| MemGPT / Letta | 单 agent 内部长期记忆 | 不跨 agent |
| Mem0 | 跨 agent 的记忆服务 | 需要服务化部署、REST API、绑死供应商 |
| MCP | 工具/资源协议 | 不是记忆方案 |
| **Agent Guild** | **跨厂商、本地优先、纯文本、零依赖** | **要求 agent 智力够读懂一份文件** |

差异化的关键：**我们不为每个 agent 写适配器**。我们写**一份** `SKILL.md`，任何足够聪明的 LLM 都能读懂并自我接入。读不懂的 agent……不配加入。这是设计本身。

---

## 用户怎么让任何 AI agent 加入

对 agent 说一句（任何语言、任何措辞）：

> "请读 `~/.agent-guild/ONBOARDING.md` 加入这个体系。"

就这一句话——这就是用户侧全部工作流。不需要装 CLI，不需要改配置。Agent 自己读这个文件，按里面的入会流程完成接入并报告。

如果某个 agent 搞不定这件事，**说明这个 agent 不够聪明，不配做你的工作伙伴** —— 你也借此知道了。这是内置的能力测试。

---

## 协议要求加入的 agent 做什么

协议显式区分**一次性入会** vs **持续运行能力**：

- **`ONBOARDING.md`**（一次性）：发现自己 runtime 的"用户可扩展 skill 目录"→ 安装（symlink → copy → readonly 自动降级）→ 闭环触发自检证明真的能调 → 在 `registry.json` 登记
- **`SKILL.md`**（每次按需触发）：读共享身份/规则/当前焦点；查收件箱/发消息；写当日日志；刷新 `last_seen`。这是加入后 agent 一直带着的运行时能力

详见：
- [`ONBOARDING.md`](ONBOARDING.md) —— 一次性入会流程
- [`SKILL.md`](../SKILL.md) —— 加入后的运行时能力
- [`SPEC.md`](SPEC.md) —— 完整协议规范
- [`CONVENTIONS.md`](CONVENTIONS.md) —— 非规范性的可选约定（如推荐的 skill 数据位置 `~/.agent-guild/skills_data/`）
- [`manifest.json`](../manifest.json) —— 机器可读

---

## 单一真相源 + 自动协议升级

每个加入 agent 的 `~/.<agent>/skills/agent-guild/` 是一条**软链**指回中央 `~/.agent-guild/skills/agent-guild/`。当本项目发布协议升级，你只更新中央目录，**用户机器上每个 agent 下次会话启动就看到新版本**。零推送、零版本检查、零 hash 比对。文件系统语义就这么干净利落。

用户自己的内容（`identity/` `rules/` `toolchain/` 等）**从不会被上游覆盖** —— 它们存在于软链外的同级目录，跟协议骨架物理隔离。

---

## 安装（用户视角）

### macOS / Linux / WSL / Git Bash

```bash
curl -fsSL https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.sh | bash
```

### Windows（PowerShell）

```powershell
iwr -useb https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.ps1 | iex
```

安装器只做**一件事**：在 `~/.agent-guild/`（Windows 上是 `%USERPROFILE%\.agent-guild\`）建中央目录 + seed 模板 + 末尾打印一条双语口令让你复制给 agent。**它不会动任何 agent 的 home 目录。** Agent 自己负责接入——这就是协议。

### 手动安装

```bash
git clone https://github.com/dqsjqian/agent-guild ~/.agent-guild
```

然后对你的 agent 说：

> "请阅读 `~/.agent-guild/ONBOARDING.md` 加入 Agent Guild。"

Agent 会自己想办法接入（软链、拷贝、或者只读 fallback——具体见 ONBOARDING.md）。

---

## 平台支持

| 系统 / Shell | 状态 |
|---|---|
| macOS | ✅ 一类支持 |
| Linux | ✅ 一类支持（任何 POSIX shell） |
| Windows + PowerShell 5.1+ | ✅ 一类支持（开发者模式或管理员权限） |
| Windows + WSL / Git Bash | ✅ 可用（Git Bash 需先设 `MSYS=winsymlinks:nativestrict`） |
| Windows + cmd.exe | ❌ 不支持（请用 PowerShell） |

### 升级（已经装过）

```bash
cd ~/.agent-guild && git pull   # （如果通过 git clone 装的）
# 或重新跑：
curl -fsSL https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.sh | bash
```

升级**永远不会**覆盖你的 `identity/` `rules/` `toolchain/`。只会更新协议骨架（`skills/`）。

---

## 多设备 / 备份

如果你有多台机器或换机，把整个 `~/.agent-guild/` 用 rsync / 私有 git 仓库 / iCloud Drive 备份即可。**注意不要把它推到公开仓库**——里面是你的私人记忆。

---

## 项目状态 & 设计哲学

**Phase 1（已完成）：协议 + 参考内容。** 目录骨架、`SKILL.md`、`manifest.json`、跨平台安装脚本。README 才是产品。

**Phase 2（3.0 已完成）：单文件 Python CLI**（`ag` 命令），子命令 `init / adopt / bootstrap / doctor / status / register / log / focus / send / audit / prune`。stdlib only，零第三方依赖，Windows / macOS / Linux 通用。

**Phase 3（进行中）：Adapters 目录。** 社区贡献各 agent 的接入指南。

我们**坚决不会**做：

- daemon（守护进程）
- pip / npm 上的包
- CRDT 同步引擎
- 云服务
- 聊天界面

这个项目是一份**约定**，不是软件。约定胜过配置。文件系统胜过数据库。软链胜过同步逻辑。

---

## License

MIT。详见 [LICENSE](LICENSE)。

## 作者

[@dqsjqian](https://github.com/dqsjqian) · 同时是 [soul-archive](https://github.com/dqsjqian/soul-archive)（数字人格存档）和 [ai-eight-creed](https://github.com/dqsjqian/ai-eight-creed)（AI 八耻八荣）的作者。

---

> *让你的 AI agent 们终于停止互相不认识。*
