#!/usr/bin/env bash
# Package agent-guild as a marketplace-ready skill zip.
#
# ONE layout only (since v3.10.0): the registry-sanctioned shape
# (references/ + scripts/, LICENSE.md, max 3 path segments). Every channel —
# GitHub releases, `ag upgrade`, ClawHub, SkillHub, local installs — ships
# and consumes this same package. adapters/ and references/examples/ stay in
# the repository only: they would add a fourth path segment, which some
# registries reject; browse them on GitHub instead.
#
# Usage:
#   bash scripts/package.sh                   # → ~/Downloads/agent-guild-vX.Y.Z.zip
#   bash scripts/package.sh /path/out.zip     # custom output path

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -E '"skill_version"' "$ROOT/manifest.json" | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
[ -n "$VERSION" ] || { echo "cannot read skill_version from manifest.json" >&2; exit 1; }

OUT="${1:-$HOME/Downloads/agent-guild-v${VERSION}.zip}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

PKG="$STAGE/agent-guild"
mkdir -p "$PKG/scripts" "$PKG/references"

cp "$ROOT/SKILL.md"      "$PKG/SKILL.md"
cp "$ROOT/manifest.json" "$PKG/manifest.json"

# Scripts: everything in scripts/ except the packager itself. Wildcarded on
# purpose — adding scripts/<new-tool> needs no edit here.
for f in "$ROOT"/scripts/*; do
  [ "$(basename "$f")" = "package.sh" ] && continue
  cp "$f" "$PKG/scripts/"
done

# Reference docs, shipped flat under references/ (path depth stays <= 3).
# Wildcarded on purpose — adding references/<NEW>.md needs no edit here.
# adapters/ and references/examples/ stay repo-only: they would add a fourth
# path segment, which some registries reject; browse them on GitHub instead.
for f in "$ROOT"/references/*.md; do
  cp "$f" "$PKG/references/"
done

# Some registries reject extensionless files; the license travels as .md.
cp "$ROOT/LICENSE" "$PKG/LICENSE.md"

chmod +x "$PKG/scripts/ag.py" "$PKG/scripts/install.sh" 2>/dev/null || true

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$STAGE" && zip -r -X "$OUT" agent-guild -x "*.DS_Store" -x "*__pycache__*" >/dev/null)

echo "✔ packaged: $OUT   ($(du -h "$OUT" | cut -f1), layout: references/)"

# ----------------------------------------------------------------- checks ---

fail=0
check() { # check <label> <condition-result>
  if [ "$2" = "0" ]; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi
}

TOPDIRS="$(cd "$STAGE" && find . -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')"
check "single top-level directory (agent-guild/)" "$([ "$TOPDIRS" = "1" ] && echo 0 || echo 1)"
check "SKILL.md at package root" "$([ -f "$PKG/SKILL.md" ] && echo 0 || echo 1)"

DEEP="$(cd "$STAGE" && find . -type f | sed 's|^\./||' | awk -F/ 'NF>3' | head -5)"
check "path depth <= 3 segments" "$([ -z "$DEEP" ] && echo 0 || echo 1)"
[ -n "$DEEP" ] && echo "$DEEP" | sed 's/^/       too deep: /'

NOEXT="$(cd "$PKG" && find . -type f ! -name "*.*" | head -5)"
check "no extensionless files" "$([ -z "$NOEXT" ] && echo 0 || echo 1)"
[ -n "$NOEXT" ] && echo "$NOEXT" | sed 's/^/       extensionless: /'

# Every references/*.md quoted in SKILL.md must exist inside the package —
# a dangling link here is exactly the v3.9.1 bug class this check kills.
python3 - "$PKG" <<'PY'
import re, sys, pathlib
pkg = pathlib.Path(sys.argv[1])
body = (pkg / "SKILL.md").read_text(encoding="utf-8")
missing = sorted({m for m in re.findall(r"references/([\w.-]+\.md)", body)
                  if not (pkg / "references" / m).is_file()})
if missing:
    print(f"  FAIL dangling doc links: {', '.join(missing)}")
sys.exit(1 if missing else 0)
PY
check "SKILL.md doc links resolve" "$?"

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
