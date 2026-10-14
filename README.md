# Secure Digital Attendance and Access System

SEP / CIAP Micro Project

## Project idea
A small web-based system demonstrating secure authentication, role-based access control, digital attendance management and audit logging for an institutional environment.

## Technology
- Python
- Flask
- SQLite
- HTML/CSS
- Jinja templates

## Demo accounts
- Student: `student1` / `student123`
- Faculty: `faculty1` / `faculty123`
- Admin: `admin` / `admin123`

Change these credentials before any real deployment. They are included only for the college demonstration.

## Run on Windows

1. Install Python 3.11+.
2. Open PowerShell in this folder.
3. Create a virtual environment:
   `python -m venv venv`
4. Activate it:
   `venv\Scripts\Activate.ps1`
5. Install packages:
   `pip install -r requirements.txt`
6. Start:
   `python app.py`
7. Open:
   `http://127.0.0.1:5000`

The SQLite database is created automatically on first run.

## Main features
- Login and password hashing
- Role-based access control
- Resource access checking
- Digital attendance recording
- Duplicate attendance prevention
- Attendance history
- Security/access audit logs
- Dashboard statistics
