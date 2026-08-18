#!/usr/bin/env python3
"""ag — Agent Guild CLI (zero-dependency, stdlib only).

Bootstraps and maintains the shared cross-agent directory at ~/.agent-guild/.
Writes are atomic + audited so multiple agents can share state without
corrupting it. Reads stay plain file reads (zero cost).

Runs on Windows / macOS / Linux (and POSIX-ish mobile shells) with Python 3.8+.
No third-party packages.

Commands:
  init [agent]            Bootstrap ~/.agent-guild/ (idempotent, safe to re-run)
  find-root [agent]       Locate your user-extensible skills dir — instant,
                          never asks the user, READONLY fallback if not found
  adopt [agent]           Scan agent home for adoptable assets (DRY-RUN report)
  adopt --apply [agent]   Move assets into the guild + link back
  bootstrap               Print all shared context (identity/rules/projects/focus)
  doctor                  Health check: broken links, stale paths, version drift
  upgrade                 Check 3 platforms for a newer skill version (dry-run)
  upgrade --apply         Download + install the latest version, keep user data
  status                  List registered agents + last_seen
  register <agent> <home> <tier> [skills_root] [caps...]
  last-seen <agent>       Refresh an agent's presence
  send <dst> <topic>      Write an inbox message from stdin
  log <agent> <title>     Append a daily log entry from stdin
  focus <agent> <title>   Update current-focus from stdin
  learn <agent> <kind> "<summary>"   Learning-ledger entry (details from stdin)
                          kind: learning | error | featreq
                          opts: --area A --priority P --category C --pattern-key K
  review                  Ledger stats: pending items + promotion candidates
  resolve <ID> [note ...] Mark a ledger entry resolved (+ resolution note)
  audit [n]               Show last n audit lines (default 20)
  prune [days]            List agents idle > N days (default 30) — never deletes

Env:
  AGENT_GUILD_DIR   override central dir (default ~/.agent-guild)
  AG_AGENT          your agent name (used by `send`, and as default for
                    init/adopt when no agent argument is given)

Exit codes: 0 ok, 1 error, 2 usage.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Tuple

CENTRAL = Path(os.environ.get("AGENT_GUILD_DIR", "~/.agent-guild")).expanduser()
REGISTRY = CENTRAL / "registry.json"
AUDIT = CENTRAL / "log" / "audit.jsonl"
DAILY = CENTRAL / "log" / "daily"
INBOX = CENTRAL / "handoff" / "inbox"
FOCUS = CENTRAL / "handoff" / "shared-state" / "current-focus.md"
VERSION = CENTRAL / "VERSION"
LEARNINGS = CENTRAL / "learnings"

PROTOCOL_VERSION = "3.1"

# Learning ledger: kind -> (file, ID prefix). Protocol 3.1+.
LEDGERS = {
    "learning": ("learnings/LEARNINGS.md", "LRN"),
    "error": ("learnings/ERRORS.md", "ERR"),
    "featreq": ("learnings/FEATURE_REQUESTS.md", "FEAT"),
}
LEDGER_ALIASES = {
    "learn": "learning", "insight": "learning",
    "err": "error", "bug": "error",
    "feat": "featreq", "feature": "featreq", "fr": "featreq",
}

# Remote version sources, queried WITHOUT any auth (any ordinary user can
# self-check). Order is the reporting priority; the newest wins.
VERSION_SOURCES = [
    ("skillhub", "https://api.skillhub.cn/api/v1/search?q=agent-guild"),
    ("github", "https://github.com/dqsjqian/agent-guild/releases/latest"),
    ("clawhub", "https://clawhub.ai/api/v1/skills/agent-guild/versions"),
]

# Download source for upgrades — our own GitHub release zip (most stable).
GITHUB_RELEASE_ZIP = (
    "https://github.com/dqsjqian/agent-guild/releases/download/"
    "v{ver}/agent-guild-skill-v{ver}.zip"
)

# ---------------------------------------------------------------- skeleton ---

SKELETON = [
    "identity", "rules", "toolchain", "projects",
    "handoff/inbox", "handoff/archive", "handoff/shared-state",
    "log/daily", "log/decisions", "learnings",
    "skills", "skills_data", "mcp", "plugins", "tools", "memory", "connectors",
]

PLACEHOLDERS = {
    "identity/profile.md": "# Who the user is\n\n_Fill this in — every joined agent reads it._\n",
    "identity/ROUTINE.md": "# Daily routine\n\n_Schedule, habits, commute, working hours._\n",
    "rules/universal.md": "# Universal rules (highest priority)\n\n_Mandatory commandments every agent obeys._\n",
    "projects/active.md": "# Active projects\n\n_What the user is working on right now._\n",
    "handoff/shared-state/current-focus.md": "# Current Focus\n\n_Latest focus block goes on top._\n",
    "memory/README.md": (
        "# memory/\n\n"
        "Cross-agent memory. Agent-private memory files adopted from each\n"
        "runtime live under `memory/<agent>/`; facts worth sharing across all\n"
        "agents go in `memory/shared/`.\n"
    ),
    "learnings/LEARNINGS.md": (
        "# Learnings\n\n"
        "Cross-agent ledger: corrections, knowledge gaps, best practices.\n"
        "Entries are append-only; only Status/Resolution may be edited later.\n"
        "Never log secrets — redacted summaries only.\n\n"
        "**Categories**: correction | insight | knowledge_gap | best_practice\n"
        "**Statuses**: pending | in_progress | resolved | wont_fix | promoted | promoted_to_skill\n\n"
        "---\n"
    ),
    "learnings/ERRORS.md": (
        "# Errors\n\n"
        "Cross-agent ledger: command failures, integration errors, unexpected\n"
        "behavior. Redacted excerpts only — no secrets, no raw transcripts.\n\n"
        "---\n"
    ),
    "learnings/FEATURE_REQUESTS.md": (
        "# Feature Requests\n\n"
        "Cross-agent ledger: capabilities the user wanted but nothing provides.\n\n"
        "---\n"
    ),
}

# --------------------------------------------------------------- adoption ---

# Where each asset class lands inside the guild.
# Note: `connectors` (credential store) is deliberately NOT adoptable — it is a
# manually-placed directory. Adopt must never auto-move credentials into a
# directory the user backs up.
ADOPT_DESTS = {
    "skills": "skills",
    "skills_data": "skills_data",
    "mcp": "mcp",
    "tools": "tools",
    "memory": "memory",
}

# Never adopt: rebuildable caches, credential stores, VCS/OS noise,
# runtime-internal bookkeeping, and the protocol's own skill.
EXCLUDE_NAMES = {
    ".venv", "venv", "node_modules", "__pycache__", ".git", ".DS_Store",
    ".env", "secrets", "cache", ".cache", "tmp", ".tmp", "dist", "build",
    "browsers",  # Playwright / Puppeteer browser binaries — rebuildable
    "agent-guild", "agent-commons",
    # runtime-internal metadata: owned by the host, not portable skills
    "agent-created-skills.json", "_bm_skillid_migration.json",
    "settings.json", "config.json", "mcp.json", ".skill-lock.json",
}

# Rebuildable binaries and runtime artifacts: adopt nothing with these suffixes.
EXCLUDE_SUFFIXES = (".app", ".pid", ".log", ".pyc", ".tmp")

# Platform-managed / vendor-wired packages: moving them breaks the host.
EXCLUDE_SUBSTRINGS = ("__skillhub", "connector-", "-connector", "marketplace",
                      "_migration", "-lock")

# Markers that identify a skill as host-wired rather than portable: its
# capability comes from a connector / MCP server the runtime manages, so moving
# the files detaches it from that wiring. Detected by content, not by a
# hardcoded vendor list — that keeps this portable across ecosystems.
HOST_WIRED_MARKERS = (
    "connector to access",
    "via connector",
    "connector config",
    "mcp connector",
    "official mcp",
    "(connector)",
)

# Users can add their own glob-ish patterns, one per line, in
# ~/.agent-guild/.adoptignore (blank lines and #comments ignored).
ADOPTIGNORE = ".adoptignore"

# Candidate locations per agent home, by asset class.
# `connectors` is intentionally absent: credentials are manually placed, never
# auto-adopted (see ADOPT_DESTS note above).
CANDIDATE_LAYOUT = {
    "skills": ["skills"],
    "skills_data": ["skills_data", "skill_data"],
    "mcp": ["mcp", "mcp_servers"],
    "tools": ["tools", "bin"],
    "memory": ["memory", "memories"],
}

# Agent-private memory files worth adopting (relative to agent home).
MEMORY_FILES = ["MEMORY.md", "SOUL.md", "USER.md", "IDENTITY.md"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def audit(action: str, detail: dict) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts": now_iso(), "action": action, **detail}, ensure_ascii=False)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ag-", suffix=".tmp")
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
    path.parent.mkdir(parents=True, exist_ok=True)
    body = path.read_text(encoding="utf-8") if path.exists() else ""
    body = body.rstrip("\n") + "\n" + content.rstrip("\n") + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ag-", suffix=".tmp")
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
        return {
            "protocol_version": PROTOCOL_VERSION,
            "central_dir": "~/.agent-guild/",
            "agents": {},
        }
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(data: dict, agent: str, action: str) -> None:
    atomic_write_json(REGISTRY, data)
    audit(action, {"agent": agent, "file": "registry.json"})


def read_stdin() -> str:
    return sys.stdin.read().strip()


def default_agent(args: list) -> str:
    """Agent name from argv, else $AG_AGENT, else 'unknown'."""
    for a in args:
        if not a.startswith("-"):
            return a
    return os.environ.get("AG_AGENT") or "unknown"


# Candidate user-extensible skills roots, checked in order. Full-disk probing
# is deliberately avoided — it is slow (30s+) and rarely needed.
def _candidate_roots(name: str) -> list:
    home = Path.home()
    roots = [
        home / f".{name}" / "skills",
        home / f".{name}",
        home / ".config" / name / "skills",
        home / ".config" / name,
    ]
    if sys.platform == "darwin":
        roots += [
            home / "Library" / "Application Support" / name / "skills",
            home / "Library" / "Application Support" / name,
        ]
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            roots += [Path(appdata) / name / "skills", Path(appdata) / name]
    return roots


def cmd_find_root(args: list) -> int:
    """Locate a user-extensible skills dir WITHOUT asking the user.

    Order: registry entry → common paths. Never full-disk probes. If nothing
    is found, print a READONLY verdict and exit 0 — joining read-only is the
    correct fallback, not a failure. Silent and autonomous by design.
    """
    agent = default_agent(args)
    entry = load_registry().get("agents", {}).get(agent, {})

    sr = entry.get("skills_root")
    if sr and sr != "platform-managed":
        p = Path(sr).expanduser()
        if p.is_dir():
            print(f"SKILLS_ROOT={p}\nTIER=copy-or-symlink  (from registry)")
            return 0

    for p in _candidate_roots(agent):
        if p.is_dir():
            print(f"SKILLS_ROOT={p}\nTIER=symlink-if-supported")
            return 0

    print("SKILLS_ROOT=not-found")
    print("TIER=readonly")
    print("VERDICT=no user-extensible skills dir found — skip installation and "
          "join read-only (read central files each session). Do NOT ask the user.")
    return 0


def agent_home(name: str) -> Path | None:
    """Resolve an agent's home dir: registry first, then ~/.<name>/."""
    entry = load_registry().get("agents", {}).get(name, {})
    home = entry.get("home")
    if home:
        p = Path(home).expanduser()
        if p.is_dir():
            return p
    p = Path(f"~/.{name}").expanduser()
    return p if p.is_dir() else None


def to_trash(path: Path) -> bool:
    """Recoverable delete, cross-platform.

    Tries the OS trash helper first (`trash` on macOS, `gio trash` / `trash-put`
    on Linux, Recycle Bin via PowerShell on Windows); otherwise moves the path
    into the guild's own .trash/<timestamp>/ so nothing is ever unrecoverable.
    """
    for cmd in (["trash"], ["trash-put"], ["gio", "trash"]):
        exe = shutil.which(cmd[0])
        if exe:
            try:
                if subprocess.run(cmd + [str(path)],
                                  capture_output=True).returncode == 0:
                    return True
            except OSError:
                pass
    if os.name == "nt" and shutil.which("powershell"):
        ps = (
            "Add-Type -AssemblyName Microsoft.VisualBasic; "
            "[Microsoft.VisualBasic.FileIO.FileSystem]::"
            f"{{0}}('{path}','OnlyErrorDialogs','SendToRecycleBin')"
        ).format("DeleteDirectory" if path.is_dir() else "DeleteFile")
        try:
            if subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                              capture_output=True).returncode == 0:
                return True
        except OSError:
            pass
    graveyard = CENTRAL / ".trash" / datetime.now().strftime("%Y%m%d-%H%M%S")
    graveyard.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(path), str(graveyard / path.name))
        return True
    except OSError:
        return False


def make_link(link: Path, target: Path) -> Tuple[bool, str]:
    """Create link -> target. Symlink first; on Windows fall back to a
    directory junction / hard link, which need no special privileges."""
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
        return True, "symlink"
    except (OSError, NotImplementedError) as e:
        first = e
    if os.name == "nt":
        if target.is_dir():
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                               capture_output=True)
            if r.returncode == 0:
                return True, "junction"
        else:
            try:
                os.link(str(target), str(link))
                return True, "hardlink"
            except OSError:
                pass
    return False, f"link failed: {first}"


# ------------------------------------------------------------------- init ---

def read_runtime_version() -> dict:
    """Read the installed runtime version anchor (~/.agent-guild/VERSION)."""
    if not VERSION.is_file():
        return {}
    out = {}
    for line in VERSION.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def write_runtime_version(proto: str, skill: str) -> None:
    """Persist the applied protocol/skill version to the anchor file."""
    VERSION.write_text(
        "# Agent Guild runtime version — managed by `ag init` / `ag upgrade`.\n"
        "# Records the version last applied to this central dir. Do not edit.\n"
        f"protocol_version={proto}\n"
        f"skill_version={skill}\n",
        encoding="utf-8",
    )


def current_versions(skill_src: Path) -> Tuple[str, str]:
    """(protocol_version, skill_version) of the skill package `ag` runs from —
    i.e. the newest version the user has at hand."""
    m = skill_src / "manifest.json"
    if m.is_file():
        try:
            d = json.loads(m.read_text(encoding="utf-8"))
            return (d.get("protocol_version", PROTOCOL_VERSION),
                    d.get("skill_version", "0"))
        except (OSError, ValueError):
            pass
    return (PROTOCOL_VERSION, "0")


def _version_gt(a: str, b: str) -> bool:
    """True if semantic version a > b (e.g. '3.4.0' > '3.3.1')."""

    def parts(v: str) -> list:
        out = []
        for seg in str(v).replace("-", ".").split("."):
            out.append(int(re.sub(r"\D", "", seg) or "0"))
        return out

    pa, pb = parts(a), parts(b)
    for x, y in zip(pa, pb):
        if x != y:
            return x > y
    return len(pa) > len(pb)


def _replace_tree(src: Path, dst: Path) -> None:
    """Replace dst with a copy of src (temp dir + atomic-ish rename).
    VCS / OS noise and caches are never copied."""
    ignore = shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", ".venv")
    tmp = dst.with_name(dst.name + ".new")
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(src, tmp, ignore=ignore)
    shutil.rmtree(dst, ignore_errors=True)
    tmp.rename(dst)


def cmd_init(args: list) -> int:
    """Bootstrap the central dir. Idempotent: never clobbers existing data."""
    agent = default_agent(args)
    fresh = not CENTRAL.exists()

    created_dirs, created_files = [], []
    for rel in SKELETON:
        p = CENTRAL / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created_dirs.append(rel)

    for rel, body in PLACEHOLDERS.items():
        p = CENTRAL / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
            created_files.append(rel)

    if not REGISTRY.exists():
        atomic_write_json(REGISTRY, {
            "protocol_version": PROTOCOL_VERSION,
            "central_dir": "~/.agent-guild/",
            "agents": {},
        })
        created_files.append("registry.json")

    # Make sure the protocol's own skill is present AND current in the bus.
    # Version-aware self-heal: compare the version this `ag` runs from against
    # the installed anchor (~/.agent-guild/VERSION). If the user upgraded the
    # skill and re-ran init, refresh protocol-owned files (skill package + root
    # docs) while leaving ALL user data (identity/rules/log/handoff/skills_data/
    # connectors/memory/registry) untouched.
    own_skill = CENTRAL / "skills" / "agent-guild"
    skill_src = Path(__file__).resolve().parent.parent  # .../skills/agent-guild
    cur_proto, cur_skill = current_versions(skill_src)
    inst = read_runtime_version()
    inst_proto = inst.get("protocol_version", "")
    inst_skill = inst.get("skill_version", "")

    skill_missing = not (own_skill / "SKILL.md").exists()
    skill_outdated = bool(inst_skill) and _version_gt(cur_skill, inst_skill)
    proto_changed = bool(inst_proto) and inst_proto != cur_proto
    upgrading = skill_outdated or proto_changed

    skill_status = "already current"
    if skill_missing:
        if (skill_src / "SKILL.md").is_file() and skill_src.resolve() != own_skill.resolve():
            own_skill.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_src, own_skill, dirs_exist_ok=True)
            skill_status = "installed"
        else:
            skill_status = "MISSING — copy the agent-guild skill package into skills/agent-guild/"
    elif upgrading:
        if skill_src.resolve() != own_skill.resolve() and (skill_src / "SKILL.md").is_file():
            _replace_tree(skill_src, own_skill)
            skill_status = f"upgraded {inst_skill or '?'} → {cur_skill}"
        else:
            skill_status = f"anchor bumped to {cur_skill}"
    elif not inst_skill:
        skill_status = "anchor repaired"

    write_runtime_version(cur_proto, cur_skill)

    # Seed / refresh the root protocol docs. First run seeds them; an upgrade
    # follows the version; when already current they are left alone.
    for doc in ("ONBOARDING.md", "CONVENTIONS.md", "SPEC.md"):
        target = CENTRAL / doc
        src = None
        for cand in (own_skill / "docs" / doc, skill_src / "docs" / doc):
            if cand.is_file():
                src = cand
                break
        if src is None:
            continue
        body = src.read_text(encoding="utf-8")
        if not target.exists():
            target.write_text(body, encoding="utf-8")
            created_files.append(doc)
        elif upgrading and target.read_text(encoding="utf-8") != body:
            target.write_text(body, encoding="utf-8")
            created_files.append(doc)

    audit("init", {"agent": agent, "fresh": fresh, "dirs": len(created_dirs)})

    print(f"{'initialized' if fresh else 'verified'} {CENTRAL}")
    print(f"  protocol_version : {cur_proto}")
    print(f"  skill_version    : {cur_skill}")
    print(f"  dirs created     : {len(created_dirs)}" + (f" ({', '.join(created_dirs)})" if created_dirs else ""))
    print(f"  files created    : {len(created_files)}" + (f" ({', '.join(created_files)})" if created_files else ""))
    print(f"  own skill        : {skill_status}")
    print()
    print("Next: `ag adopt <agent>` to see what can move in, then `ag register`.")
    return 0


# ---------------------------------------------------------------- upgrade ---

def _verkey(v: str) -> Tuple[int, ...]:
    """Semantic-version tuple for comparison."""
    return tuple(int(re.sub(r"\D", "", seg) or "0")
                 for seg in str(v).replace("-", ".").split("."))


def _http_bytes(url: str, timeout: int = 12) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "agent-guild"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _http_json(url: str, timeout: int = 12):
    return json.loads(_http_bytes(url, timeout).decode("utf-8"))


def fetch_skillhub_version() -> str:
    d = _http_json("https://api.skillhub.cn/api/v1/search?q=agent-guild")
    for x in d.get("results", []):
        ns = (x.get("namespace") or {}).get("canonicalName", "")
        if x.get("slug") == "agent-guild" or "agent-guild" in str(ns):
            v = x.get("version")
            if v:
                return str(v)
    raise LookupError("agent-guild not found on skillhub")


def fetch_github_version() -> str:
    """Get the latest release tag via the releases/latest redirect (no API,
    no rate limit)."""

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(
        "https://github.com/dqsjqian/agent-guild/releases/latest",
        headers={"User-Agent": "agent-guild"})
    try:
        opener.open(req, timeout=12)
        raise LookupError("no redirect from releases/latest")
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise
        loc = e.headers.get("Location", "")
        tag = loc.rstrip("/").rsplit("/", 1)[-1]
        if not tag or not tag.startswith("v"):
            raise LookupError(f"unexpected redirect target: {loc}")
        return tag[1:]


def fetch_clawhub_version() -> str:
    d = _http_json("https://clawhub.ai/api/v1/skills/agent-guild/versions")
    items = d.get("items", [])
    if not items or not items[0].get("version"):
        raise LookupError("no versions on clawhub")
    return str(items[0]["version"])


def _apply_skill_package(skill_src_dir: Path, proto: str, skill: str) -> None:
    """Replace the central skill package + root docs from skill_src_dir, then
    bump the VERSION anchor. User-data dirs are never touched."""
    own_skill = CENTRAL / "skills" / "agent-guild"
    _replace_tree(skill_src_dir, own_skill)
    for doc in ("ONBOARDING.md", "CONVENTIONS.md", "SPEC.md"):
        src = skill_src_dir / "docs" / doc
        if not src.is_file():
            continue
        body = src.read_text(encoding="utf-8")
        target = CENTRAL / doc
        if not target.exists() or target.read_text(encoding="utf-8") != body:
            target.write_text(body, encoding="utf-8")
    write_runtime_version(proto, skill)


def cmd_upgrade(args: list) -> int:
    """Check the three platforms for a newer version; --apply downloads and
    installs it (user data preserved)."""
    apply_ = "--apply" in args

    versions, errors = {}, []
    for name, fetcher in (("skillhub", fetch_skillhub_version),
                          ("github", fetch_github_version),
                          ("clawhub", fetch_clawhub_version)):
        try:
            versions[name] = fetcher()
        except Exception as e:  # network / parse — skip this source
            errors.append(f"{name}: {e}")

    if not versions:
        print("could not reach any version source")
        for e in errors:
            print(f"  - {e}")
        return 1

    local = read_runtime_version().get("skill_version", "0")
    latest_name, latest = max(versions.items(), key=lambda kv: _verkey(kv[1]))

    print("version check:")
    for name, v in versions.items():
        mark = "  ← latest" if name == latest_name else ""
        print(f"  {name:<9} {v}{mark}")
    print(f"  {'local':<9} {local}")
    for e in errors:
        print(f"  (unreachable: {e})")

    if not _version_gt(latest, local):
        print(f"\nalready up to date ({local}).")
        return 0

    print(f"\nupdate available: {local} → {latest} (from {latest_name})")
    if not apply_:
        print("run `ag upgrade --apply` to download and install.")
        return 0

    print("downloading ...")
    try:
        data = _http_bytes(GITHUB_RELEASE_ZIP.format(ver=latest), timeout=120)
    except Exception as e:
        print(f"download failed: {e}")
        return 1

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            stage = Path(tempfile.mkdtemp(prefix="ag-upgrade-"))
            z.extractall(stage)
        pkg = stage / "agent-guild"
        if not (pkg / "SKILL.md").is_file():
            print("apply failed: release zip has unexpected layout")
            return 1
        m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
        new_proto = m.get("protocol_version", PROTOCOL_VERSION)
        new_skill = m.get("skill_version", latest)
        _apply_skill_package(pkg, new_proto, new_skill)
    except Exception as e:
        print(f"apply failed: {e}")
        return 1

    print(f"upgraded {local} → {new_skill} (protocol {new_proto}).")
    print("user data (identity/rules/log/handoff/skills_data/connectors/memory) untouched.")
    return 0


# ------------------------------------------------------------------ adopt ---

def _user_ignores() -> list:
    """User-defined ignore patterns from ~/.agent-guild/.adoptignore."""
    p = CENTRAL / ADOPTIGNORE
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def _is_host_wired_skill(skill_dir: Path) -> bool:
    """True if this skill's capability comes from host-managed connector/MCP
    wiring, so its files are not portable on their own."""
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return False
    try:
        head = md.read_text(encoding="utf-8", errors="ignore")[:1500].lower()
    except OSError:
        return False
    return any(m in head for m in HOST_WIRED_MARKERS)


def _is_excluded(name: str, kind: str = "") -> bool:
    if name in EXCLUDE_NAMES:
        return True
    if any(s in name for s in EXCLUDE_SUBSTRINGS):
        return True
    if name.endswith(EXCLUDE_SUFFIXES):
        return True
    for pat in _user_ignores():
        if fnmatch(name, pat):
            return True
    return False


def _scan_dir(src_dir: Path, dest_root: str) -> list[dict]:
    """Adoptable children of src_dir (real dirs/files, not symlinks)."""
    found = []
    if not src_dir.is_dir():
        return found
    for child in sorted(src_dir.iterdir()):
        if child.is_symlink():
            continue  # already linked somewhere — nothing to adopt
        if _is_excluded(child.name, dest_root):
            continue
        if child.name.startswith("."):
            continue
        # A skill is a directory with a SKILL.md; loose files under skills/ are
        # host bookkeeping, not skills.
        if dest_root == "skills":
            if (child.is_dir() and (child / "SKILL.md").is_file()
                    and not _is_host_wired_skill(child)):
                found.append({"src": child, "dest": CENTRAL / dest_root / child.name, "kind": dest_root})
            continue
        if child.is_dir() or child.suffix in (".md", ".json", ".yaml", ".yml", ".toml"):
            found.append({
                "src": child,
                "dest": CENTRAL / dest_root / child.name,
                "kind": dest_root,
            })
    return found


def _scan_agent(home: Path, agent: str) -> list[dict]:
    items, seen_src, used_dest = [], set(), set()

    def add(src: Path, dest: Path, kind: str) -> None:
        key = src.resolve() if src.exists() else src
        if key in seen_src:
            return
        seen_src.add(key)
        # Two distinct sources can map to the same name (e.g. ~/.x/MEMORY.md and
        # ~/.x/memory/MEMORY.md). Disambiguate instead of silently overwriting.
        if dest in used_dest:
            try:
                rel = src.parent.relative_to(home).as_posix()
            except ValueError:
                rel = src.parent.name
            tag = rel.strip("./").replace("/", "-") or "home"
            dest = dest.with_name(f"{dest.stem}__{tag}{dest.suffix}")
        used_dest.add(dest)
        items.append({"src": src, "dest": dest, "kind": kind})

    for cls, subdirs in CANDIDATE_LAYOUT.items():
        dest_root = ADOPT_DESTS[cls]
        for sub in subdirs:
            src_dir = home / sub
            for it in _scan_dir(src_dir, dest_root):
                dest = it["dest"]
                if cls == "memory":
                    # keep each agent's memory namespaced: memory/<agent>/
                    dest = CENTRAL / dest_root / agent / it["src"].name
                add(it["src"], dest, it["kind"])

    # agent-private memory files sitting at the home root
    for fname in MEMORY_FILES:
        f = home / fname
        if f.is_file() and not f.is_symlink():
            add(f, CENTRAL / "memory" / agent / fname, "memory")
    return items


def _link_back(src: Path, dest: Path) -> Tuple[bool, str]:
    """Move src -> dest, then link src -> dest. Verify; roll back on any failure.

    The verification step matters most for memory files: some runtimes recreate
    or refuse to follow links, and a silent failure would lose user data.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(src), str(dest))
    except OSError as e:
        return False, f"move failed: {e}"

    linked, how = make_link(src, dest)
    if not linked:
        shutil.move(str(dest), str(src))  # rollback
        return False, f"{how} (rolled back)"

    # Verify the link resolves to the new location and is still readable.
    ok, why = True, ""
    try:
        if not src.exists() or src.resolve() != dest.resolve():
            ok, why = False, "link does not resolve to target"
        elif dest.is_file():
            dest.read_bytes()
    except OSError as e:
        ok, why = False, f"unreadable after link: {e}"

    if not ok:
        try:
            src.unlink()
        except OSError:
            try:
                shutil.rmtree(src)  # Windows junction
            except OSError:
                pass
        shutil.move(str(dest), str(src))  # rollback
        return False, f"verification failed: {why} (rolled back)"
    return True, how


def cmd_adopt(args: list) -> int:
    apply = "--apply" in args
    rest = [a for a in args if not a.startswith("-")]
    agent = default_agent(rest)
    home = agent_home(agent)
    if home is None:
        print(f"cannot resolve home for agent '{agent}' — "
              f"pass a registered name or set AG_AGENT", file=sys.stderr)
        return 1
    if not CENTRAL.exists():
        print(f"{CENTRAL} missing — run `ag init` first", file=sys.stderr)
        return 1

    items = _scan_agent(home, agent)
    if not items:
        print(f"nothing to adopt from {home}")
        return 0

    print(f"{'ADOPTING' if apply else 'DRY-RUN'} — agent={agent} home={home}")
    print(f"{'kind':<12} {'name':<34} action")
    print("-" * 78)

    moved = skipped = failed = 0
    for it in items:
        src, dest, kind = it["src"], it["dest"], it["kind"]
        if dest.exists() or dest.is_symlink():
            print(f"{kind:<12} {src.name:<34} skip (already in guild)")
            skipped += 1
            continue
        if not apply:
            print(f"{kind:<12} {src.name:<34} would move -> {dest.relative_to(CENTRAL)}")
            continue
        ok, msg = _link_back(src, dest)
        if ok:
            print(f"{kind:<12} {src.name:<34} moved + symlinked")
            audit("adopt", {"agent": agent, "kind": kind, "name": src.name})
            moved += 1
        else:
            print(f"{kind:<12} {src.name:<34} FAILED: {msg}")
            failed += 1

    print("-" * 78)
    if apply:
        print(f"moved={moved} skipped={skipped} failed={failed}")
    else:
        print(f"{len(items) - skipped} candidate(s). Re-run with --apply to execute.")
        print("Excluded by policy: caches (.venv/node_modules), credentials, "
              "platform-managed packages (__skillhub/connector-*).")
    return 0 if failed == 0 else 1


# -------------------------------------------------------------- bootstrap ---

BOOTSTRAP_FILES = [
    ("identity/profile.md", "WHO THE USER IS"),
    ("identity/ROUTINE.md", "ROUTINE"),
    ("rules/universal.md", "UNIVERSAL RULES (highest priority)"),
    ("projects/active.md", "ACTIVE PROJECTS"),
    ("handoff/shared-state/current-focus.md", "CURRENT FOCUS"),
]


def cmd_bootstrap(args: list) -> int:
    """Dump all shared session context in one shot (read-only)."""
    if not CENTRAL.exists():
        print(f"{CENTRAL} missing — run `ag init` first", file=sys.stderr)
        return 1
    agent = default_agent(args)
    shown = 0
    for rel, title in BOOTSTRAP_FILES:
        p = CENTRAL / rel
        print(f"\n{'=' * 78}\n== {title}  ({rel})\n{'=' * 78}")
        if p.exists():
            print(p.read_text(encoding="utf-8").rstrip())
            shown += 1
        else:
            print(f"[missing: {rel}]")

    # Unread inbox for this agent
    if INBOX.is_dir():
        mine = [f.name for f in sorted(INBOX.iterdir())
                if f.is_file() and f"-to-{agent}-" in f.name]
        print(f"\n{'=' * 78}\n== INBOX for {agent}\n{'=' * 78}")
        print("\n".join(f"  {m}" for m in mine) if mine else "  (empty)")

    # Other rules files, listed not dumped (read on demand)
    extra = sorted(p.name for p in (CENTRAL / "rules").glob("*.md")
                   if p.name != "universal.md") if (CENTRAL / "rules").is_dir() else []
    if extra:
        print(f"\nOther rules (read on demand): {', '.join(extra)}")

    # Learning-ledger pending summary (protocol 3.1+)
    led = []
    for path in _ledger_files():
        if not path.exists():
            continue
        entries = _parse_entries(path.read_text(encoding="utf-8"))
        n_open = sum(1 for e in entries
                     if _field(e, "Status") in ("", "pending", "in_progress"))
        if n_open:
            top = next((e for e in entries
                        if _field(e, "Status") in ("", "pending", "in_progress")
                        and _field(e, "Priority") in ("high", "critical")), None)
            hint = f" — top: {top['id']} {_summary_of(top)}" if top else ""
            led.append(f"{path.stem} {n_open} open{hint}")
    if led:
        print(f"\nLearning ledger (learnings/): {' | '.join(led)}")
        print("  fix what you touch (ag resolve), promote what recurs (ag review).")

    print(f"\n{shown}/{len(BOOTSTRAP_FILES)} context files loaded.")
    return 0


# ----------------------------------------------------------------- doctor ---

def cmd_doctor(args: list) -> int:
    """Health check: broken links, missing files, registry / version drift."""
    if not CENTRAL.exists():
        print(f"{CENTRAL} missing — run `ag init` first", file=sys.stderr)
        return 1

    problems = 0
    print("== broken links in the guild ==")
    dangling = []
    for root, dirs, files in os.walk(CENTRAL, followlinks=False):
        for name in list(dirs) + files:
            p = Path(root) / name
            if p.is_symlink() and not p.exists():
                dangling.append(p)
    if dangling:
        for p in dangling:
            print(f"  ✗ {p} -> {os.readlink(p)}")
        problems += len(dangling)
    else:
        print("  ok — none")

    print("\n== broken links in registered agent homes ==")
    reg = load_registry()
    agent_dangling = []
    for name, entry in reg.get("agents", {}).items():
        sr = entry.get("skills_root")
        if not sr or sr == "platform-managed":
            continue
        d = Path(sr).expanduser()
        if not d.is_dir():
            continue
        try:
            children = list(d.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink() and not child.exists():
                agent_dangling.append((name, child))
    if agent_dangling:
        for name, p in agent_dangling:
            print(f"  ✗ [{name}] {p} -> {os.readlink(p)}")
        problems += len(agent_dangling)
    else:
        print("  ok — none")

    print("\n== core protocol files ==")
    required = [
        "registry.json", "ONBOARDING.md",
        "skills/agent-guild/SKILL.md", "skills/agent-guild/manifest.json",
        "identity/profile.md", "rules/universal.md",
    ]
    missing = [r for r in required if not (CENTRAL / r).is_file()]
    if missing:
        for r in missing:
            print(f"  ✗ missing: {r}")
        problems += len(missing)
    else:
        print("  ok — all present")

    bad_json = []
    for rel in ("registry.json", "skills/agent-guild/manifest.json"):
        p = CENTRAL / rel
        if p.is_file():
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                bad_json.append((rel, str(e)))
    if bad_json:
        for rel, e in bad_json:
            print(f"  ✗ unparseable JSON: {rel} ({e})")
        problems += len(bad_json)

    print("\n== registry drift ==")
    drift = 0
    for name, entry in reg.get("agents", {}).items():
        home = entry.get("home", "")
        if home and not Path(home).expanduser().exists():
            print(f"  ✗ [{name}] home does not exist: {home}")
            drift += 1
        sr = entry.get("skills_root")
        if sr and sr != "platform-managed" and not Path(sr).expanduser().exists():
            print(f"  ✗ [{name}] skills_root does not exist: {sr}")
            drift += 1
    if not drift:
        print("  ok — none")
    problems += drift

    print(f"\n== protocol version drift (central={PROTOCOL_VERSION}) ==")
    stale_proto = []
    central_major = PROTOCOL_VERSION.split(".")[0]
    for name, entry in reg.get("agents", {}).items():
        pv = str(entry.get("protocol_version", "0"))
        if pv.split(".")[0] != central_major:
            stale_proto.append((name, pv))
    if stale_proto:
        for name, pv in stale_proto:
            print(f"  ✗ [{name}] joined under {pv} — MAJOR bump, must re-run ONBOARDING.md")
        problems += len(stale_proto)
    else:
        print("  ok — all agents on the current major version")

    print(f"\n{'=' * 60}")
    if problems:
        print(f"{problems} problem(s) found. Suggested fixes:")
        print("  broken links      → delete the link (never the target)")
        print("  missing files     → `ag init` refills gaps without touching data")
        print("  registry drift    → `ag register <agent> <home> <tier> <skills_root>`")
        print("  version drift     → re-run ONBOARDING.md, then re-register")
        return 1
    print("All checks passed.")
    return 0


# ------------------------------------------------------- existing commands ---

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
        print("usage: ag register <agent> <home> <tier> [skills_root] [capabilities...]", file=sys.stderr)
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
        protocol_version=PROTOCOL_VERSION,
        install_tier=tier,
        skills_root=skills_root,
        capabilities=caps,
    )
    data["agents"][name] = entry
    save_registry(data, name, "register")
    print(f"registered {name} (tier={tier}, protocol={PROTOCOL_VERSION})")
    return 0


def cmd_last_seen(args: list) -> int:
    if len(args) < 1:
        print("usage: ag last-seen <agent>", file=sys.stderr)
        return 2
    name = args[0]
    data = load_registry()
    agents = data.setdefault("agents", {})
    if name not in agents:
        print(f"agent '{name}' not registered — run: ag register {name} <home> <tier>", file=sys.stderr)
        return 1
    agents[name]["last_seen"] = now_iso()
    save_registry(data, name, "last_seen")
    print(f"{name} last_seen updated")
    return 0


def cmd_send(args: list) -> int:
    if len(args) < 2:
        print("usage: ag send <dst> <topic>  (message body from stdin)", file=sys.stderr)
        return 2
    dst, topic = args[0], args[1]
    body = read_stdin()
    if not body:
        print("empty message body", file=sys.stderr)
        return 2
    src = os.environ.get("AG_AGENT") or "unknown"
    safe_topic = re.sub(r"[^A-Za-z0-9._-]", "-", topic)
    fname = f"from-{src}-to-{dst}-{safe_topic}.md"
    atomic_append(INBOX / fname, body)
    audit("send", {"from": src, "to": dst, "file": f"handoff/inbox/{fname}"})
    print(f"sent to {dst}: {fname}")
    return 0


def cmd_log(args: list) -> int:
    if len(args) < 2:
        print("usage: ag log <agent> <title>  (body from stdin)", file=sys.stderr)
        return 2
    agent, title = args[0], args[1]
    body = read_stdin()
    if not body:
        print("empty log body", file=sys.stderr)
        return 2
    day = datetime.now().strftime("%Y-%m-%d")
    path = DAILY / f"{day}-{agent}.md"
    atomic_append(path, f"\n## {title}\n\n{body}")
    print(f"appended to log/daily/{day}-{agent}.md")
    return 0


def cmd_focus(args: list) -> int:
    if len(args) < 2:
        print("usage: ag focus <agent> <title>  (body from stdin)", file=sys.stderr)
        return 2
    agent, title = args[0], args[1]
    body = read_stdin()
    block = f"> Last updated: {now_iso()} by {agent}\n\n## {title}\n\n{body}\n\n---\n"
    existing = FOCUS.read_text(encoding="utf-8") if FOCUS.exists() else ""
    existing = re.sub(r"^#\s*Current Focus\s*\n+", "", existing.lstrip())
    new = "# Current Focus\n\n" + block + existing
    FOCUS.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(FOCUS.parent), prefix=".ag-", suffix=".tmp")
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


# --------------------------------------------------------------- learnings ---

# Entry header pattern: "## [LRN-20260818-003] category"
_ENTRY_RE = re.compile(r"^## \[((?:LRN|ERR|FEAT)-\d{8}-[A-Za-z0-9]{3})\]\s*(.*)$", re.M)


def _ledger_files() -> list:
    return [CENTRAL / rel for rel, _ in LEDGERS.values()]


def _parse_entries(text: str) -> list:
    """Split a ledger file into structured entries (id, category, block)."""
    out = []
    matches = list(_ENTRY_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end]
        out.append({"id": m.group(1), "category": m.group(2).strip(), "block": block})
    return out


def _field(entry: dict, name: str) -> str:
    m = re.search(rf"^\*\*{re.escape(name)}\*\*:\s*(.+)$", entry["block"], re.M)
    return m.group(1).strip() if m else ""


def _summary_of(entry: dict) -> str:
    m = re.search(r"^### Summary\s*\n+\s*(.+)$", entry["block"], re.M)
    return m.group(1).strip() if m else "(no summary)"


def _next_id(path: Path, prefix: str) -> str:
    day = datetime.now().strftime("%Y%m%d")
    used = set()
    if path.exists():
        for e in _parse_entries(path.read_text(encoding="utf-8")):
            if e["id"].startswith(f"{prefix}-{day}-"):
                used.add(e["id"].rsplit("-", 1)[-1])
    n = 1
    while f"{n:03d}" in used:
        n += 1
    return f"{prefix}-{day}-{n:03d}"


def _opt(args: list, name: str, default: str = "") -> str:
    """Extract --name VALUE from args (and remove both from the list)."""
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            val = args[i + 1]
            del args[i:i + 2]
            return val
        args.remove(name)
    return default


def cmd_learn(args: list) -> int:
    """Append a structured entry to a learning ledger (details from stdin)."""
    area = _opt(args, "--area", "")
    priority = _opt(args, "--priority", "medium")
    category = _opt(args, "--category", "")
    pattern_key = _opt(args, "--pattern-key", "")
    rest = [a for a in args if not a.startswith("-")]
    if len(rest) < 3:
        print('usage: ag learn <agent> <learning|error|featreq> "<summary>" '
              "[--area A] [--priority low|medium|high|critical] "
              "[--category C] [--pattern-key K]  (details from stdin)",
              file=sys.stderr)
        return 2
    agent, kind, summary = rest[0], rest[1].lower(), rest[2]
    kind = LEDGER_ALIASES.get(kind, kind)
    if kind not in LEDGERS:
        print(f"unknown kind '{kind}' — use learning | error | featreq", file=sys.stderr)
        return 2
    if not CENTRAL.exists():
        print(f"{CENTRAL} missing — run `ag init` first", file=sys.stderr)
        return 1

    rel, prefix = LEDGERS[kind]
    path = CENTRAL / rel
    if not path.exists():  # older central dir — back-fill header
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(PLACEHOLDERS.get(rel, "# ledger\n\n---\n"), encoding="utf-8")

    # Recurrence detection: same Pattern-Key logged before?
    see_also = ""
    if pattern_key and path.exists():
        prior = [e["id"] for e in _parse_entries(path.read_text(encoding="utf-8"))
                 if re.search(rf"Pattern-Key:\s*{re.escape(pattern_key)}\s*$",
                              e["block"], re.M)]
        if prior:
            see_also = ", ".join(prior)
            print(f"recurrence: Pattern-Key '{pattern_key}' seen in {see_also} "
                  f"— linking via See Also; promotion threshold may now be met (ag review).")

    entry_id = _next_id(path, prefix)
    body = read_stdin() or "(no details provided)"

    if kind == "error":
        detail = f"### Error\n```\n{body}\n```"
    elif kind == "featreq":
        detail = f"### Requested Capability\n{summary}\n\n### User Context\n{body}"
    else:
        detail = f"### Details\n{body}"
        if not category:
            category = "insight"

    meta = [f"- Source: conversation",
            f"- Related Files: ",
            f"- Tags: "]
    if see_also:
        meta.append(f"- See Also: {see_also}")
    if pattern_key:
        meta.append(f"- Pattern-Key: {pattern_key}")

    if kind == "learning":
        heading_cat = category or "insight"
    elif kind == "error":
        heading_cat = category or "error"
    else:
        heading_cat = category or "request"
    entry = (
        f"\n## [{entry_id}] {heading_cat}\n\n"
        f"**Logged**: {now_iso()}\n"
        f"**By**: {agent}\n"
        f"**Priority**: {priority}\n"
        f"**Status**: pending\n"
        f"**Area**: {area or 'unspecified'}\n\n"
        f"### Summary\n{summary}\n\n"
        f"{detail}\n\n"
        f"### Suggested Action\n(none yet)\n\n"
        f"### Metadata\n" + "\n".join(meta) + "\n\n---\n"
    )
    atomic_append(path, entry)
    audit("learn", {"agent": agent, "id": entry_id, "kind": kind,
                    "pattern_key": pattern_key or None})
    print(f"logged {entry_id} -> {rel} (by {agent}, priority={priority})")
    print("next: fix it later with `ag resolve " + entry_id + "`, "
          "or distill recurring ones via `ag review`.")
    return 0


def cmd_resolve(args: list) -> int:
    """Set an entry's Status to resolved + append a Resolution block."""
    if not args:
        print("usage: ag resolve <ENTRY-ID> [note ...]", file=sys.stderr)
        return 2
    entry_id = args[0].strip("[]")
    note = " ".join(args[1:]).strip() or "resolved"
    agent = os.environ.get("AG_AGENT") or "unknown"

    for path in _ledger_files():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        entries = _parse_entries(text)
        for e in entries:
            if e["id"] != entry_id:
                continue
            block = e["block"]
            if "**Status**: resolved" in block:
                print(f"{entry_id} is already resolved")
                return 0
            new_block, n = re.subn(r"^\*\*Status\*\*:\s*\S+",
                                   "**Status**: resolved", block, count=1, flags=re.M)
            if n == 0:
                new_block = block.replace("### Summary",
                                          "**Status**: resolved\n\n### Summary", 1)
            new_block = new_block.rstrip("\n") + (
                f"\n\n### Resolution\n- **Resolved**: {now_iso()}\n"
                f"- **By**: {agent}\n- **Notes**: {note}\n\n---\n")
            new_text = text.replace(block, new_block, 1)
            fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ag-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(new_text)
            os.replace(tmp, path)
            audit("resolve", {"agent": agent, "id": entry_id})
            print(f"resolved {entry_id} in {path.relative_to(CENTRAL)}")
            return 0
    print(f"entry '{entry_id}' not found in any ledger "
          f"(searched learnings/*.md)", file=sys.stderr)
    return 1


def cmd_review(args: list) -> int:
    """Ledger overview: pending stats, high-priority items, promotion candidates."""
    any_file = False
    for path in _ledger_files():
        if not path.exists():
            continue
        any_file = True
        entries = _parse_entries(path.read_text(encoding="utf-8"))
        if not entries:
            continue
        open_items = [e for e in entries
                      if _field(e, "Status") in ("", "pending", "in_progress")]
        print(f"== {path.relative_to(CENTRAL)} — {len(entries)} entries, "
              f"{len(open_items)} open ==")
        hot = [e for e in open_items if _field(e, "Priority") in ("high", "critical")]
        for e in hot:
            print(f"  [{_field(e, 'Priority'):<8}] {e['id']}  {_summary_of(e)}"
                  f"  (by {_field(e, 'By') or '?'})")
        if not hot and open_items:
            print(f"  ({len(open_items)} open, none high/critical)")
        if not open_items:
            print("  (all resolved/promoted)")

        # Pattern-Key recurrence groups -> promotion candidates
        groups = {}
        for e in entries:
            m = re.search(r"^- Pattern-Key:\s*(\S+)\s*$", e["block"], re.M)
            if m:
                groups.setdefault(m.group(1), []).append(e)
        for key, es in sorted(groups.items()):
            hits, agents = len(es), {_field(e, "By") for e in es}
            if hits >= 3 or (hits >= 2 and len(agents) >= 2):
                print(f"  PROMOTION CANDIDATE: Pattern-Key '{key}' — "
                      f"{hits} hits by {len(agents)} agents "
                      f"({', '.join(sorted(a or '?' for a in agents))})")
                print(f"    -> distill into rules/ / toolchain/ / memory/shared/, "
                      f"or extract a skill onto skills/ (docs/LEARNINGS.md)")
        print()

    if not any_file:
        print("no ledgers found — run `ag init` to create learnings/")
        return 1
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
            print(f"{e.get('ts','?')}  {e.get('action','?'):<10} "
                  f"{e.get('agent',''):<12} {e.get('file', e.get('name', e.get('title','')))}")
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
        "init": cmd_init,
        "find-root": cmd_find_root,
        "adopt": cmd_adopt,
        "bootstrap": cmd_bootstrap,
        "doctor": cmd_doctor,
        "upgrade": cmd_upgrade,
        "status": cmd_status,
        "register": cmd_register,
        "last-seen": cmd_last_seen,
        "send": cmd_send,
        "log": cmd_log,
        "focus": cmd_focus,
        "learn": cmd_learn,
        "review": cmd_review,
        "resolve": cmd_resolve,
        "audit": cmd_audit,
        "prune": cmd_prune,
    }
    fn = table.get(cmd)
    if fn is None:
        print(f"unknown command: {cmd}\n\n{__doc__}", file=sys.stderr)
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
