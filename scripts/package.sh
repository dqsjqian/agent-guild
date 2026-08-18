#!/usr/bin/env bash
# Package agent-guild as a marketplace-ready skill zip.
#
# The zip contains a self-contained skill package (SKILL.md + manifest +
# scripts + onboarding docs). Data never ships — the skill reads/writes the
# user's ~/.agent-guild/ at runtime (capability/data separation).
#
# Usage:
#   bash scripts/package.sh                # → ~/Downloads/agent-guild-skill-vX.Y.Z.zip
#   bash scripts/package.sh /path/out.zip  # custom output path
#   REGISTRY_SAFE=1 bash scripts/package.sh  # omit extensionless files (LICENSE)
#                                            # for registries that reject them

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(grep -E '"skill_version"' "$ROOT/manifest.json" | head -1 | grep -oE '[0-9.]+')"
[ -n "$VERSION" ] || VERSION="3.1"

OUT="${1:-$HOME/Downloads/agent-guild-skill-v${VERSION}.zip}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

PKG="$STAGE/agent-guild"
mkdir -p "$PKG/scripts" "$PKG/docs"

cp "$ROOT/SKILL.md"      "$PKG/SKILL.md"
cp "$ROOT/manifest.json" "$PKG/manifest.json"
cp "$ROOT/scripts/ag.py" "$PKG/scripts/ag.py"
cp "$ROOT/scripts/install.sh"  "$PKG/scripts/install.sh"
cp "$ROOT/scripts/install.ps1" "$PKG/scripts/install.ps1"
cp "$ROOT/docs/ONBOARDING.md"  "$PKG/docs/ONBOARDING.md"
cp "$ROOT/docs/CONVENTIONS.md" "$PKG/docs/CONVENTIONS.md"
cp "$ROOT/docs/SPEC.md"        "$PKG/docs/SPEC.md"
cp "$ROOT/docs/LEARNINGS.md"   "$PKG/docs/LEARNINGS.md"
cp "$ROOT/docs/README.md"      "$PKG/docs/README.md"
cp "$ROOT/docs/README_CN.md"   "$PKG/docs/README_CN.md"
cp -R "$ROOT/docs/adapters"    "$PKG/docs/"
cp -R "$ROOT/docs/examples"    "$PKG/docs/"
chmod +x "$PKG/scripts/ag.py" "$PKG/scripts/install.sh" 2>/dev/null || true

# Some skill registries reject extensionless files. Ship the license as
# LICENSE.md there so the terms still travel with the package.
if [ -n "${REGISTRY_SAFE:-}" ]; then
  cp "$ROOT/LICENSE" "$PKG/LICENSE.md"
else
  cp "$ROOT/LICENSE" "$PKG/LICENSE"
fi

mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
(cd "$STAGE" && zip -r -X "$OUT" agent-guild >/dev/null)

echo "✔ packaged: $OUT"
echo "  contents:"
(cd "$STAGE" && unzip -l "$OUT" | sed -n '5,20p' | head -16)
