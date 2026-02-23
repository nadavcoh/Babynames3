#!/usr/bin/env bash
# make_pr.sh — called by Flask /api/patch
# Usage: make_pr.sh <extract_dir> <branch> <pr_title> <github_token> <github_repo> <app_dir>
#
# Copies files from extract_dir into the app, creates a branch, pushes, opens a PR.
# Prints the PR URL as the last line of stdout.

set -euo pipefail

EXTRACT_DIR="$1"
BRANCH="$2"
PR_TITLE="$3"
GITHUB_TOKEN="$4"
GITHUB_REPO="$5"  # e.g. nadavcoh/Babynames3
APP_DIR="$6"

# ── Go to repo root ────────────────────────────────────────────────────────────
cd "$APP_DIR"

# Make sure we're clean on main
git fetch origin main --quiet
git checkout main --quiet
git pull origin main --quiet

# ── Create branch ─────────────────────────────────────────────────────────────
git checkout -b "$BRANCH"

# ── Copy files from extract (skip scripts/, .git/, .github/ to avoid loops) ──
rsync -a \
  --exclude='.git/' \
  --exclude='.github/' \
  --exclude='scripts/' \
  --exclude='*.db' \
  --exclude='__pycache__/' \
  --exclude='venv/' \
  "$EXTRACT_DIR/" "$APP_DIR/"

# ── Commit ────────────────────────────────────────────────────────────────────
git add -A
if git diff --cached --quiet; then
  echo "No changes to commit" >&2
  git checkout main --quiet
  git branch -d "$BRANCH" --quiet
  exit 1
fi

git commit -m "$PR_TITLE"

# ── Push ──────────────────────────────────────────────────────────────────────
git push "https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git" "$BRANCH"

# ── Open PR via GitHub API ────────────────────────────────────────────────────
RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${GITHUB_REPO}/pulls" \
  -d "{
    \"title\": \"${PR_TITLE}\",
    \"head\":  \"${BRANCH}\",
    \"base\":  \"main\",
    \"body\":  \"Automated patch from iOS Shortcut via שם טוב patch endpoint.\"
  }")

PR_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['html_url'])" 2>/dev/null || echo "")

if [ -z "$PR_URL" ]; then
  echo "PR creation failed. API response:" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

# Return to main
git checkout main --quiet

# Last line must be the PR URL (Flask reads it)
echo "$PR_URL"
