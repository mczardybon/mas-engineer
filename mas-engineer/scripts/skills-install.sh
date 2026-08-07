#!/usr/bin/env bash
# skills-install.sh — R110-133 self-contained mas-engineer skills installer
#
# Bundled skills: mas-state/skills/ (in the repo) -> <TARGET> (user-supplied)
#
# Why no hardcoded runtime path:
#   mas-engineer is a generic agent-project. It does not know — and refuses to
#   know — which agent runtime consumes its skills. The runtime's skills
#   directory is the runtime's concern, not ours. This script is a copy-utility:
#   give it a target path and it copies the repo's mas-state/skills/ there.
#
# Contract (enforced by tests/test_skills_install.py):
#   - Idempotent: re-running with the same target overwrites mas-engineer-owned
#     skills with current repo state.
#   - No-delete: skills in the target that are NOT in the repo are preserved.
#   - No-env-var: the target path comes from a CLI argument, never from an
#     environment variable. No $X, no $HERMES_HOME, no $HOME tricks.
#
# Usage:
#   bash scripts/skills-install.sh                          # target = ./mas-state/skills (no-op install)
#   bash scripts/skills-install.sh /path/to/target/skills    # copy to <target>
#
# Exit codes:
#   0 — all good
#   1 — fatal: source dir not readable, target dir not creatable, bad args
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Skills liegen seit 2026-08-07 unter mas-state/skills (umbenannt aus mas-engineer/)
SKILLS_SRC="$ROOT/mas-state/skills"

# Target = CLI arg if given, else repo-relative mas-state/skills/ (no-op).
# When target == SKILLS_SRC, the install is a no-op: skills are already where
# they belong, namely the repo. We still report success so callers can run
# this unconditionally.
TARGET="${1:-$SKILLS_SRC}"

if [ ! -d "$SKILLS_SRC" ]; then
    echo "  ⚠️  no skills/ dir in $ROOT — skipping (R110-133 not active in this checkout)"
    exit 0
fi

# Sanity: refuse to install into a non-existent ancestor that we can't create.
TARGET_PARENT="$(dirname "$TARGET")"
if [ ! -d "$TARGET_PARENT" ]; then
    if ! mkdir -p "$TARGET_PARENT" 2>/dev/null; then
        echo "  ❌ cannot create $TARGET_PARENT — check path / permissions"
        exit 1
    fi
fi

if ! mkdir -p "$TARGET" 2>/dev/null; then
    echo "  ❌ cannot create $TARGET — check path / permissions"
    exit 1
fi

INSTALLED=0
if [ "$TARGET" = "$SKILLS_SRC" ]; then
    # Self-copy: source == target. We are already where we need to be.
    # Skip the install to avoid the cp-after-rm race (rm removes the source
    # before cp can read it). Count skills for the success report.
    INSTALLED=$(find "$SKILLS_SRC" -mindepth 2 -name "SKILL.md" -type f | wc -l)
else
    # Walk recursively: any directory containing a SKILL.md gets copied to
    # <TARGET>/<relative-path>. This handles both top-level skills
    # (mas-engineer-commit-protocol) and category subdirs (devops/, mas-engineer/).
    while IFS= read -r skill_md; do
        skill_dir="$(dirname "$skill_md")"
        rel="${skill_dir#${SKILLS_SRC}/}"
        target="$TARGET/$rel"
        if ! mkdir -p "$target" 2>/dev/null; then
            echo "  ❌ cannot create $target"
            exit 1
        fi
        # Idempotent overwrite for mas-engineer-owned skills; user-installed
        # skills (those not in the repo) are preserved by virtue of not being
        # touched — we only rm the skill-dirs we are about to (re-)write.
        rm -rf "$target"
        cp -r "$skill_dir" "$target"
        INSTALLED=$((INSTALLED + 1))
    done < <(find "$SKILLS_SRC" -mindepth 2 -name "SKILL.md" -type f)

    # Subset index: ship alongside the skills so the runtime can discover
    # them the same way it discovers its own.
    if [ -f "$SKILLS_SRC/SKILLS-INDEX.md" ]; then
        cp "$SKILLS_SRC/SKILLS-INDEX.md" "$TARGET/SKILLS-INDEX.mas-engineer.md"
    fi
fi

echo "  installed $INSTALLED skills → $TARGET"
if [ "$TARGET" = "$SKILLS_SRC" ]; then
    echo "  ℹ️  target = repo src — install was a no-op (skills already in place)"
else
    echo "  🛡️  preserved any skills in <target> that are not in the repo (no-delete policy)"
fi
exit 0
