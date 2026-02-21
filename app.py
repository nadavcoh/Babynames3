#!/usr/bin/env python3
"""שם טוב — Name Explorer · Flask backend"""

import json, sqlite3, os, argparse, socket, sys
from flask import Flask, request, jsonify, render_template, g, send_from_directory

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "shem_tov.db")

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
        import time, platform
        app_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.run(["git", "-C", app_dir, "pull"], check=True)

        if platform.system() == "Windows":
            # On Windows, spawn a new detached process then exit
            python = os.path.join(app_dir, "venv", "Scripts", "python.exe")
            if not os.path.exists(python):
                python = sys.executable
            subprocess.Popen(
                [python, os.path.join(app_dir, "app.py")] + sys.argv[1:],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
        else:
            # On Linux/Mac, execv replaces this process in-place
            python = os.path.join(app_dir, "venv", "bin", "python")
            if not os.path.exists(python):
                python = sys.executable
            os.execv(python, [python, os.path.join(app_dir, "app.py")] + sys.argv[1:])

        time.sleep(1)   # give the new process a moment to bind the port
        os._exit(0)     # exit the old process

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
    db.commit(); db.close()

USER_ID = "default"
DEFAULTS = {
    "minTotal": 20, "showUnisex": True, "showVintage": True,
    "showModern": True, "showClassic": True, "cardTheme": "warm",
    "showDaughters": True,
}

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
    args = p.parse_args()
    init_db()
    try: local_ip = socket.gethostbyname(socket.gethostname())
    except: local_ip = "?.?.?.?"
    print(f"\n  \u05E9\u05DD \u05D8\u05D5\u05D1  \u2014  Name Explorer")
    print(f"  Local:    http://localhost:{args.port}")
    print(f"  Network:  http://{local_ip}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)