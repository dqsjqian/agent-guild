# <Agent Name> Adapter

> Replace `<Agent Name>` with the actual agent (e.g. "Claude Code", "Cursor", "Aider").

## Agent home

- **Default home directory**: `~/.<agent-dir>/`
- **User-extensible skills directory**: `<the path the runtime is allowed to load third-party skills from — NOT the built-in/whitelisted dir>`
- **Skill mechanism**: <e.g. "reads `<user-skills-dir>/*` at session start", or "uses a Custom Skills setting in the UI", or "no skill mechanism — read SKILL.md directly each session">

## Symlink support

- [ ] Symlinks work
- [ ] Symlinks not supported — must `cp` and re-fetch periodically
- [ ] Other (explain)

## How to join

```bash
# Either rely on the global installer:
curl -fsSL https://raw.githubusercontent.com/dqsjqian/agent-commons/main/install.sh | bash

# Or do it manually:
mkdir -p <user-extensible-skills-dir>
ln -sfn ~/.agent-commons/skills/agent-commons <user-extensible-skills-dir>/agent-commons
```

Then start a new session with the agent and say:

> "Read `~/.agent-commons/ONBOARDING.md` and follow the joining flow."

(Onboarding is one-time. After joining, the agent uses `~/.agent-commons/skills/agent-commons/SKILL.md` automatically as its runtime capability.)

## Verification

After the agent reports having joined:

```bash
cat ~/.agent-commons/registry.json | grep -A 7 '"<agent-name>"'
ls ~/.agent-commons/log/daily/$(date +%Y-%m-%d)-<agent-name>.md 2>/dev/null
```

The registry entry should include `install_tier`, `install_verified`, and `skills_root`.

## Known quirks

- (none / list any)

## Author of this adapter

`@<your-github-handle>` — opened in PR #N
