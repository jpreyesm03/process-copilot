#!/usr/bin/env bash
# Back up this repo to OneDrive: full git history as one bundle file + a browsable snapshot of the working tree.
# Runs after every commit (git post-commit hook) and on demand. Secrets (.env) and rebuildable folders are skipped.
# Restore:  git clone process-copilot.bundle process-copilot && cd process-copilot && uv sync
set -euo pipefail
cd "$(dirname "$0")/.."
DEST="${P2_BACKUP_DIR:-$HOME/Library/CloudStorage/OneDrive-UW/JP/FDE_Consulting/proyectos/archive/p2_process_copilot_original}"
[ -d "$(dirname "$DEST")" ] || { echo "backup: OneDrive folder not found, skipped"; exit 0; }
mkdir -p "$DEST/snapshot"

git bundle create "$DEST/process-copilot.bundle.tmp" --all 2>/dev/null
mv -f "$DEST/process-copilot.bundle.tmp" "$DEST/process-copilot.bundle"

rsync -a --delete \
  --exclude '.git/' --exclude '.venv/' --exclude 'node_modules/' --exclude '.next/' \
  --exclude '__pycache__/' --exclude '.pytest_cache/' --exclude '.ruff_cache/' \
  --exclude '.env' --exclude '.env.local' --exclude 'web/.env.local' \
  ./ "$DEST/snapshot/"

cat > "$DEST/README.md" <<EOF
# P2 Process Copilot: backup

The working repo lives at \`~/other/process-copilot\` (outside OneDrive) and on GitHub:
https://github.com/jpreyesm03/process-copilot (private).

This folder is an automatic backup, refreshed after every commit:
- \`process-copilot.bundle\`: the full git history in one file.
- \`snapshot/\`: the current files, including uncommitted work (no .venv, node_modules, build output or .env secrets).

Restore on a new computer:
    git clone process-copilot.bundle process-copilot
    cd process-copilot && uv sync
    cp .env.example .env   # then add the keys again

Last backup: $(date '+%Y-%m-%d %H:%M %Z') · commit $(git rev-parse --short HEAD)
EOF
echo "backup: $DEST ($(git rev-parse --short HEAD))"
