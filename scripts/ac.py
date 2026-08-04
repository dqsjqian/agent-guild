#!/usr/bin/env python3
"""ac — Agent Guild CLI (zero-dependency, stdlib only).

Provides atomic, audited write operations for the shared state under
~/.agent-guild/, so multiple agents can update the same files without
corrupting them, and every write leaves an audit trail.

Reads stay plain file reads (zero cost). Only writes go through here.

Commands:
  status                 List registered agents + last_seen
  register <agent> ...   Register / update an agent entry (atomic + audit)
  last-seen <agent>      Update an agent's last_seen (atomic + audit)
  send <dst> <topic>     Write an inbox message from stdin (atomic + audit)
  log <agent> <title>    Append a daily log entry from stdin
  focus <agent> <title>  Update current-focus from stdin (atomic + audit)
  audit [n]              Show last n audit lines (default 20)
  prune [days]           List agents idle > N days (default 30) — does not delete

Exit codes: 0 ok, 1 error, 2 usage.
"""

import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CENTRAL = Path(os.environ.get("AGENT_GUILD_DIR", "~/.agent-guild")).expanduser()
REGISTRY = CENTRAL / "registry.json"
AUDIT = CENTRAL / "log" / "audit.jsonl"
DAILY = CENTRAL / "log" / "daily"
INBOX = CENTRAL / "handoff" / "inbox"
FOCUS = CENTRAL / "handoff" / "shared-state" / "current-focus.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def audit(action: str, detail: dict) -> None:
    """Append one audit line (atomic append)."""
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {"ts": now_iso(), "action": action, **detail},
        ensure_ascii=False,
    )
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def atomic_write_json(path: Path, data) -> None:
    """Write JSON via temp file + os.replace (atomic, no torn writes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ac-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_append(path: Path, content: str) -> None:
    """Append via temp copy + os.replace — safe against interleaved writers."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = path.read_text(encoding="utf-8") if path.exists() else ""
    body = body.rstrip("\n") + "\n" + content.rstrip("\n") + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ac-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_registry() -> dict:
    if not REGISTRY.exists():
        return {"protocol_version": "2.0", "central_dir": "~/.agent-guild/", "agents": {}}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(data: dict, agent: str, action: str) -> None:
    atomic_write_json(REGISTRY, data)
    audit(action, {"agent": agent, "file": "registry.json"})


def read_stdin() -> str:
    return sys.stdin.read().strip()


def cmd_status(_args=None) -> int:
    data = load_registry()
    agents = data.get("agents", {})
    if not agents:
        print("No agents registered.")
        return 0
    print(f"{'agent':<12} {'tier':<10} {'last_seen'}")
    print("-" * 60)
    for name, e in sorted(agents.items()):
        print(f"{name:<12} {e.get('install_tier','?'):<10} {e.get('last_seen','?')}")
    return 0


def cmd_register(args: list) -> int:
    if len(args) < 3:
        print("usage: ac register <agent> <home> <tier> [skills_root] [capabilities...]", file=sys.stderr)
        return 2
    name, home, tier = args[0], args[1], args[2]
    skills_root = args[3] if len(args) > 3 else None
    caps = args[4:] or ["read_files", "write_files"]
    data = load_registry()
    data.setdefault("agents", {})
    entry = data["agents"].get(name, {})
    entry.update(
        joined_at=entry.get("joined_at", now_iso()),
        home=home,
        last_seen=now_iso(),
        protocol_version="2.0",
        install_tier=tier,
        skills_root=skills_root,
        capabilities=caps,
    )
    data["agents"][name] = entry
    save_registry(data, name, "register")
    print(f"registered {name} (tier={tier})")
    return 0


def cmd_last_seen(args: list) -> int:
    if len(args) < 1:
        print("usage: ac last-seen <agent>", file=sys.stderr)
        return 2
    name = args[0]
    data = load_registry()
    agents = data.setdefault("agents", {})
    if name not in agents:
        print(f"agent '{name}' not registered — run: ac register {name} <home> <tier>", file=sys.stderr)
        return 1
    agents[name]["last_seen"] = now_iso()
    save_registry(data, name, "last_seen")
    print(f"{name} last_seen updated")
    return 0


def cmd_send(args: list) -> int:
    if len(args) < 2:
        print("usage: ac send <dst> <topic>  (message body from stdin)", file=sys.stderr)
        return 2
    dst, topic = args[0], args[1]
    body = read_stdin()
    if not body:
        print("empty message body", file=sys.stderr)
        return 2
    src = os.environ.get("AC_AGENT", "unknown")
    safe_topic = re.sub(r"[^A-Za-z0-9._-]", "-", topic)
    fname = f"from-{src}-to-{dst}-{safe_topic}.md"
    atomic_append(INBOX / fname, body)
    audit("send", {"from": src, "to": dst, "file": f"handoff/inbox/{fname}"})
    print(f"sent to {dst}: {fname}")
    return 0


def cmd_log(args: list) -> int:
    if len(args) < 2:
        print("usage: ac log <agent> <title>  (body from stdin)", file=sys.stderr)
        return 2
    agent, title = args[0], args[1]
    body = read_stdin()
    if not body:
        print("empty log body", file=sys.stderr)
        return 2
    day = datetime.now().strftime("%Y-%m-%d")
    path = DAILY / f"{day}-{agent}.md"
    content = f"\n## {title}\n\n{body}"
    atomic_append(path, content)
    print(f"appended to log/daily/{day}-{agent}.md")
    return 0


def cmd_focus(args: list) -> int:
    if len(args) < 2:
        print("usage: ac focus <agent> <title>  (body from stdin)", file=sys.stderr)
        return 2
    agent, title = args[0], args[1]
    body = read_stdin()
    block = (
        f"> Last updated: {now_iso()} by {agent}\n\n"
        f"## {title}\n\n{body}\n\n---\n"
    )
    existing = FOCUS.read_text(encoding="utf-8") if FOCUS.exists() else ""
    new = "# Current Focus\n\n" + block + existing.lstrip()
    FOCUS.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(FOCUS.parent), prefix=".ac-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new)
        os.replace(tmp, FOCUS)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    audit("focus", {"agent": agent, "title": title})
    print(f"current-focus updated by {agent}")
    return 0


def cmd_audit(args: list) -> int:
    n = int(args[0]) if args and args[0].isdigit() else 20
    if not AUDIT.exists():
        print("no audit trail yet")
        return 0
    lines = [l for l in AUDIT.read_text(encoding="utf-8").splitlines() if l.strip()][-n:]
    for line in lines:
        try:
            e = json.loads(line)
            print(f"{e.get('ts','?')}  {e.get('action','?'):<10} {e.get('agent',''):<12} {e.get('file', e.get('title',''))}")
        except json.JSONDecodeError:
            print(line)
    return 0


def cmd_prune(args: list) -> int:
    days = int(args[0]) if args and args[0].isdigit() else 30
    data = load_registry()
    now = datetime.now(timezone.utc)
    stale = []
    for name, e in data.get("agents", {}).items():
        ls = e.get("last_seen")
        if not ls:
            continue
        try:
            t = datetime.fromisoformat(ls.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            age = (now - t.astimezone(timezone.utc)).days
        except ValueError:
            continue
        if age > days:
            stale.append((name, ls, age))
    if not stale:
        print(f"no agents idle > {days} days")
        return 0
    print(f"agents idle > {days} days (candidates for manual removal):")
    for name, ls, age in stale:
        print(f"  {name:<12} last_seen={ls}  idle={age}d")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd, args = sys.argv[1], sys.argv[2:]
    table = {
        "status": cmd_status,
        "register": cmd_register,
        "last-seen": cmd_last_seen,
        "send": cmd_send,
        "log": cmd_log,
        "focus": cmd_focus,
        "audit": cmd_audit,
        "prune": cmd_prune,
    }
    fn = table.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
