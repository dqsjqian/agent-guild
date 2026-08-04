# Path Conventions (template)

> Where to put what on your machine. Customize for your setup.

## Central directories

| Path | Purpose |
|---|---|
| `~/.agent-commons/` | Cross-agent shared memory hub (this protocol) |
| `~/.skills_data/` *(optional)* | Skill runtime data root, if you use skill-based agents |

## Agent home pattern

| Path | Meaning |
|---|---|
| `~/.<agent-name>/` | Each agent's private home |
| `~/.<agent-name>/skills/agent-commons/` | Symlink to `~/.agent-commons/skills/` (joining symbol) |
| `~/.<agent-name>/MEMORY.md.local` *(optional)* | Agent's private preferences, NOT shared |

## Project workspaces (example)

| Path | Use |
|---|---|
| `~/Code/` | Work projects |
| `~/Learning/` | Personal open-source projects |
| `~/Projects/` | Mix |

## New skill / tool data

Put runtime data under `~/.skills_data/<name>/` (or wherever your conventions place it). Don't pollute `~/` with hidden dirs.
