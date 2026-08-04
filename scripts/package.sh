#!/usr/bin/env bash
# Package agent-guild as a marketplace-ready skill zip.
#
# The zip contains a self-contained skill package (SKILL.md + manifest +
# scripts + onboarding docs). Data never ships — the skill reads/writes the
# user's ~/.agent-guild/ at runtime (capability/data separation).
#
# Usage:
#   bash scripts/package.sh                # → dist/agent-guild-skill-vX.Y.Z.zip
#   bash scripts/package.sh /path/out.zip  # custom output path

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -E '"skill_version"' "$ROOT/manifest.json" | head -1 | grep -oE '[0-9.]+')"
[ -n "$VERSION" ] || VERSION="3.0"

OUT="${1:-$HOME/Downloads/agent-guild-skill-v${VERSION}.zip}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

PKG="$STAGE/agent-guild"
mkdir -p "$PKG/scripts" "$PKG/docs"

cp "$ROOT/SKILL.md"      "$PKG/SKILL.md"
cp "$ROOT/manifest.json" "$PKG/manifest.json"
cp "$ROOT/LICENSE"       "$PKG/LICENSE"
cp "$ROOT/scripts/ac.py" "$PKG/scripts/ac.py"
cp "$ROOT/docs/ONBOARDING.md"  "$PKG/docs/ONBOARDING.md"
cp "$ROOT/docs/CONVENTIONS.md" "$PKG/docs/CONVENTIONS.md"
cp "$ROOT/docs/README.md"      "$PKG/docs/README.md"

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$STAGE" && zip -r -X "$OUT" agent-guild >/dev/null)

echo "✔ packaged: $OUT"
echo "  contents:"
(cd "$STAGE" && unzip -l "$OUT" | sed -n '5,20p' | head -16)
