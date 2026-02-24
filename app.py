#!/usr/bin/env python3
"""שם טוב — Name Explorer · Flask backend"""

import json, sqlite3, os, argparse, socket, sys, subprocess
from flask import Flask, request, jsonify, render_template, g, send_from_directory

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "shem_tov.db")

def get_version():
    """Return short git hash + date, or 'dev' if git unavailable."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        sha = subprocess.check_output(
            ["git", "-C", app_dir, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
        date = subprocess.check_output(
            ["git", "-C", app_dir, "log", "-1", "--format=%cd", "--date=short"],
            stderr=subprocess.DEVNULL).decode().strip()
        return f"{sha} ({date})"
    except Exception:
        return "dev"

APP_VERSION = get_version()  # computed once at startup

# ─── GITHUB WEBHOOK (auto-deploy on push) ─────────────────────────────────────
import hmac, hashlib, subprocess, threading

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

@app.route("/webhook", methods=["POST"])
def github_webhook():
    # Verify signature
    if WEBHOOK_SECRET:
        sig = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), request.data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return jsonify({"error": "bad signature"}), 403

    # Only act on push events
    if request.headers.get("X-GitHub-Event") != "push":
        return jsonify({"ok": True, "action": "ignored"})

    def do_deploy():
        import platform, tempfile
        app_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.run(["git", "-C", app_dir, "pull"], check=True)

        if platform.system() == "Windows":
            # Write a relay .bat that waits for this process to exit (port to free),
            # then starts a fresh python process. We exit immediately after launching
            # the relay so the port is released before the new server tries to bind it.
            python = os.path.join(app_dir, "venv", "Scripts", "python.exe")
            if not os.path.exists(python):
                python = sys.executable
            args = " ".join(
                f'"{a}"' for a in [python, os.path.join(app_dir, "app.py")] + sys.argv[1:]
            )
            bat = os.path.join(tempfile.gettempdir(), "_shem_tov_restart.bat")
            with open(bat, "w") as f:
                f.write(
                    "@echo off\n"
                    "timeout /t 2 /nobreak >nul\n"
                    f"start \"shem_tov\" {args}\n"
                )
            subprocess.Popen(
                ["cmd", "/c", bat],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
            # Exit immediately — port is freed before the relay fires
            os._exit(0)
        else:
            # On Linux/Mac, execv replaces this process in-place (same PID, same port)
            python = os.path.join(app_dir, "venv", "bin", "python")
            if not os.path.exists(python):
                python = sys.executable
            os.execv(python, [python, os.path.join(app_dir, "app.py")] + sys.argv[1:])

    threading.Thread(target=do_deploy, daemon=True).start()
    return jsonify({"ok": True, "action": "deploying"})
 
# ─── DATABASE FUNCTIONS ───
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS state (
        user_id TEXT PRIMARY KEY, liked TEXT NOT NULL DEFAULT '[]',
        skipped TEXT NOT NULL DEFAULT '[]', updated DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS settings (
        user_id TEXT PRIMARY KEY, prefs TEXT NOT NULL DEFAULT '{}',
        updated DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS ratings (
        user_id TEXT PRIMARY KEY, data TEXT NOT NULL DEFAULT '{}',
        updated DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db.commit(); db.close()

USER_ID = "default"
DEFAULTS = {
    "minTotal": 20, "showUnisex": True, "showVintage": True,
    "showModern": True, "showClassic": True, "cardTheme": "warm",
    "showDaughters": True,
}

@app.route("/api/version")
def get_version_route():
    return jsonify({"version": APP_VERSION})

# ─── STATE ───
@app.route("/api/state", methods=["GET"])
def get_state():
    row = get_db().execute("SELECT liked,skipped FROM state WHERE user_id=?", (USER_ID,)).fetchone()
    return jsonify({"liked": json.loads(row["liked"]), "skipped": json.loads(row["skipped"])} if row else {"liked":[],"skipped":[]})

@app.route("/api/state", methods=["POST"])
def save_state():
    d = request.get_json(force=True)
    db = get_db()
    db.execute("""INSERT INTO state(user_id,liked,skipped) VALUES(?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET liked=excluded.liked,skipped=excluded.skipped,updated=CURRENT_TIMESTAMP""",
        (USER_ID, json.dumps(d.get("liked",[]),ensure_ascii=False), json.dumps(d.get("skipped",[]),ensure_ascii=False)))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/state", methods=["DELETE"])
def clear_state():
    db = get_db(); db.execute("DELETE FROM state WHERE user_id=?", (USER_ID,)); db.commit()
    return jsonify({"ok": True})

# ─── SETTINGS ───
@app.route("/api/settings", methods=["GET"])
def get_settings():
    row = get_db().execute("SELECT prefs FROM settings WHERE user_id=?", (USER_ID,)).fetchone()
    return jsonify({**DEFAULTS, **(json.loads(row["prefs"]) if row else {})})

@app.route("/api/settings", methods=["POST"])
def save_settings():
    merged = {**DEFAULTS, **request.get_json(force=True)}
    db = get_db()
    db.execute("""INSERT INTO settings(user_id,prefs) VALUES(?,?)
        ON CONFLICT(user_id) DO UPDATE SET prefs=excluded.prefs,updated=CURRENT_TIMESTAMP""",
        (USER_ID, json.dumps(merged)))
    db.commit()
    return jsonify({"ok": True, "settings": merged})

# ─── RATINGS ───
@app.route("/api/ratings", methods=["GET"])
def get_ratings():
    row = get_db().execute("SELECT data FROM ratings WHERE user_id=?", (USER_ID,)).fetchone()
    return jsonify(json.loads(row["data"]) if row else {})

@app.route("/api/ratings", methods=["POST"])
def save_ratings():
    d = request.get_json(force=True)
    db = get_db()
    db.execute("""INSERT INTO ratings(user_id,data) VALUES(?,?)
        ON CONFLICT(user_id) DO UPDATE SET data=excluded.data,updated=CURRENT_TIMESTAMP""",
        (USER_ID, json.dumps(d, ensure_ascii=False)))
    db.commit()
    return jsonify({"ok": True})

# ─── NAMES DATA ───
import functools

@app.route("/api/names")
@functools.lru_cache(maxsize=1)  # serve from cache after first load
def get_names():
    names_path = os.path.join(os.path.dirname(__file__), "static", "names.json")
    with open(names_path, encoding="utf-8") as f:
        data = f.read()
    from flask import Response
    return Response(data, mimetype="application/json",
                    headers={"Cache-Control": "public, max-age=86400"})


# ─── PATCH / PR ENDPOINT ──────────────────────────────────────────────────────
@app.route("/api/patch", methods=["POST"])
def apply_patch():
    """
    Receive a .tar.gz from iOS Shortcut, extract it, create a branch, push, open PR.
    Requires env vars: GITHUB_TOKEN, GITHUB_REPO (e.g. nadavcoh/Babynames3)
    Headers: X-Branch-Name (optional, defaults to patch/TIMESTAMP)
    """
    import tempfile, tarfile, shutil, time
    from datetime import datetime

    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPO", "")
    if not token or not repo:
        return jsonify({"error": "GITHUB_TOKEN and GITHUB_REPO env vars required"}), 500

    app_dir    = os.path.dirname(os.path.abspath(__file__))
    branch     = request.headers.get("X-Branch-Name") or f"patch/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    pr_title   = request.headers.get("X-PR-Title") or f"Patch {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Save the uploaded tarball to a temp file
    tmp = tempfile.mkdtemp()
    try:
        tar_path = os.path.join(tmp, "patch.tar.gz")
        request.stream.seek(0)
        with open(tar_path, "wb") as f:
            f.write(request.data or request.stream.read())

        # Extract
        extract_dir = os.path.join(tmp, "extracted")
        os.makedirs(extract_dir)
        with tarfile.open(tar_path) as t:
            # Strip leading component (e.g. "shem_tov/") if present
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
                    if ".." in m.name or os.path.isabs(m.name):
                        app.logger.warning(f"Skipping potentially malicious path in tarball: {m.name}")
                        continue
                    t.extract(m, extract_dir)

        # Run the make_pr.sh script
        script = os.path.join(app_dir, "scripts", "make_pr.sh")
        env = os.environ.copy()
        env["GITHUB_TOKEN"] = token
        result = subprocess.run(
            ["bash", script, extract_dir, branch, pr_title, repo, app_dir],
            capture_output=True, text=True, timeout=60, env=env
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr or result.stdout}), 500

        pr_url = result.stdout.strip().splitlines()[-1]  # last line is the PR URL
        return jsonify({"ok": True, "pr_url": pr_url, "branch": branch})

    except Exception as e:
        app.logger.error(f"Error applying patch: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while applying the patch."}), 500
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ─── SERVE ───
@app.route("/static/<path:path>")
def static_files(path): return send_from_directory("static", path)

@app.route("/")
def index(): return render_template("index.html")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=5003)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--cert", default="", help="Path to TLS certificate file (e.g. from tailscale cert)")
    p.add_argument("--key",  default="", help="Path to TLS private key file")
    args = p.parse_args()
    init_db()
    try: local_ip = socket.gethostbyname(socket.gethostname())
    except: local_ip = "?.?.?.?"
    scheme = "https" if args.cert else "http"
    print(f"\n  \u05E9\u05DD \u05D8\u05D5\u05D1  \u2014  Name Explorer  [{APP_VERSION}]")
    print(f"  Local:    {scheme}://localhost:{args.port}")
    print(f"  Network:  {scheme}://{local_ip}:{args.port}\n")
    ssl_ctx = (args.cert, args.key) if args.cert and args.key else None
    app.run(host=args.host, port=args.port, debug=args.debug, ssl_context=ssl_ctx)