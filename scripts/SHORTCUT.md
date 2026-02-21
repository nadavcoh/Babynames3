# iOS Shortcut: Deploy Patch via a-Shell

---

## One-time setup

### 1. Install a-Shell
Free on the App Store: **a-Shell** by Nicolas Holzschuch

### 2. Copy deploy_patch.py to a-Shell
In **Files**: copy `deploy_patch.py` to **On My iPhone → a-Shell → Documents**

### 3. Create config file
In a-Shell, type:
```
edit ~/Documents/deploy_config.txt
```
Enter these two lines, then save:
```
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_REPO=nadavcoh/Babynames3
```
Get a token at **github.com/settings/tokens** with `repo` scope.

---

## Build the Shortcut

Open **Shortcuts** → **+** → name it **"Deploy Patch"**

### Action 1 — Receive the file
- **Receive input** from Share Sheet
- Accept: **Files**
- If no input → Stop and respond: "No file received"

### Action 2 — Save to a-Shell's Documents
- **Save File**
- Where: **On My iPhone → a-Shell → Documents**
- File name: `patch.tar.gz`
- Overwrite if exists: **On**

### Action 3 — Run in a-Shell
- **Run Command** *(the a-Shell Shortcuts action)*
- Command:
```
python3 ~/Documents/deploy_patch.py
```

That's the entire command — no `source`, no `&&`, no variables.

---

## Usage

1. Claude gives you a `.tar.gz`
2. Long-press the file → Share → **Deploy Patch**
3. a-Shell opens, runs for ~10 seconds
4. Safari opens the new PR automatically
