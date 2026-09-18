#!/usr/bin/env bash
# Package agent-guild as a marketplace-ready skill zip.
#
# The zip contains a self-contained skill package (SKILL.md + manifest +
# scripts + protocol docs). Data never ships — the skill reads/writes the
# user's ~/.agent-guild/ at runtime (capability/data separation).
#
# Two layouts, same content:
#
#   default   docs/ + full docs tree (adapters/, examples/) + LICENSE
#             → GitHub releases, `ag upgrade`
#   MARKET=1  references/ + scripts/ only, LICENSE.md, max 3 path segments
#             → skill registries that sanction references/ scripts/ templates/
#               and reject deep paths or extensionless files
#
# Usage:
#   bash scripts/package.sh                   # → ~/Downloads/agent-guild-skill-vX.Y.Z.zip
#   bash scripts/package.sh /path/out.zip     # custom output path
#   MARKET=1 bash scripts/package.sh          # → ~/Downloads/agent-guild-skill-market-vX.Y.Z.zip
#   REGISTRY_SAFE=1 bash scripts/package.sh   # keep docs/ layout, ship LICENSE.md
#
# MARKET=1 self-checks the result and fails loudly instead of handing over a
# package a registry would reject.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -E '"skill_version"' "$ROOT/manifest.json" | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
[ -n "$VERSION" ] || { echo "cannot read skill_version from manifest.json" >&2; exit 1; }

if [ -n "${MARKET:-}" ]; then
  DEFAULT_OUT="$HOME/Downloads/agent-guild-skill-market-v${VERSION}.zip"
  DOCDIR="references"
else
  DEFAULT_OUT="$HOME/Downloads/agent-guild-skill-v${VERSION}.zip"
  DOCDIR="docs"
fi
OUT="${1:-$DEFAULT_OUT}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

PKG="$STAGE/agent-guild"
mkdir -p "$PKG/scripts" "$PKG/$DOCDIR"

cp "$ROOT/SKILL.md"      "$PKG/SKILL.md"
cp "$ROOT/manifest.json" "$PKG/manifest.json"
cp "$ROOT/scripts/ag.py" "$PKG/scripts/ag.py"
cp "$ROOT/scripts/test_junction.py" "$PKG/scripts/test_junction.py"
cp "$ROOT/scripts/install.sh"  "$PKG/scripts/install.sh"
cp "$ROOT/scripts/install.ps1" "$PKG/scripts/install.ps1"

# Protocol docs. `ag init` seeds the root docs from either layout, so the
# market package stays fully functional after install.
for d in ONBOARDING CONVENTIONS SPEC LEARNINGS PORTABILITY SECURITY README README_EN; do
  cp "$ROOT/docs/$d.md" "$PKG/$DOCDIR/$d.md"
done

# The adapters/ and examples/ trees would add a fourth path segment, which
# some registries reject. They ship in the default layout only; the market
# package points at the repository for them instead.
if [ -z "${MARKET:-}" ]; then
  cp -R "$ROOT/docs/adapters" "$PKG/docs/"
  cp -R "$ROOT/docs/examples" "$PKG/docs/"
fi

chmod +x "$PKG/scripts/ag.py" "$PKG/scripts/install.sh" 2>/dev/null || true

# In the market layout the docs live in references/, so the paths quoted in
# SKILL.md have to follow. Only the shipped doc names are rewritten.
if [ -n "${MARKET:-}" ]; then
  python3 - "$PKG/SKILL.md" <<'PY'
import re, sys
p = sys.argv[1]
names = "ONBOARDING|CONVENTIONS|SPEC|LEARNINGS|PORTABILITY|SECURITY|README_EN|README"
body = open(p, encoding="utf-8").read()
body, n = re.subn(rf"(?<![\w/])docs/({names})\.md", r"references/\1.md", body)
open(p, "w", encoding="utf-8").write(body)
print(f"  ok   rewrote {n} doc path(s) in SKILL.md -> references/")
PY
fi

# Some registries reject extensionless files. Ship the license as LICENSE.md
# there so the terms still travel with the package.
if [ -n "${MARKET:-}" ] || [ -n "${REGISTRY_SAFE:-}" ]; then
  cp "$ROOT/LICENSE" "$PKG/LICENSE.md"
else
  cp "$ROOT/LICENSE" "$PKG/LICENSE"
fi

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$STAGE" && zip -r -X "$OUT" agent-guild -x "*.DS_Store" -x "*__pycache__*" >/dev/null)

echo "✔ packaged: $OUT   ($(du -h "$OUT" | cut -f1), layout: $DOCDIR/)"

# ----------------------------------------------------------------- checks ---

fail=0
check() { # check <label> <condition-result>
  if [ "$2" = "0" ]; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi
}

TOPDIRS="$(cd "$STAGE" && find . -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')"
check "single top-level directory (agent-guild/)" "$([ "$TOPDIRS" = "1" ] && echo 0 || echo 1)"
check "SKILL.md at package root" "$([ -f "$PKG/SKILL.md" ] && echo 0 || echo 1)"

DEEP="$(cd "$STAGE" && find . -type f | sed 's|^\./||' | awk -F/ 'NF>3' | head -5)"
NOEXT="$(cd "$PKG" && find . -type f ! -name "*.*" | head -5)"
if [ -n "${MARKET:-}" ]; then
  # Registry constraints — only the market layout promises to satisfy them.
  # The default layout deliberately ships docs/adapters/ and docs/examples/,
  # which are one segment deeper.
  check "path depth <= 3 segments" "$([ -z "$DEEP" ] && echo 0 || echo 1)"
  [ -n "$DEEP" ] && echo "$DEEP" | sed 's/^/       too deep: /'
  check "no extensionless files" "$([ -z "$NOEXT" ] && echo 0 || echo 1)"
  [ -n "$NOEXT" ] && echo "$NOEXT" | sed 's/^/       extensionless: /'
fi

JUNK="$(cd "$STAGE" && find . \( -name ".DS_Store" -o -name "__pycache__" -o -name "*.pyc" -o -name ".venv" \) | head -5)"
check "no OS noise / caches" "$([ -z "$JUNK" ] && echo 0 || echo 1)"

SIZE_KB="$(du -k "$OUT" | cut -f1)"
check "size under 3MB (${SIZE_KB}KB)" "$([ "$SIZE_KB" -lt 3072 ] && echo 0 || echo 1)"

# Required frontmatter for skill registries, plus the SemVer shape.
python3 - "$PKG/SKILL.md" "$VERSION" <<'PY'
import re, sys
path, version = sys.argv[1], sys.argv[2]
fm = open(path, encoding="utf-8").read().split("---", 2)[1]
required = ["name", "description", "description_zh", "description_en",
            "version", "author", "display_name", "display_name_en", "slug"]
missing = [k for k in required if not re.search(rf"^{k}:", fm, re.M)]
print("  ok   frontmatter: all required fields present" if not missing
      else f"  FAIL frontmatter missing: {', '.join(missing)}")

v = re.search(r'^version:\s*"?([^"\s]+)"?', fm, re.M)
v = v.group(1) if v else ""
ok = bool(re.fullmatch(r"\d+\.\d+\.\d+", v)) and v == version
print(f"  ok   version {v} is SemVer and matches manifest" if ok
      else f"  FAIL version '{v}' must be x.y.z and match manifest ({version})")

name = re.search(r"^name:\s*(\S+)", fm, re.M)
name = name.group(1) if name else ""
print(f"  ok   name '{name}' is kebab-case" if re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name)
      else f"  FAIL name '{name}' must be kebab-case")

d = re.search(r"^description:\s*\|\n(.*?)(?=^\w+:)", fm, re.S | re.M)
n = len(d.group(1)) if d else len(re.search(r"^description:\s*(.+)$", fm, re.M).group(1))
print(f"  ok   description {n} chars (limit 1024)" if n <= 1024
      else f"  FAIL description {n} chars exceeds the 1024 limit")
PY

echo
echo "  contents:"
(cd "$STAGE" && find . -type f | sed 's|^\./|    |' | sort)

[ "$fail" = "0" ] || { echo; echo "✖ package has issues — fix them before uploading" >&2; exit 1; }
