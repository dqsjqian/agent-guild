# Security & Capability Disclosure

Agent Guild is a filesystem convention plus one zero-dependency Python CLI
(`scripts/ag.py`, standard library only). This document lists **every**
sensitive operation the CLI can perform, why it exists, and the boundary it
stays inside — so a reviewer can verify the claims against the source instead
of trusting a summary.

## Scope in one line

The CLI stores plaintext in `~/.agent-guild/` and does not upload memory
content or require an account. It checks public release versions and can
download this project's updates. `UPGRADE.md` controls bootstrap checks:
`mode = check` is the default, `off` disables them, and `apply` also installs
updates. `ag bootstrap <agent> --no-maintenance` skips both upgrade checks
and automatic grooming for that invocation.

Local storage does not control what a calling AI runtime does with text it
reads. The guild provides no encryption or per-agent access control:
`private/` and `memory/<agent>/` are naming conventions, and `recall` searches
all memory subdirectories. Git ignore rules do not restrict runtime reads
or other sync tools. Share only within the user's chosen trust boundary.

## Operation by operation

| Operation | Where | Why | Boundary |
|---|---|---|---|
| **HTTP request** | `_http_bytes`, `_http_json`, `fetch_*_version` | `ag upgrade` compares the installed version against the published one; `ag bootstrap` additionally runs a rate-limited self-check of the same version sources (3.9.0+, once per `UPGRADE.md` interval, default 24h) | Only the three public registry endpoints in `VERSION_SOURCES` and the project's own release URL. No request carries user data — no body, no query built from local state, only a `User-Agent` header. Runs only when the user invokes `ag upgrade`, or on bootstrap subject to the `UPGRADE.md` policy (`mode = off` disables) |
| **Downloading an archive** | `cmd_upgrade`, `_download_and_apply`, `maybe_auto_upgrade` | Install a newer version of this same skill | Only `github.com/dqsjqian/agent-guild/releases/download/...`, under `ag upgrade --apply` or a bootstrap self-check with `UPGRADE.md` `mode = apply`; extracted into a temp dir and validated (`SKILL.md` must be present) before anything is replaced. User data directories are never touched |
| **Process creation** | `to_trash`, `make_link` | Use the OS instead of reimplementing it: `trash` / `trash-put` / `gio trash` for recoverable deletes, PowerShell's Recycle Bin API on Windows, `cmd /c mklink /J` when symlinks need elevation | A fixed list of OS utilities with argument vectors (never a shell string, never user-supplied commands). No shell interpolation anywhere |
| **Temporary files** | `atomic_write_json`, `atomic_append`, `_append_lock`, `cmd_focus`, `link_capability`, `cmd_upgrade` | Atomic writes: write to a temp file in the same directory, then `os.replace`. A crash mid-write can never corrupt shared state. Concurrent appends (several agents writing the same daily log or ledger at once) are serialized by an advisory lock on a sidecar `.<name>.ag-lock` file — the lock deliberately does NOT live on the target file, because `os.replace` swaps the inode and a lock on the old inode protects nothing | `tempfile.mkstemp` / `mkdtemp`, cleaned up in `finally` / `trap`. Also used to probe whether this device supports symlinks at all. Lock files are empty (`fcntl.flock` on POSIX, `msvcrt.locking` on Windows), hold no data, and remain next to their target inside `~/.agent-guild/` |
| **Reading environment variables** | module level, `detect_os`, `host_id` | Configuration and platform detection | `AGENT_GUILD_DIR`, `AG_AGENT`, `AG_HOST_ID`, `AG_PLATFORM`, `APPDATA`, `PREFIX`, `ANDROID_ROOT`. No secrets are read, and nothing read is ever written to a network |
| **Deleting files** | `to_trash`, `drop_link`, `_replace_tree` | Remove stale links and rotate expired data | **Nothing is ever hard-deleted.** Deletes go to the OS trash or to `~/.agent-guild/.trash/<timestamp>/`. Links are unlinked, never trashed, so a trash helper can never follow one and take the target with it. `shutil.rmtree` is used only on temp/staging directories created in the same run |
| **Writing files** | everywhere | The guild is a set of Markdown/JSON files | Writes stay inside `~/.agent-guild/`. The only writes outside it are the links an agent asks for during `adopt` / `link-root`, pointing back into the guild, plus the inbound link `port --apply` recreates at a path whose payload it just moved in |
| **Changing permissions** | `scripts/install.sh`, `scripts/install.ps1` | `chmod +x` on this project's own CLI after download | Applies only to `scripts/ag.py` and `scripts/install.sh` inside the install directory |
| **Collecting system information** | `platform_facts`, `detect_os`, `detect_arch`, `host_id` | Tell devices apart so one guild directory can be carried between them: OS tag, CPU architecture, hostname, Python version, whether symlinks work | Written to `hosts/<host-id>/host.json` on the local disk and used for local decisions. Never transmitted. `AG_HOST_ID` lets a user replace the hostname with any label they prefer |
| **Moving / copying files** | `cmd_adopt`, `cmd_link_root`, `cmd_port`, `_groom` | Consolidate selected assets, archive expired data | `adopt`, `link-root` and `port` preview by default; `--apply` executes within the user's selected scope. `groom` applies retention unless `--dry-run`; bootstrap may invoke it automatically unless `--no-maintenance`. Adoption excludes connector stores. Memory-only use requires no asset migration |
| **Reading files** | `cmd_bootstrap` and friends | Read the user's own shared context: identity, rules, projects, focus, inbox | Reads inside `~/.agent-guild/`, plus the agent home directories listed in `registry.json` when auditing installs |

## Instruction-shaped text

`references/ONBOARDING.md` describes a joining procedure, so it is written in
the imperative ("run this", "register yourself"). That is procedural
documentation for a flow the **user** requests — not an instruction to act
without being asked. The file states this at the top: if the user has not
asked to join, the flow does not run.

The skill does not ask an agent to conceal actions, bypass a confirmation the
host requires, escalate privileges, or override the host's own rules.

## What the skill deliberately does not do

- No daemon, no background scheduler, no autostart hook
- No credential reading, no keychain access, no `.env` parsing
- No network destination outside the version-check endpoints listed above
- No hard deletes, no `rm -rf` of user directories, no recursive delete of any
  path the user did not point at
- No shell-string execution — every subprocess call uses an argument vector
- No code generation or `eval` of downloaded content; an upgrade only replaces
  this skill's own package files

## Verifying these claims

```bash
# every network call site
grep -n "urlopen\|Request(" scripts/ag.py

# every subprocess call site
grep -n "subprocess.run" scripts/ag.py

# every delete path
grep -n "rmtree\|unlink\|to_trash\|drop_link" scripts/ag.py

# the registry endpoints, in one place
grep -n -A6 "VERSION_SOURCES" scripts/ag.py

# every file-lock call site (append serialization)
grep -n "flock\|msvcrt\|ag-lock" scripts/ag.py
```

The CLI is a single file with no dependencies, so the audit surface is exactly
`scripts/ag.py` plus two installer scripts.

## Reporting a concern

Open an issue at <https://github.com/dqsjqian/agent-guild/issues>. The project
is MIT-licensed; the full source of everything described here ships inside the
package.
