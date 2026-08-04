#!/usr/bin/env bash
# Package agent-commons as a marketplace-ready skill zip.
#
# The zip contains a self-contained skill package (SKILL.md + manifest +
# scripts + onboarding docs). Data never ships — the skill reads/writes the
# user's ~/.agent-commons/ at runtime (capability/data separation).
#
# Usage:
#   bash scripts/package.sh                # → dist/agent-commons-skill-vX.Y.Z.zip
#   bash scripts/package.sh /path/out.zip  # custom output path

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -E '"skill_version"' "$ROOT/skills/agent-commons/manifest.json" | head -1 | grep -oE '[0-9.]+')"
[ -n "$VERSION" ] || VERSION="3.0"

OUT="${1:-$ROOT/dist/agent-commons-skill-v${VERSION}.zip}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

PKG="$STAGE/agent-commons"
mkdir -p "$PKG/scripts"

cp "$ROOT/skills/agent-commons/SKILL.md"     "$PKG/SKILL.md"
cp "$ROOT/skills/agent-commons/manifest.json" "$PKG/manifest.json"
cp "$ROOT/ONBOARDING.md"                     "$PKG/ONBOARDING.md"
cp "$ROOT/CONVENTIONS.md"                    "$PKG/CONVENTIONS.md"
cp "$ROOT/LICENSE"                           "$PKG/LICENSE"
cp "$ROOT/README.md"                         "$PKG/README.md"
cp "$ROOT/scripts/ac.py"                     "$PKG/scripts/ac.py"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$STAGE" && zip -r -X "$OUT" agent-commons >/dev/null)

echo "✔ packaged: $OUT"
echo "  contents:"
(cd "$STAGE" && unzip -l "$OUT" | sed -n '5,20p' | head -16)
