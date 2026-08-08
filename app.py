
import os, re, json, signal, subprocess, secrets
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

BASE = Path(__file__).resolve().parent
PROJECTS = BASE / "projects"
RUNTIME = BASE / "runtime"
PROJECTS.mkdir(exist_ok=True)
RUNTIME.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "CHANGE_ME")

def logged_in():
    return session.get("admin") is True

def safe_name(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:80]

def pid_file(name):
    return RUNTIME / f"{safe_name(name)}.pid"

def log_file(name):
    return RUNTIME / f"{safe_name(name)}.log"

def project_dir(name):
    return PROJECTS / safe_name(name)

def running(name):
    pf = pid_file(name)
    if not pf.exists():
        return False
    try:
        pid = int(pf.read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        try: pf.unlink()
        except Exception: pass
        return False

def projects():
    out = []
    for p in sorted(PROJECTS.iterdir()):
        if p.is_dir():
            out.append({
                "name": p.name,
                "running": running(p.name),
                "files": [x.name for x in p.iterdir() if x.is_file()]
            })
    return out

@app.get("/")
def index():
    if not logged_in():
        return redirect(url_for("login"))
    return render_template("index.html", projects=projects())

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("index"))
        flash("Invalid login.")
    return render_template("login.html")

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.post("/upload")
def upload():
    if not logged_in(): return redirect(url_for("login"))
    name = safe_name(request.form.get("name",""))
    f = request.files.get("file")
    if not name or not f or not f.filename:
        flash("Project name and file are required.")
        return redirect(url_for("index"))

    ext = Path(f.filename).suffix.lower()
    if ext not in {".py", ".zip"}:
        flash("Only .py and .zip uploads are accepted.")
        return redirect(url_for("index"))

    d = project_dir(name)
    d.mkdir(exist_ok=True)
    # Store the upload as app.py for .py projects.
    if ext == ".py":
        f.save(d / "app.py")
    else:
        f.save(d / "project.zip")
        flash("ZIP uploaded. Unzip it on the server into this project folder before starting.")
    flash(f"Uploaded {name}.")
    return redirect(url_for("index"))

@app.post("/start/<name>")
def start(name):
    if not logged_in(): return redirect(url_for("login"))
    name = safe_name(name)
    d = project_dir(name)
    script = d / "app.py"
    if not script.exists():
        flash("This project needs an app.py file.")
        return redirect(url_for("index"))
    if running(name):
        flash("Project is already running.")
        return redirect(url_for("index"))

    log = open(log_file(name), "a", buffering=1)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    p = subprocess.Popen(
        ["python3", str(script)],
        cwd=str(d),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
        shell=False
    )
    pid_file(name).write_text(str(p.pid))
    flash(f"{name} started (PID {p.pid}).")
    return redirect(url_for("index"))

@app.post("/stop/<name>")
def stop(name):
    if not logged_in(): return redirect(url_for("login"))
    pf = pid_file(safe_name(name))
    if not pf.exists():
        flash("Project is not running.")
        return redirect(url_for("index"))
    try:
        pid = int(pf.read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    try: pf.unlink()
    except Exception: pass
    flash(f"{safe_name(name)} stopped.")
    return redirect(url_for("index"))

@app.get("/logs/<name>")
def logs(name):
    if not logged_in(): return redirect(url_for("login"))
    lf = log_file(safe_name(name))
    text = lf.read_text(errors="replace")[-20000:] if lf.exists() else "No logs yet."
    return render_template("logs.html", name=safe_name(name), logs=text)

@app.get("/api/status")
def api_status():
    if not logged_in(): return jsonify({"error":"unauthorized"}), 401
    return jsonify(projects())

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
