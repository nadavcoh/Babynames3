#!/usr/bin/env python3
"""
deploy_patch.py — runs in a-Shell on iOS
Invoked directly by Shortcuts: python3 ~/Documents/deploy_patch.py

Config file: ~/Documents/deploy_config.txt
  GITHUB_TOKEN=ghp_...
  GITHUB_REPO=nadavcoh/Babynames3
"""

import os, sys, subprocess, tarfile, shutil, json, urllib.request, urllib.error
from datetime import datetime

# ── Load config from file (no env vars / shell needed) ───────────────────────
CONFIG_PATH = os.path.expanduser("~/Documents/deploy_config.txt")
config = {}
if os.path.exists(CONFIG_PATH):
    for line in open(CONFIG_PATH):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip()

GITHUB_TOKEN = config.get("GITHUB_TOKEN", "")
GITHUB_REPO  = config.get("GITHUB_REPO", "")
TARBALL      = os.path.expanduser("~/Documents/patch.tar.gz")
BRANCH       = "patch/" + datetime.now().strftime("%Y%m%d-%H%M%S")
PR_TITLE     = "Patch from iOS " + datetime.now().strftime("%Y-%m-%d %H:%M")
WORK_DIR     = os.path.expanduser("~/Documents/babynames_repo")

def die(msg):
    print("\n✗", msg)
    sys.exit(1)

def run(*cmd, cwd=None):
    print("  $", " ".join(cmd))
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        die((r.stderr or r.stdout or f"{cmd[0]} failed").strip())
    return r.stdout.strip()

# ── Validate ──────────────────────────────────────────────────────────────────
if not GITHUB_TOKEN:
    die(f"GITHUB_TOKEN missing.\nCreate {CONFIG_PATH} with:\n  GITHUB_TOKEN=ghp_yourtoken\n  GITHUB_REPO=nadavcoh/Babynames3")
if not GITHUB_REPO:
    die(f"GITHUB_REPO missing in {CONFIG_PATH}")
if not os.path.exists(TARBALL):
    die(f"Tarball not found: {TARBALL}")

AUTHED = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"

print(f"\n=== שם טוב patch deployer ===")
print(f"Tarball : {TARBALL}")
print(f"Branch  : {BRANCH}")
print(f"Repo    : {GITHUB_REPO}\n")

# ── Clone or pull ─────────────────────────────────────────────────────────────
if os.path.isdir(os.path.join(WORK_DIR, ".git")):
    print("→ Updating existing clone...")
    run("lg2", "checkout", "main", cwd=WORK_DIR)
    run("lg2", "pull", AUTHED, "main", cwd=WORK_DIR)
else:
    print("→ Cloning repo...")
    os.makedirs(os.path.dirname(WORK_DIR), exist_ok=True)
    run("lg2", "clone", AUTHED, WORK_DIR)

# ── Create branch ─────────────────────────────────────────────────────────────
print(f"→ Creating branch {BRANCH}...")
run("lg2", "checkout", "-b", BRANCH, cwd=WORK_DIR)

# ── Extract tarball ───────────────────────────────────────────────────────────
print(f"→ Extracting patch...")
EXTRACT_TMP = os.path.expanduser("~/Documents/_patch_extract")
shutil.rmtree(EXTRACT_TMP, ignore_errors=True)
os.makedirs(EXTRACT_TMP)

with tarfile.open(TARBALL) as t:
    members = t.getmembers()
    top = members[0].name.split("/")[0] if members else ""
    for m in members:
        parts = m.name.split("/", 1)
        if len(parts) > 1 and parts[0] == top:
            m.name = parts[1]
        elif parts[0] == top:
            continue
        if m.name:
            # Security: ensure path is safe before extracting
            if ".." in m.name or m.name.startswith("/"):
                print(f"✗ Skipping potentially malicious path in tarball: {m.name}")
                continue
            t.extract(m, EXTRACT_TMP)

SKIP = {"venv", "__pycache__", ".git"}
for item in os.listdir(EXTRACT_TMP):
    if item in SKIP or item.endswith(".db"):
        continue
    src = os.path.join(EXTRACT_TMP, item)
    dst = os.path.join(WORK_DIR, item)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

shutil.rmtree(EXTRACT_TMP, ignore_errors=True)

# ── Commit ────────────────────────────────────────────────────────────────────
print("→ Committing...")
run("lg2", "add", ".", cwd=WORK_DIR)
status = run("lg2", "status", "--short", cwd=WORK_DIR)
if not status:
    run("lg2", "checkout", "main", cwd=WORK_DIR)
    run("lg2", "branch", "-d", BRANCH, cwd=WORK_DIR)
    die("No changes — tarball is identical to main.")

run("lg2", "commit", "-m", PR_TITLE,
    "--author", "iOS Patch <patch@shem-tov.local>",
    cwd=WORK_DIR)

# ── Push ──────────────────────────────────────────────────────────────────────
print(f"→ Pushing...")
run("lg2", "push", AUTHED, BRANCH, cwd=WORK_DIR)

# ── Open PR ───────────────────────────────────────────────────────────────────
print("→ Creating PR...")
payload = json.dumps({
    "title": PR_TITLE, "head": BRANCH, "base": "main",
    "body": "Automated patch from iOS via a-Shell."
}).encode()
req = urllib.request.Request(
    f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
    data=payload,
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
)
try:
    with urllib.request.urlopen(req) as resp:
        pr_url = json.loads(resp.read())["html_url"]
except urllib.error.HTTPError as e:
    die(f"GitHub API: {json.loads(e.read()).get('message', str(e))}")

run("lg2", "checkout", "main", cwd=WORK_DIR)
print(f"\n✓ Done! Opening PR...")
run("open", pr_url)
