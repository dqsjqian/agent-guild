# Agent Guild

> Give your local AI assistants one shared set of preferences, project conventions, and work handoffs.

**English** | [中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/dqsjqian/agent-guild/blob/main/LICENSE)
[![Protocol](https://img.shields.io/badge/protocol-v3.3-green)](references/SPEC.md)

Agent Guild is for **one person using multiple trusted AI assistants with local filesystem access**.
It stores shared context in Markdown and JSON under `~/.agent-guild/`, so you can inspect, edit,
and back it up while switching assistants. A runtime skill defines the reading and writing
contract; a Python CLI handles concurrent writes, search, and archiving.

## Try the outcome first: A remembers, B finds it

After installing and connecting two assistants, test a harmless demonstration convention:

1. Tell assistant A:
   > Remember this lasting demo convention: deliverables for the demo project must include validation results.
   > Save it in the guild's `memory/shared/demo.md`, add it to `memory/shared/INDEX.md`, and report the saved path.
2. Switch to assistant B:
   > Search the guild for the “demo project” delivery convention. Repeat it and cite the source file.
3. Check that B finds the same content and file. Remove the demo convention and its index entry when finished.

That is the useful acceptance test; placing a skill on disk is only the first installation step.
Keep lasting preferences and project conventions in identity, rules, or shared memory.
`log/daily/` records session history and is not a substitute for lasting memory.
Assistants still need to read the relevant context; Agent Guild does not inject all history into every answer.

## Where it fits

| Your need | What Agent Guild provides |
|---|---|
| Switch between two or more local assistants without repeating conventions | Shared identity, rules, project state, and searchable memory files |
| See and correct what assistants remember | Ordinary Markdown and JSON, with no proprietary database |
| Hand off unfinished work | Shared focus, inbox messages, and daily logs for the receiving assistant to read |
| Move personal working context to another device | Shared, platform, and host scopes; you choose how to transfer files |
| Also consolidate skills, tools, and their data | An optional full shared-hub mode; trying memory does not require migrating those assets |

It does not provide multi-user access isolation, automatic device synchronization, or background task execution.
An assistant without access to the local files cannot use the directory directly. An assistant that can read
files but cannot load custom skills can read the protocol manually; it needs a session reminder rather than
automatic skill triggering.

The tradeoff is **less infrastructure and inspectable files, with assistants following a shared contract
and the user managing filesystem access**. The CLI requires Python 3.9+ and uses only its standard library.
There is no server or resident process.

## Install and connect

### 1. Create the central directory

macOS / Linux / WSL / Git Bash (Bash and curl required):

```bash
curl -fsSL https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.sh | bash
```

Windows (PowerShell 5.1+):

```powershell
iwr -useb https://raw.githubusercontent.com/dqsjqian/agent-guild/main/scripts/install.ps1 | iex
```

The installer downloads the protocol and CLI, seeds templates, and prints the joining instruction.
It does not modify an assistant's own directories. To inspect the source first, download and read
the installer before running it.

### 2. Connect each assistant

For a first trial, ask for shared memory only:

> Read `~/.agent-guild/ONBOARDING.md` and connect shared memory only. Keep my existing skills and tools directories in place.

If you want to consolidate more assets, explicitly choose the full shared hub:

> Read `~/.agent-guild/ONBOARDING.md` and join in full shared-hub mode. Report the directories moved and the installation tier used.

Full mode moves eligible assets into the guild and attempts a directory link for the assistant's skills.
Fallbacks are per-skill links, copies, or manual reading. See the [joining flow](references/ONBOARDING.md).
Then run the two-assistant test above to confirm that shared memory is actually retrievable.

### Install from source

Keep the **source checkout** separate from your **private guild data**. Run these commands in a source
workspace of your choice:

```bash
git clone https://github.com/dqsjqian/agent-guild agent-guild-source
python3 agent-guild-source/scripts/ag.py init demo-agent
```

Replace `demo-agent` with your assistant's name. On Windows, use `python` if that is your Python command.
`init` creates the runtime directory at `~/.agent-guild/` and installs the skill; then give your assistant
the joining instruction above. Do not clone the source repository directly into the private data directory.

## What you control

- **Memory content:** identity, rules, and project files are user-owned. Assistants should record relevant summaries; keep passwords and tokens out of shared memory.
- **Network and updates:** installation downloads files. By default, `bootstrap` checks three public version sources at most once per device every 24 hours, without uploading memory content. In `UPGRADE.md`, `mode = check` reports updates, `mode = apply` downloads and installs them, and `mode = off` disables automatic checks. Manual `upgrade` remains available.
- **Context-only reads:** `bootstrap <agent> --no-maintenance` skips automatic grooming and upgrade checks for that invocation without changing saved policies.
- **Automatic archiving:** by default, `bootstrap` attempts grooming once per device every 24 hours. It archives expired logs, focus entries, and resolved learning entries, and rotates the audit log; unread messages are only reported. Preview with `groom --dry-run` and adjust retention in `RETENTION.md`. Archiving preserves history and does not reduce the total size of the directory's history.
- **Sharing boundaries:** `memory/<agent>/` and `private/` are organizational conventions, not access controls or encryption. Programs with access to those files may still read them. Connect assistants you trust.
- **Models and backups:** Agent Guild stores its data files locally. Whether an assistant sends their contents to a model service depends on that assistant's runtime; your chosen backup or sync tool also has its own data handling.

These boundaries describe Agent Guild itself. Other skills and tools in shared directories have their own
permissions and behavior. See the [security and capability disclosure](references/SECURITY.md).

## Daily use and updates

Ask a connected assistant to “remember this project convention,” “find our previous decision,”
“update the current focus,” or “groom the guild.” See the [capabilities reference](references/CAPABILITIES.md)
for commands. CLI writes and checks happen when invoked, not in the background.

Check for and apply an update to Agent Guild:

```bash
python3 "$HOME/.agent-guild/skills/agent-guild/scripts/ag.py" upgrade
python3 "$HOME/.agent-guild/skills/agent-guild/scripts/ag.py" upgrade --apply
```

On Windows, use `python` and the corresponding `$env:USERPROFILE` path. You can also rerun the installer.
Updates replace Agent Guild's protocol files while preserving identity, rules, and project content.
Linked installations see central updates; copy installations require the assistant's copy to be refreshed.
See the [update procedure](references/ONBOARDING.md#step-7--update-protocol-how-to-stay-current-as-the-central-skill-evolves).

## Files and multiple devices

```text
~/.agent-guild/
├── identity/ rules/ projects/     Identity, conventions, project state
├── memory/shared/                Lasting shared facts and INDEX.md
├── memory/<agent>/               Memory organized by assistant
├── handoff/                      Focus, inbox, archives
├── log/ learnings/               Session logs, corrections, lessons
├── hosts/<host-id>/              Local paths, platform, installation state
├── skills/agent-guild/           Agent Guild runtime skill
├── RETENTION.md UPGRADE.md       Retention and automatic-check policies
└── registry.json                Registration records
```

Full shared-hub mode also uses `skills/`, `skills_data/`, `mcp/`, `plugins/`, and `tools/`.
Shared facts stay in their usual directories. Tools for a specific OS or architecture use platform
declarations; machine-specific paths belong under `hosts/<host-id>/`. Local file locks do not resolve
conflicts introduced by synchronization between devices.

To move, copy the required directories using your chosen method, run `init` and `port` on the new device,
and address missing platform tools. Review personal data and credentials included in a backup;
keep private guild data out of public repositories. See [portability and backups](references/PORTABILITY.md).

## Project and documentation

Agent Guild is a local filesystem protocol and its reference implementation. It supports platform detection
and several link fallbacks. Whether a skill loads depends on the assistant runtime's filesystem permissions
and extension support; joining includes verification.

- [Runtime skill](SKILL.md) · [Full specification](references/SPEC.md) · [Conventions](references/CONVENTIONS.md)
- [Joining flow](references/ONBOARDING.md) · [Capabilities](references/CAPABILITIES.md) · [Machine-readable manifest](manifest.json)
- [Contribute an integration guide](https://github.com/dqsjqian/agent-guild/blob/main/references/adapters/README.md)

License: [MIT](https://github.com/dqsjqian/agent-guild/blob/main/LICENSE). Author: [@dqsjqian](https://github.com/dqsjqian).
