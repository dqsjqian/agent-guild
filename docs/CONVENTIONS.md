# Agent Guild — Conventions (default-on)

> This file describes **default-on conventions** for things that live *alongside* the core protocol. They are NOT optional: every joined agent MUST follow them, with one escape hatch — if your runtime *requires* a private location (e.g. a platform-managed skills dir), use it and note the reason in `registry.json`. That counts as compliant.
>
> These conventions sit a layer *above* the core protocol (identity / rules / handoff / daily logs — see [`SPEC.md`](SPEC.md) and [`ONBOARDING.md`](ONBOARDING.md)). The protocol layer is the hard MUST; this convention layer is default-on with a documented escape hatch.

## Why conventions, not rules

The core protocol (`SPEC.md`) is deliberately small — just enough to let agents share identity, rules, and coordination state. Anything else lives outside the protocol.

But over time, multiple skills end up wanting *similar* things:

- A place to persist their own per-skill data
- A place to put per-skill configuration
- A way to declare external dependencies

If every skill picks its own `~/.<random-name>/` directory, users end up with a scattered mess of "where does this skill keep its stuff?". Conventions give skills a single default answer to questions like that (escape hatch: runtime-forced private paths, noted in registry).

**A skill that follows the conventions here gets the user a uniform backup/sync story for free.** A skill that ignores them still works fine; it just doesn't compose as neatly with sibling skills.

## Convention 0 — Shared skill bus

> **Default location for skills that should be available to every joined agent: `~/.agent-guild/skills/<skill-name>/`**

The `skills/` directory is **not** just where Agent Guild keeps its own runtime skill — it is the **shared skill bus** for the whole protocol. Any skill placed under `~/.agent-guild/skills/<name>/` is reachable by every joined agent on the machine, not just the one that installed it.

```
~/.agent-guild/skills/
├── agent-guild/          ← the protocol's own runtime skill (always present)
├── soul-archive/           ← e.g. installed once, available to every agent
├── wechat-publisher/       ← same
├── <your-skill>/           ← any future shared skill
└── ...
```

### Important properties

- **Joined agents SHOULD prefer `~/.agent-guild/skills/<name>/` over installing a private copy.** If a user wants the wechat-publisher skill, install it once into the central bus; every agent then symlinks/copies/reads from there using the same Tier-1/2/3 install pattern from `ONBOARDING.md` Step 3.
- **Each skill subdirectory is owned by that skill.** Agent Guild does NOT validate or interpret its contents.
- **Naming** (MUST): lowercase-hyphenated slug `[a-z0-9-]` (e.g. `qq-mail`, `agent-browser`, `wecom-doc-to-html`). No CJK characters, no spaces, no `-skill` suffix — the directory name is the identity, not a display label. The same rule applies to `skills_data/` and `connectors/` subdirectories.
- **Discovery**: agents looking for a capability the user has previously installed SHOULD check `~/.agent-guild/skills/` first before asking the user to install something.

### Why this matters

Without this convention, each agent maintains its own private skill collection — a useful skill installed in agent A is invisible to agent B. With this convention, **install once, use everywhere**.

## Convention 1 — Skill data root

> **Default location for per-skill persistent data: `~/.agent-guild/skills_data/<skill-name>/`**

Skills that need to persist non-trivial data — accumulated user models, knowledge graphs, conversation logs, learned patterns, caches — **MAY** use a subdirectory under `~/.agent-guild/skills_data/` named after the skill itself.

```
~/.agent-guild/
├── identity/         ← protocol layer (read by all agents)
├── rules/            ← protocol layer
├── handoff/          ← protocol layer
├── log/              ← protocol layer
├── registry.json     ← protocol layer
│
├── skills/           ← shared skill bus (Convention 0)
│   ├── agent-guild/
│   ├── soul-archive/
│   └── ...
│
└── skills_data/      ← convention layer (skill-private)
    ├── soul-archive/    ← managed by soul-archive
    ├── <other-skill>/   ← managed by that skill
    └── ...
```

### Important properties

- **Agent Guild does not read, write, validate, or interpret anything inside `skills_data/`.** It belongs entirely to the skill that owns the subdirectory.
- **Skills following this convention get free backup/sync semantics**: when a user backs up `~/.agent-guild/`, all participating skills come along.
- **Skills NOT following this convention still work fine.** A skill is free to put its data anywhere it wants (`~/.skills_data/`, `~/.<skill-name>/`, `~/Library/Application Support/<bundle>/`, etc.) — Agent Guild doesn't care.
- **No naming registry, no central authority.** Just don't pick a name that collides with another well-known skill.

### When NOT to use this convention

- **Highly sensitive data that should never sync to cloud / git / multi-device backups.** Users may rsync `~/.agent-guild/` to private storage; if your skill captures e.g. medical or financial records the user did not consent to share, keep that data outside this directory or split it into a subdirectory the user can `.gitignore` separately.
- **Data that should be wiped on logout / shared across users / OS-managed.** Use the platform-appropriate location (`/tmp`, `/var`, OS keychain, etc.).
- **Data that fundamentally belongs to the agent's runtime, not the user.** Stay inside the agent's home directory.

### Privacy layering inside `skills_data/<skill-name>/`

Skills that hold **mixed-sensitivity data** SHOULD split into clearly named subdirectories so users can apply different sync/backup policies:

```
~/.agent-guild/skills_data/<skill-name>/
├── public/      ← safe to sync everywhere (preferences, profiles, settings)
├── private/     ← sensitive — recommend .gitignore by default
└── ...
```

This is default-on, not optional. The point is: **make it easy for users to back up safely without surprising them**.

> **Credentials are NOT skill data.** Login cookies, API keys, OAuth tokens and lock files belong under `~/.agent-guild/connectors/<name>/` (Convention 6), not here — `skills_data/` is for a skill's user-facing data, and mixing secrets into it defeats the whole point of having a clean backup root.

### Default `.gitignore` template

If the user wants to version-control `~/.agent-guild/` for personal multi-device sync via private git, this is a sensible starting point:

```gitignore
# Skill private data — keep out of any git history
skills_data/*/private/

# Per-skill caches that don't need to follow you across devices
skills_data/*/cache/

# Common scratch / log paths some skills use
skills_data/*/tmp/
skills_data/*/.tmp/

# Rebuildable binaries / dependency trees — never sync these
skills_data/*/browsers/
skills_data/*/node_modules/
skills_data/*/.venv/
**/*.app
**/*.pid

# Connector credentials — stay local, never in git
connectors/
```

## Convention 2 — Skill metadata file (optional)

A skill that publishes data under `skills_data/<skill-name>/` MAY drop a `_meta.json` at the top of its subdirectory describing what's in there:

```json
{
  "skill_name": "soul-archive",
  "skill_version": "3.0",
  "skill_repo": "https://github.com/dqsjqian/soul-archive",
  "data_format_version": "3.0",
  "privacy_layers": ["public", "private"],
  "owner_writes_only": true
}
```

This is purely informational — for users browsing their own data, and for tooling that wants to enumerate installed skills. Agent Guild does not consume this file.

## Convention 3 — Shared MCP servers

> **Default location for MCP servers shared across joined agents: `~/.agent-guild/mcp/<server-name>/`**

MCP servers that are agent-agnostic (not bound to a specific runtime's lifecycle) SHOULD be installed under `~/.agent-guild/mcp/<server-name>/`. The directory MAY contain:

- Server config files (e.g. `config.json`, `.env.example`)
- Local server implementation (a self-contained binary, Node/Python script, etc.)
- A `README.md` for the user describing what the server does and how to wire an agent to it

Joined agents that want to use the server SHOULD point their runtime's MCP config at this central location instead of installing a private copy. **Install once, used by all.**

## Convention 4 — Shared plugins

> **Default location for cross-agent plugins: `~/.agent-guild/plugins/<plugin-name>/`**

For plugins that aren't tied to a single agent's runtime — e.g. browser/editor/IDE extensions, tools that hook into a generic plugin protocol, scripts that several different agents might invoke. Each subdirectory is owned by the plugin.

If a plugin is fundamentally **agent-specific** (e.g. only loadable by one specific runtime), it belongs in that agent's own home, not here.

## Convention 5 — Shared CLI tools

> **Default location for shared command-line scripts and utilities: `~/.agent-guild/tools/<tool-name>/`**

For helper scripts and small utilities the user (or any agent) might run from any shell session. Examples: an `ag` CLI for browsing the central directory, a custom `gh-helper.sh`, a Python script that reformats agent logs.

The user MAY add `~/.agent-guild/tools/*/bin/` to `$PATH` if they want shell-level access. This is a user convenience, not a protocol requirement.

## Convention 6 — Connector credentials

> **Default location for connector credentials: `~/.agent-guild/connectors/<connector-name>/`**

Login cookies, API keys, OAuth tokens, CLI lock files — anything a connector or integration uses to authenticate — belong under `connectors/<name>/`, **not** `skills_data/`. `skills_data/` is for a skill's user-facing data; credentials are a different category with different handling:

- **Manually placed, never auto-adopted.** `ag adopt` will not move credentials into the guild (moving secrets into a directory the user backs up is a risk, not a benefit). You place them there yourself.
- **Gitignored by default.** The `.gitignore` template above excludes `connectors/` entirely, so credentials never leak into a private git mirror or an accidental public push.
- **Naming**: same lowercase-hyphenated slug as `skills/` and `skills_data/`.

```
~/.agent-guild/connectors/
├── qq-mail/config.json       ← login credentials for the qq-mail connector
├── clawhub/lock.json         ← publish lock / session state
└── <other-connector>/...
```

If a credential must be kept *outside* the guild entirely (e.g. OS keychain, a runtime-managed secret store), that is a legitimate escape hatch — note it in `registry.json` just like any other runtime-forced private path.

## Convention 7 — Conventions are default-on; protocol stays versioned

**Conventions in this file are default-on, not optional** (escape hatch documented at the top). The *protocol* layer (`SPEC.md`) remains intentionally small and stable — a change to hard protocol requirements still goes through a normal versioned spec bump, not by quietly rewording a convention.

If you build a skill that wants to read another skill's `skills_data/`, that's between the two skills — don't lobby for the protocol to standardize the cross-skill access pattern.

---

## Summary table

| Convention | Path | What goes there | Read by |
|---|---|---|---|
| 0 — Shared skill bus | `~/.agent-guild/skills/<name>/` | Skill packages available to every joined agent | Every joined agent |
| 1 — Skill data root | `~/.agent-guild/skills_data/<name>/` | Per-skill persistent data | Owning skill (others MAY read if documented) |
| 2 — Skill metadata | `skills_data/<name>/_meta.json` | Optional informational descriptor | Users / inspection tooling |
| 3 — Shared MCP | `~/.agent-guild/mcp/<name>/` | Agent-agnostic MCP servers | Any agent that wires up to them |
| 4 — Shared plugins | `~/.agent-guild/plugins/<name>/` | Cross-agent plugins (browser/editor/IDE extensions) | Any compatible host |
| 5 — Shared CLI tools | `~/.agent-guild/tools/<name>/` | Scripts / utilities runnable from any shell | Anyone — agent or human |
| 6 — Connector credentials | `~/.agent-guild/connectors/<name>/` | Login cookies / API keys / lock files (gitignored) | The owning connector |
| 7 — Default-on, versioned | — | Conventions are default-on; hard protocol changes stay versioned | — |

---

## Why this matters

Without conventions, the ecosystem fragments: every skill ships its own data location, its own backup story, its own privacy layering — and users end up tracking N different `~/.something/` directories.

With these conventions, users get **one directory to back up, one directory to inspect, one directory to migrate to a new machine**. Each skill stays fully autonomous, but they end up cooperating where it matters: the user's mental model.

**And every joined agent gets the same shared toolkit** — install a useful skill once, every agent on the machine can trigger it. Wire up a useful MCP server once, every agent can use it.

> *Convention over configuration, when configuration adds no value.*
