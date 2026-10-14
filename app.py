from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "local-development-only-change-me"
DB = "secure_attendance.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Student','Faculty','Admin'))
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course TEXT NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent')),
        marked_by INTEGER NOT NULL,
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(marked_by) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        resource TEXT NOT NULL,
        action TEXT NOT NULL,
        result TEXT NOT NULL,
        reason TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    users = [
        ("student1", generate_password_hash("student123"), "Rahul Shah", "Student"),
        ("faculty1", generate_password_hash("faculty123"), "Dr. Mehta", "Faculty"),
        ("admin", generate_password_hash("admin123"), "System Administrator", "Admin")
    ]
    for u in users:
        try:
            conn.execute("INSERT INTO users (username,password,full_name,role) VALUES (?,?,?,?)", u)
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def audit(resource, action, result, reason=""):
    conn = get_db()
    conn.execute(
        """INSERT INTO access_logs
           (user_id,resource,action,result,reason,timestamp)
           VALUES (?,?,?,?,?,?)""",
        (session["user_id"], resource, action, result, reason,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) c FROM attendance").fetchone()["c"]
    present = conn.execute("SELECT COUNT(*) c FROM attendance WHERE status='Present'").fetchone()["c"]
    absent = conn.execute("SELECT COUNT(*) c FROM attendance WHERE status='Absent'").fetchone()["c"]
    access_total = conn.execute("SELECT COUNT(*) c FROM access_logs").fetchone()["c"]
    denied = conn.execute("SELECT COUNT(*) c FROM access_logs WHERE result='DENIED'").fetchone()["c"]
    recent = conn.execute("""
        SELECT l.*, u.full_name FROM access_logs l
        JOIN users u ON u.id=l.user_id ORDER BY l.id DESC LIMIT 8
    """).fetchall()
    conn.close()
    return render_template("dashboard.html", total=total, present=present,
                           absent=absent, access_total=access_total, denied=denied,
                           recent=recent)

@app.route("/access", methods=["GET", "POST"])
@login_required
def access():
    result = None
    if request.method == "POST":
        resource = request.form["resource"]
        role = session["role"]

        allowed = {
            "Classroom": ["Student", "Faculty", "Admin"],
            "Computer Lab": ["Faculty", "Admin"],
            "Cybersecurity Lab": ["Faculty", "Admin"],
            "Administration Office": ["Admin"]
        }

        if role in allowed.get(resource, []):
            result = ("GRANTED", "Role is authorized for this resource.")
            audit(resource, "Access Attempt", "GRANTED", result[1])
        else:
            result = ("DENIED", "Role is not authorized for this resource.")
            audit(resource, "Access Attempt", "DENIED", result[1])

    return render_template("access.html", result=result)

@app.route("/attendance", methods=["GET", "POST"])
@login_required
@role_required("Faculty", "Admin")
def attendance():
    conn = get_db()
    students = conn.execute("SELECT id, full_name, username FROM users WHERE role='Student'").fetchall()

    if request.method == "POST":
        student_id = request.form["student_id"]
        course = request.form["course"].strip()
        status = request.form["status"]
        date = request.form["date"] or datetime.now().strftime("%Y-%m-%d")

        existing = conn.execute("""
            SELECT id FROM attendance
            WHERE student_id=? AND course=? AND date=?
        """, (student_id, course, date)).fetchone()

        if existing:
            flash("Attendance already exists for this student, course and date.", "warning")
        else:
            conn.execute("""
                INSERT INTO attendance(student_id,course,date,status,marked_by)
                VALUES(?,?,?,?,?)
            """, (student_id, course, date, status, session["user_id"]))
            conn.commit()
            flash("Attendance recorded successfully.", "success")
            audit("Attendance", "Mark Attendance", "GRANTED",
                  f"{status} recorded for student ID {student_id}")

    records = conn.execute("""
        SELECT a.*, u.full_name AS student_name, m.full_name AS marked_by_name
        FROM attendance a
        JOIN users u ON u.id=a.student_id
        JOIN users m ON m.id=a.marked_by
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()
    return render_template("attendance.html", students=students, records=records)

@app.route("/my-attendance")
@login_required
def my_attendance():
    conn = get_db()
    records = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id=? ORDER BY date DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("my_attendance.html", records=records)

@app.route("/logs")
@login_required
@role_required("Admin", "Faculty")
def logs():
    conn = get_db()
    logs = conn.execute("""
        SELECT l.*, u.full_name, u.role
        FROM access_logs l JOIN users u ON u.id=l.user_id
        ORDER BY l.id DESC
    """).fetchall()
    conn.close()
    return render_template("logs.html", logs=logs)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
