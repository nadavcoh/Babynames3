#!/bin/sh
# deploy_patch.sh — runs in a-Shell on iOS (uses lg2, not git)
# Usage: deploy_patch.sh <path_to_patch.tar.gz> [branch_name] [pr_title]
#
# One-time setup in a-Shell:
#   echo 'export GITHUB_TOKEN=ghp_...' >> ~/Documents/.profile
#   echo 'export GITHUB_REPO=nadavcoh/Babynames3' >> ~/Documents/.profile

set -e

TARBALL="${1:?Usage: deploy_patch.sh <patch.tar.gz> [branch] [title]}"
BRANCH="${2:-patch/$(date '+%Y%m%d-%H%M%S')}"
PR_TITLE="${3:-Patch from iOS $(date '+%Y-%m-%d %H:%M')}"

GITHUB_TOKEN="${GITHUB_TOKEN:?Please set GITHUB_TOKEN in ~/Documents/.profile}"
GITHUB_REPO="${GITHUB_REPO:?Please set GITHUB_REPO in ~/Documents/.profile}"

WORK_DIR="$HOME/Documents/babynames_repo"
AUTHED_REMOTE="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"

echo "=== שם טוב patch deployer ==="
echo "Tarball : $TARBALL"
echo "Branch  : $BRANCH"
echo "Repo    : $GITHUB_REPO"
echo ""

# ── Clone or update repo ──────────────────────────────────────────────────────
if [ -d "$WORK_DIR/.git" ]; then
  echo "→ Updating existing clone..."
  cd "$WORK_DIR"
  lg2 checkout main
  lg2 pull "$AUTHED_REMOTE" main
else
  echo "→ Cloning repo..."
  lg2 clone "$AUTHED_REMOTE" "$WORK_DIR"
  cd "$WORK_DIR"
fi

# ── Create branch ─────────────────────────────────────────────────────────────
echo "→ Creating branch $BRANCH..."
lg2 checkout -b "$BRANCH"

# ── Extract tarball into repo ─────────────────────────────────────────────────
echo "→ Extracting $TARBALL..."
EXTRACT_TMP="$HOME/Documents/_patch_extract"
rm -rf "$EXTRACT_TMP"
mkdir -p "$EXTRACT_TMP"
tar -xzf "$TARBALL" -C "$EXTRACT_TMP"

# Strip leading directory (e.g. "repo/" or "Babynames3-main/")
TOP=$(ls "$EXTRACT_TMP" | head -1)
if [ -d "$EXTRACT_TMP/$TOP" ]; then
  SRC="$EXTRACT_TMP/$TOP"
else
  SRC="$EXTRACT_TMP"
fi

cp -r "$SRC/." "$WORK_DIR/"
# Remove things that must not be committed
rm -rf "$WORK_DIR/venv" "$WORK_DIR/__pycache__" "$WORK_DIR"/*.db 2>/dev/null || true

# ── Commit ────────────────────────────────────────────────────────────────────
echo "→ Committing..."
lg2 add .

# lg2 doesn't support diff --cached, check status instead
STATUS=$(lg2 status --short 2>/dev/null || lg2 status)
if [ -z "$STATUS" ]; then
  echo "✗ No changes — tarball matches what's already on main."
  lg2 checkout main
  lg2 branch -d "$BRANCH" 2>/dev/null || true
  rm -rf "$EXTRACT_TMP"
  exit 1
fi

lg2 commit -m "$PR_TITLE" \
  --author "iOS Patch <patch@shem-tov.local>"

# ── Push ──────────────────────────────────────────────────────────────────────
echo "→ Pushing $BRANCH..."
lg2 push "$AUTHED_REMOTE" "$BRANCH"

# ── Create PR via GitHub API ──────────────────────────────────────────────────
echo "→ Opening pull request..."
API_RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${GITHUB_REPO}/pulls" \
  -d "{\"title\":\"${PR_TITLE}\",\"head\":\"${BRANCH}\",\"base\":\"main\",\"body\":\"Automated patch from iOS via a-Shell.\"}")

PR_URL=$(echo "$API_RESPONSE" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('html_url','ERROR: '+d.get('message','unknown')))")

# Cleanup
rm -rf "$EXTRACT_TMP"
lg2 checkout main

if echo "$PR_URL" | grep -q "^https://"; then
  echo ""
  echo "✓ PR created: $PR_URL"
  open "$PR_URL"
else
  echo "✗ PR creation failed:"
  echo "$API_RESPONSE"
  exit 1
fi
