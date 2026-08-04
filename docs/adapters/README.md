# Adapters

This directory hosts integration guides for specific AI agent products. Each file describes:

- How that agent discovers `~/.agent-guild/`
- Whether it supports symlinks (or needs a fallback)
- Where in its config the user should reference the central directory
- Any agent-specific quirks

## Contributing a new adapter

Copy `_template.md` to `<agent-name>.md`, fill it in, open a PR.

We **do not** ship per-agent code adapters — adapters are documentation only. The protocol is designed so any sufficiently capable agent can self-onboard from `~/.agent-guild/ONBOARDING.md`, then use `SKILL.md` as its runtime capability.

## Existing adapters

- (none yet — be the first)
