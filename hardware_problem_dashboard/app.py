import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "dashboard.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
STATUSES = ["Open", "Under Investigation", "In Progress", "Testing", "Resolved", "On Hold"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','client')),
        client_name TEXT
    );
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_key TEXT UNIQUE NOT NULL,
        client_name TEXT NOT NULL,
        hardware TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        root_cause TEXT DEFAULT '',
        action_taken TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Open',
        progress INTEGER NOT NULL DEFAULT 0,
        assigned_to TEXT DEFAULT '',
        target_date TEXT DEFAULT '',
        verification TEXT DEFAULT '',
        remarks TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    if not conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        conn.execute("INSERT INTO users(username,password_hash,role,client_name) VALUES(?,?,?,?)",
                     ("admin", generate_password_hash("Admin@123"), "admin", None))
        conn.execute("INSERT INTO users(username,password_hash,role,client_name) VALUES(?,?,?,?)",
                     ("client1", generate_password_hash("Client@123"), "client", "Acme Manufacturing"))
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        samples = [
            ("HW-1001","Acme Manufacturing","Industrial Control Unit","Power supply failure",
             "Unit shuts down intermittently during operation.","Loose power connector","Connector replaced and load test completed.","Resolved",100,"R. Kumar","2026-11-22","Passed","Operating normally."),
            ("HW-1002","Acme Manufacturing","CNC Controller","Controller overheating",
             "Temperature rises above the normal operating range.","Cooling fan airflow restricted","Fan cleaned; replacement fan being arranged.","In Progress",65,"S. Priya","2026-11-25","","Awaiting replacement fan."),
            ("HW-1003","Acme Manufacturing","Operator Display","Display flickering",
             "Display flickers after extended usage.","","Initial inspection completed.","Under Investigation",25,"R. Kumar","2026-11-27","","Diagnostic testing underway."),
            ("HW-1004","Northstar Components","Network Gateway","Intermittent network connection",
             "Gateway disconnects from the plant network.","Damaged patch cable","Cable replaced and connectivity verified.","Testing",90,"A. Dev","2026-11-20","","Final soak test in progress.")
        ]
        for s in samples:
            conn.execute("""INSERT INTO issues(issue_key,client_name,hardware,title,description,root_cause,
                         action_taken,status,progress,assigned_to,target_date,verification,remarks,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*s, now, now))
    conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], username=user["username"], role=user["role"],
                           client_name=user["client_name"])
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    if session["role"] == "admin":
        issues = conn.execute("SELECT * FROM issues ORDER BY updated_at DESC").fetchall()
    else:
        issues = conn.execute("SELECT * FROM issues WHERE client_name=? ORDER BY updated_at DESC",
                              (session.get("client_name"),)).fetchall()
    conn.close()
    total = len(issues)
    resolved = sum(1 for x in issues if x["status"] == "Resolved")
    active = sum(1 for x in issues if x["status"] in ("Under Investigation","In Progress","Testing"))
    pending = sum(1 for x in issues if x["status"] in ("Open","On Hold"))
    avg_progress = round(sum(x["progress"] for x in issues)/total) if total else 0
    status_counts = {s: sum(1 for x in issues if x["status"] == s) for s in STATUSES}
    return render_template("dashboard.html", issues=issues, total=total, resolved=resolved,
                           active=active, pending=pending, avg_progress=avg_progress,
                           status_counts=status_counts, statuses=STATUSES)

@app.route("/issues/new", methods=["GET","POST"])
@admin_required
def new_issue():
    if request.method == "POST":
        form = issue_form()
        if not form["client_name"] or not form["hardware"] or not form["title"] or not form["description"]:
            flash("Client, hardware, problem title and description are required.", "error")
            return render_template("issue_form.html", issue=None, statuses=STATUSES)
        conn = db()
        next_id = conn.execute("SELECT COALESCE(MAX(id),0)+1 AS n FROM issues").fetchone()["n"]
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute("""INSERT INTO issues(issue_key,client_name,hardware,title,description,root_cause,
                     action_taken,status,progress,assigned_to,target_date,verification,remarks,created_at,updated_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (f"HW-{1000+next_id}", form["client_name"], form["hardware"], form["title"],
                      form["description"], form["root_cause"], form["action_taken"], form["status"],
                      form["progress"], form["assigned_to"], form["target_date"], form["verification"],
                      form["remarks"], now, now))
        conn.commit()
        conn.close()
        flash("Problem created successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("issue_form.html", issue=None, statuses=STATUSES)

def issue_form():
    return {
        "client_name": request.form.get("client_name","").strip(),
        "hardware": request.form.get("hardware","").strip(),
        "title": request.form.get("title","").strip(),
        "description": request.form.get("description","").strip(),
        "root_cause": request.form.get("root_cause","").strip(),
        "action_taken": request.form.get("action_taken","").strip(),
        "status": request.form.get("status","Open"),
        "progress": max(0,min(100,int(request.form.get("progress",0) or 0))),
        "assigned_to": request.form.get("assigned_to","").strip(),
        "target_date": request.form.get("target_date","").strip(),
        "verification": request.form.get("verification","").strip(),
        "remarks": request.form.get("remarks","").strip()
    }

@app.route("/issues/<int:issue_id>/edit", methods=["GET","POST"])
@admin_required
def edit_issue(issue_id):
    conn = db()
    issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if not issue:
        conn.close()
        abort(404)
    if request.method == "POST":
        f = issue_form()
        conn.execute("""UPDATE issues SET client_name=?,hardware=?,title=?,description=?,root_cause=?,
                     action_taken=?,status=?,progress=?,assigned_to=?,target_date=?,verification=?,remarks=?,
                     updated_at=? WHERE id=?""",
                     (f["client_name"],f["hardware"],f["title"],f["description"],f["root_cause"],
                      f["action_taken"],f["status"],f["progress"],f["assigned_to"],f["target_date"],
                      f["verification"],f["remarks"],datetime.now().strftime("%Y-%m-%d %H:%M"),issue_id))
        conn.commit()
        conn.close()
        flash("Problem updated successfully.", "success")
        return redirect(url_for("dashboard"))
    conn.close()
    return render_template("issue_form.html", issue=issue, statuses=STATUSES)

@app.route("/issues/<int:issue_id>")
@login_required
def issue_detail(issue_id):
    conn = db()
    issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    conn.close()
    if not issue:
        abort(404)
    if session["role"] != "admin" and issue["client_name"] != session.get("client_name"):
        abort(403)
    return render_template("issue_detail.html", issue=issue)

@app.route("/admin/users", methods=["GET","POST"])
@admin_required
def users():
    conn = db()
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        client_name = request.form.get("client_name","").strip()
        if not username or len(password) < 8 or not client_name:
            flash("Enter a username, client name and password of at least 8 characters.", "error")
        else:
            try:
                conn.execute("INSERT INTO users(username,password_hash,role,client_name) VALUES(?,?,?,?)",
                             (username,generate_password_hash(password),"client",client_name))
                conn.commit()
                flash("Client login created.", "success")
            except sqlite3.IntegrityError:
                flash("That username already exists.", "error")
    rows = conn.execute("SELECT id,username,client_name FROM users WHERE role='client' ORDER BY username").fetchall()
    conn.close()
    return render_template("users.html", users=rows)

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The requested item was not found."), 404

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
