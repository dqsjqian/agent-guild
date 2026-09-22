# File Cleanup Preferences (template)

> Your preferences for file deletion. Agents follow these when you ask them to clean up directories.

## Default-deletable (no need to ask)

- Log files (`*.log`, `*.logg`, `*.err`) — including those being actively written; live processes will rebuild as needed
- Temporary scripts (`/tmp/*.sh`, `/tmp/*.py` etc., one-shot task artifacts)
- Test HTML / one-off rendering output
- `.DS_Store` (macOS Finder cache)

## Never delete (even if user says "logs are fine")

- Root-owned system/security logs (anything that would need `sudo`)
- `*.lock`, `*.sock`, `*.pid`, `*_push_allow` files (active-process IPC)
- System process working directories
- Application runtime metadata

## Deletion method (hard rule)

- **Always use `trash` command** to move to OS trash (macOS: `brew install trash`)
- **Never `rm -f`** — keeps files recoverable for ~30 days
- **Batch size**: max 10 files per batch, report between batches

## Decision flow

1. Is it a log? → yes, trash directly
2. Is it a temporary script? → yes, after task confirmed complete, trash
3. Unsure? → list it for the user, wait for confirmation
4. Looks like system/process file? → don't touch
