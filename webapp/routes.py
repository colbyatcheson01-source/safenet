import json
import os
import sys
import secrets
import sqlite3
import threading
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash

from webapp.app import get_db

main_bp = Blueprint("main", __name__)
BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(BASE)

sys.path.insert(0, BASE_DIR)
import updater

UPDATE_STATUS = {"checking": False, "available": False, "version": "", "error": ""}


def load_json(name):
    with open(os.path.join(BASE, "data", name), "r", encoding="utf-8") as f:
        return json.load(f)


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "login required"}), 401
            return redirect(url_for("main.login", next=request.path))
        return f(*a, **kw)
    return wrapper


def log_activity(user_id, action, details=None):
    try:
        db = get_db()
        db.execute("INSERT INTO activity_log (user_id, action, details) VALUES (?, ?, ?)",
                   (user_id, action, details))
        db.commit()
        db.close()
    except sqlite3.Error:
        pass


# ─── Auth ─────────────────────────────────────────────────

@main_bp.route("/auth/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        if not data.get("email") or not data.get("password") or not data.get("name"):
            return render_template("register.html", error="All fields required")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                (data["email"].strip(), generate_password_hash(data["password"]), data["name"].strip()),
            )
            db.commit()
            row = db.execute("SELECT id, is_admin FROM users WHERE email=?", (data["email"].strip(),)).fetchone()
            session["user_id"] = row["id"]
            session["is_admin"] = bool(row["is_admin"])
            session["user_name"] = data["name"].strip()
            db.close()
            log_activity(row["id"], "account_created")
            return redirect(url_for("main.index"))
        except sqlite3.IntegrityError:
            db.close()
            return render_template("register.html", error="Email already registered")
    return render_template("register.html")


@main_bp.route("/auth/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (data.get("email", "").strip(),)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], data.get("password", "")):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = bool(user["is_admin"])
            log_activity(user["id"], "login")
            nxt = request.args.get("next") or url_for("main.index")
            return redirect(nxt)
        return render_template("login.html", error="Invalid email or password")
    return render_template("login.html")


@main_bp.route("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))


# ─── Public Pages ─────────────────────────────────────────

@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/lessons")
def lessons():
    data = load_json("lessons.json")
    return render_template("lessons.html", lessons=data["lessons"])


@main_bp.route("/lessons/<int:lesson_id>")
def lesson(lesson_id):
    data = load_json("lessons.json")
    for l in data["lessons"]:
        if l["id"] == lesson_id:
            return render_template("lesson.html", lesson=l)
    return redirect(url_for("main.lessons"))


@main_bp.route("/quiz")
def quiz():
    db = get_db()
    uid = session.get("user_id")
    if uid:
        scores = db.execute(
            "SELECT lesson_id, MAX(score) as best, total FROM quiz_scores WHERE user_id=? GROUP BY lesson_id",
            (uid,),
        ).fetchall()
    else:
        scores = []
    db.close()
    sd = {s["lesson_id"]: {"best": s["best"], "total": s["total"]} for s in scores}
    data = load_json("lessons.json")
    return render_template("quiz.html", lessons=data["lessons"], scores=sd)


@main_bp.route("/api/quiz/<int:lesson_id>/submit", methods=["POST"])
def submit_quiz(lesson_id):
    data = load_json("lessons.json")
    ld = next((l for l in data["lessons"] if l["id"] == lesson_id), None)
    if not ld:
        return jsonify({"error": "not found"}), 404
    answers = request.json.get("answers", {})
    score = sum(
        1 for q in ld.get("quiz", [])
        if answers.get(str(q["id"]), "").strip().lower() == q["answer"].strip().lower()
    )
    db = get_db()
    uid = session.get("user_id")
    if uid:
        db.execute("INSERT INTO quiz_scores (user_id, lesson_id, score, total) VALUES (?, ?, ?, ?)",
                   (uid, lesson_id, score, len(ld["quiz"])))
        db.commit()
        log_activity(uid, "quiz_completed", f"lesson={lesson_id} score={score}/{len(ld['quiz'])}")
    db.close()
    return jsonify({"score": score, "total": len(ld["quiz"])})


# ─── Scenarios (interactive) ──────────────────────────────

@main_bp.route("/scenarios")
def scenarios():
    data = load_json("scenarios.json")
    return render_template("scenarios.html", scenarios=data["scenarios"])


@main_bp.route("/scenarios/<int:sid>")
def scenario(sid):
    data = load_json("scenarios.json")
    s = next((s for s in data["scenarios"] if s["id"] == sid), None)
    if not s:
        return redirect(url_for("main.scenarios"))
    return render_template("scenario.html", scenario=s)


@main_bp.route("/api/scenarios/<int:sid>/step/<step_id>")
def scenario_step(sid, step_id):
    data = load_json("scenarios.json")
    s = next((s for s in data["scenarios"] if s["id"] == sid), None)
    if not s:
        return jsonify({"error": "not found"}), 404
    step = next((st for st in s["steps"] if st["id"] == step_id), None)
    if not step:
        return jsonify({"error": "step not found"}), 404
    return jsonify(step)


# ─── Report ───────────────────────────────────────────────

@main_bp.route("/report", methods=["GET"])
def report():
    prefilled = {}
    for k in ("url", "platform", "category"):
        if request.args.get(k):
            prefilled[k] = request.args[k]
    return render_template("report.html", prefilled=prefilled)


@main_bp.route("/api/report", methods=["POST"])
def submit_report():
    data = request.json
    uid = session.get("user_id")
    db = get_db()
    db.execute(
        "INSERT INTO reports (user_id, platform, profile_url, description, category, severity, reporter_email) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, data.get("platform", ""), data.get("profile_url", ""),
         data.get("description", ""), data.get("category", "other"),
         data.get("severity", "medium"), data.get("email", "")),
    )
    db.commit()
    db.close()
    if uid:
        log_activity(uid, "report_submitted", f"platform={data.get('platform')} url={data.get('profile_url')}")
    return jsonify({
        "status": "submitted",
        "message": "Report recorded. Also submit to NCMEC at https://report.cybertrip.org",
    })


# ─── Report Management ────────────────────────────────────

@main_bp.route("/reports")
@login_required
def list_reports():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM reports WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    db.close()
    return render_template("reports.html", reports=rows)


# ─── Dashboard ────────────────────────────────────────────

@main_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/parent")
def parent_dashboard():
    return render_template("parent.html")


@main_bp.route("/api/dashboard/stats")
def dashboard_stats():
    db = get_db()
    uid = session.get("user_id")
    out = {}
    if uid:
        r = db.execute("SELECT COUNT(*) FROM reports WHERE user_id=?", (uid,)).fetchone()[0]
        q = db.execute("SELECT COUNT(DISTINCT lesson_id) FROM quiz_scores WHERE user_id=?", (uid,)).fetchone()[0]
        a = db.execute("SELECT COUNT(*) FROM activity_log WHERE user_id=?", (uid,)).fetchone()[0]
        out = {"reports": r, "quiz_completed": q, "activities": a}
    db.close()
    return jsonify(out)


@main_bp.route("/api/dashboard/settings", methods=["GET", "POST"])
@login_required
def dashboard_settings():
    uid = session["user_id"]
    db = get_db()
    if request.method == "POST":
        data = request.json
        for key, value in data.items():
            db.execute(
                "INSERT INTO dashboard_settings (user_id, setting_key, setting_value) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value=excluded.setting_value",
                (uid, key, str(value)),
            )
        db.commit()
        db.close()
        return jsonify({"status": "ok"})
    rows = db.execute(
        "SELECT setting_key, setting_value FROM dashboard_settings WHERE user_id=?",
        (uid,),
    ).fetchall()
    db.close()
    return jsonify({r["setting_key"]: r["setting_value"] for r in rows})


@main_bp.route("/api/parent/public")
def parent_public():
    db = get_db()
    uid = session.get("user_id")
    if not uid:
        demo = db.execute("SELECT id FROM users WHERE email='demo@safenet.local'").fetchone()
        uid = demo["id"] if demo else None
    out = {"reports": 0, "quiz_completed": 0, "score": 0}
    if uid:
        r = db.execute("SELECT COUNT(*) FROM reports WHERE user_id=?", (uid,)).fetchone()[0]
        q = db.execute("SELECT COUNT(DISTINCT lesson_id) FROM quiz_scores WHERE user_id=?", (uid,)).fetchone()[0]
        settings_rows = db.execute(
            "SELECT setting_key, setting_value FROM dashboard_settings WHERE user_id=?", (uid,)
        ).fetchall()
        out = {"reports": r, "quiz_completed": q}
        checked = 0
        for row in settings_rows:
            if row["setting_value"] == "true":
                checked += 1
        out["score"] = round((checked / 6) * 100) if settings_rows else 0
        out["settings"] = {r["setting_key"]: r["setting_value"] for r in settings_rows}
    db.close()
    return jsonify(out)


# ─── Safety Plan ──────────────────────────────────────────

@main_bp.route("/safety-plan")
@login_required
def safety_plan():
    db = get_db()
    plan = db.execute(
        "SELECT * FROM safety_plans WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
        (session["user_id"],),
    ).fetchone()
    db.close()
    data = json.loads(plan["plan_data"]) if plan else {}
    return render_template("safety_plan.html", plan=data)


@main_bp.route("/api/safety-plan", methods=["POST"])
@login_required
def save_safety_plan():
    uid = session["user_id"]
    data = request.json
    db = get_db()
    existing = db.execute(
        "SELECT id FROM safety_plans WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
        (uid,),
    ).fetchone()
    if existing:
        db.execute("UPDATE safety_plans SET plan_data=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (json.dumps(data), existing["id"]))
    else:
        db.execute("INSERT INTO safety_plans (user_id, plan_data) VALUES (?, ?)",
                   (uid, json.dumps(data)))
    db.commit()
    db.close()
    log_activity(uid, "safety_plan_saved")
    return jsonify({"status": "ok"})


@main_bp.route("/api/safety-plan/export")
@login_required
def export_safety_plan():
    db = get_db()
    plan = db.execute(
        "SELECT * FROM safety_plans WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",
        (session["user_id"],),
    ).fetchone()
    db.close()
    data = json.loads(plan["plan_data"]) if plan else {}
    lines = ["FAMILY SAFETY PLAN", "=" * 40, ""]
    for k, v in data.items():
        lines.append(f"{k.replace('_', ' ').title()}: {v}")
    resp = make_response("\n".join(lines))
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=safety_plan.txt"
    return resp


# ─── Activity Log ─────────────────────────────────────────

@main_bp.route("/activity")
@login_required
def activity():
    return render_template("activity.html")


@main_bp.route("/api/activity")
@login_required
def get_activity():
    db = get_db()
    rows = db.execute(
        "SELECT action, details, created_at FROM activity_log WHERE user_id=? ORDER BY created_at DESC LIMIT 100",
        (session["user_id"],),
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ─── User Settings ───────────────────────────────────────

@main_bp.route("/settings")
@login_required
def user_settings():
    db = get_db()
    user = db.execute("SELECT id, email, name, created_at FROM users WHERE id=?", (session["user_id"],)).fetchone()
    keys = db.execute("SELECT id, key, name, created_at FROM api_keys WHERE user_id=?", (session["user_id"],)).fetchall()
    db.close()
    return render_template("settings.html", user=user, api_keys=keys)


@main_bp.route("/api/settings/profile", methods=["POST"])
@login_required
def update_profile():
    data = request.json
    db = get_db()
    db.execute("UPDATE users SET name=? WHERE id=?", (data.get("name", session["user_name"]), session["user_id"]))
    db.commit()
    db.close()
    session["user_name"] = data.get("name", session["user_name"])
    return jsonify({"status": "ok"})


@main_bp.route("/api/settings/password", methods=["POST"])
@login_required
def change_password():
    data = request.json
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not check_password_hash(user["password_hash"], data.get("current", "")):
        db.close()
        return jsonify({"error": "Current password incorrect"}), 400
    db.execute("UPDATE users SET password_hash=? WHERE id=?",
               (generate_password_hash(data["new"]), session["user_id"]))
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


@main_bp.route("/api/settings/api-key", methods=["POST"])
@login_required
def create_api_key():
    key = "sn_" + secrets.token_hex(24)
    db = get_db()
    db.execute("INSERT INTO api_keys (user_id, key, name) VALUES (?, ?, ?)",
               (session["user_id"], key, request.json.get("name", "OSINT Tool")))
    db.commit()
    db.close()
    return jsonify({"key": key})


@main_bp.route("/api/settings/api-key/<int:kid>", methods=["DELETE"])
@login_required
def delete_api_key(kid):
    db = get_db()
    db.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (kid, session["user_id"]))
    db.commit()
    db.close()
    return jsonify({"status": "deleted"})


# ─── OSINT API Endpoint ──────────────────────────────────

@main_bp.route("/api/osint/submit", methods=["POST"])
def osint_submit():
    data = request.json
    auth = request.headers.get("Authorization", "").replace("Bearer ", "")
    if auth:
        db = get_db()
        key = db.execute("SELECT user_id FROM api_keys WHERE key=?", (auth,)).fetchone()
        db.close()
        if not key:
            return jsonify({"error": "invalid api key"}), 403
        uid = key["user_id"]
    else:
        uid = session.get("user_id")
    db = get_db()
    for account in data.get("accounts", []):
        db.execute(
            "INSERT INTO reports (user_id, platform, profile_url, description, category, severity) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uid, account.get("platform", "unknown"),
             account.get("url", ""),
             f"OSINT scan for '{data.get('username', 'unknown')}' — {account.get('platform', '')}",
             "osint_scan", "info"),
        )
    db.commit()
    db.close()
    return jsonify({"status": "submitted", "count": len(data.get("accounts", []))})


# ─── Contact / Resources ─────────────────────────────────

@main_bp.route("/contact")
def contact():
    return render_template("contact.html")


@main_bp.route("/resources")
def resources():
    return render_template("resources.html")


# ─── Search ───────────────────────────────────────────────

@main_bp.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()
    if not q:
        return render_template("search.html", results=[], query="")
    data = load_json("lessons.json")
    results = []
    for l in data["lessons"]:
        match = q in l["title"].lower() or q in l["summary"].lower()
        if not match:
            match = any(q in s["heading"].lower() or q in s["body"].lower() for s in l.get("sections", []))
        if match:
            results.append({"type": "lesson", "id": l["id"], "title": l["title"], "summary": l["summary"]})
    return render_template("search.html", results=results, query=q)


# ─── API Lessons ─────────────────────────────────────────

@main_bp.route("/api/lessons")
def api_lessons():
    return jsonify(load_json("lessons.json"))


# ─── Auto-Update ─────────────────────────────────────────

@main_bp.route("/api/update/status")
def update_status():
    info = updater.get_local_version()
    return jsonify({
        "current_version": info.get("version", "0.0.0"),
        "update_available": UPDATE_STATUS["available"],
        "update_version": UPDATE_STATUS["version"],
        "checking": UPDATE_STATUS["checking"],
        "error": UPDATE_STATUS["error"],
    })


@main_bp.route("/api/update/check")
def update_check():
    if UPDATE_STATUS["checking"]:
        return jsonify({"status": "already_checking"})
    UPDATE_STATUS["checking"] = True
    UPDATE_STATUS["error"] = ""

    def check():
        try:
            update = updater.check_for_update()
            if update:
                UPDATE_STATUS["available"] = True
                UPDATE_STATUS["version"] = update["version"]
            else:
                UPDATE_STATUS["available"] = False
                UPDATE_STATUS["version"] = ""
        except Exception as e:
            UPDATE_STATUS["error"] = str(e)
        finally:
            UPDATE_STATUS["checking"] = False

    threading.Thread(target=check, daemon=True).start()
    return jsonify({"status": "checking"})


@main_bp.route("/api/update/apply")
def update_apply():
    if UPDATE_STATUS["checking"]:
        return jsonify({"status": "busy", "message": "Already checking for updates."})
    if not UPDATE_STATUS["available"]:
        return jsonify({"status": "none", "message": "No update available. Check first."})

    UPDATE_STATUS["checking"] = True
    UPDATE_STATUS["error"] = ""

    def apply():
        try:
            update = updater.check_for_update()
            if update and update.get("download_url"):
                import tempfile, zipfile, shutil, subprocess
                temp_dir = tempfile.mkdtemp(prefix="safenet_dl_")
                zip_path = updater.download_update(update["download_url"], temp_dir)
                if zip_path:
                    extract_dir = os.path.join(temp_dir, "_extracted")
                    os.makedirs(extract_dir, exist_ok=True)
                    with zipfile.ZipFile(zip_path, "r") as z:
                        z.extractall(extract_dir)
                    extracted = os.listdir(extract_dir)
                    if len(extracted) == 1 and os.path.isdir(os.path.join(extract_dir, extracted[0])):
                        extract_dir = os.path.join(extract_dir, extracted[0])
                    update_dir = os.path.join(BASE_DIR, "_update_new")
                    if os.path.exists(update_dir):
                        shutil.rmtree(update_dir)
                    os.rename(extract_dir, update_dir)
                    updater.set_local_version(update["version"])
                    UPDATE_STATUS["available"] = False
                    runner = os.path.join(BASE_DIR, "update_runner.bat")
                    if os.path.exists(runner):
                        subprocess.Popen([runner], cwd=BASE_DIR)
                    else:
                        subprocess.Popen(["cmd", "/c", "timeout", "/t", "3", "&",
                                          "start", "SafeNet.exe"], cwd=BASE_DIR)
                    os._exit(0)
        except Exception as e:
            UPDATE_STATUS["error"] = str(e)
        finally:
            UPDATE_STATUS["checking"] = False

    threading.Thread(target=apply, daemon=True).start()
    return jsonify({"status": "applying", "message": "Update downloaded. Restarting..."})


# ─── Sale / Pricing Page ─────────────────────────────────

@main_bp.route("/get-safenet")
def sale_page():
    return render_template("sale.html")


@main_bp.route("/download")
def download_exe():
    exe_path = os.path.join(BASE_DIR, "SafeNet.exe")
    if os.path.exists(exe_path):
        from flask import send_file
        return send_file(exe_path, as_attachment=True, download_name="SafeNet.exe")
    return "SafeNet.exe not found. Please run package.ps1 first.", 404


@main_bp.route("/api/donate", methods=["POST"])
def donate():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO donations (user_id, name, email, amount, message) VALUES (?, ?, ?, ?, ?)",
        (session.get("user_id"), data.get("name", ""), data.get("email", ""),
         data.get("amount"), data.get("message", "")),
    )
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


@main_bp.route("/api/analytics/track", methods=["POST"])
def track_event():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO analytics_events (event_type, source) VALUES (?, ?)",
        (data.get("event", "page_view"), data.get("source", "direct")),
    )
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


# ─── Admin Marketing ──────────────────────────────────────

AD_TEMPLATES = {
    "facebook": {
        "intro": "🛡️ Worried about your child's online safety?\n\nSafeNet is the free tool that helps parents teach, monitor, and respond to online threats — no tech skills needed.\n\n✅ 10 interactive lessons for kids\n✅ One-click reporting tool\n✅ Family safety plan generator\n✅ Works right on your computer\n\nDownload free → pay what you can.\n\n[Link] #OnlineSafety #Parenting #SafeNet",
        "privacy": "🔒 Your child's privacy matters more than ever.\n\nSafeNet helps you check account privacy settings, scan for exposed usernames across 25+ platforms, and build healthy digital habits as a family.\n\nAll free. No subscriptions. No data collection.\n\n[Link] #Privacy #Parenting #SafeNet",
        "anti-bullying": "💔 Is your child being cyberbullied? You don't have to face it alone.\n\nSafeNet gives parents the tools to document incidents, report to authorities, and teach kids how to respond — all in one private, free app.\n\nGet SafeNet today → [Link]\n\n#Cyberbullying #Parenting #SafeNet",
        "default": "🛡️ Keep your family safe online — for free.\n\nSafeNet gives you lessons, reporting tools, safety plans, and a parent dashboard. No tech skills required. Pay what you can.\n\nDownload now → [Link]"
    },
    "twitter": {
        "intro": "Protect your family online with SafeNet 🛡️\n\nFree tools for parents:\n📚 10 lessons\n🚨 One-click reporting\n📊 Parent dashboard\n📝 Safety plan generator\n\nPay what you can, if you can. Download free → [Link]",
        "privacy": "Your kid's privacy settings OK? SafeNet checks 25+ platforms for exposed accounts. Free for every parent. No catch. [Link] #Privacy #Parenting",
        "anti-bullying": "Spot cyberbullying before it's too late. SafeNet helps parents document and report incidents. Free. Private. Effective. [Link] #Cyberbullying",
        "default": "Online safety for families — made simple. SafeNet is free. No tech skills needed. [Link]"
    },
    "linkedin": {
        "intro": "Help families in your community stay safe online.\n\nSafeNet is a free, parent-friendly toolkit that provides:\n• Interactive safety lessons for children\n• One-click reporting to authorities\n• Family safety plan templates\n• Parent dashboard with real-time stats\n\nBuilt for non-technical parents. Zero cost. Pay-what-you-can donations keep us running.\n\nLearn more → [Link]\n\n#OnlineSafety #DigitalParenting #CommunityImpact",
        "default": "SafeNet: free online safety tools for families. Lessons, reporting, safety plans — all in one place. No technical skills required. [Link]"
    },
    "email": {
        "intro": "Subject: Keep your family safe online — for free\n\nHi [Name],\n\nI wanted to share SafeNet with you — a completely free tool that helps parents teach kids about online safety, report concerns, and create a family safety plan.\n\nIt's designed for non-technical parents (no setup headaches, no confusing jargon).\n\nHere's what you get:\n• 10 interactive safety lessons with quizzes\n• One-click reporting to NCMEC / law enforcement\n• A family safety plan generator\n• A parent dashboard showing your safety score\n• A Chrome extension for quick reporting\n\nAnd it's all free. If you find it useful, you can throw a few dollars our way — but there's no pressure.\n\nDownload here: [Link]\n\nStay safe,\n[Your Name]",
        "default": "Subject: Free online safety tool for parents\n\nHi [Name],\n\nSafeNet is a free toolkit for parents who want to protect their kids online but don't know where to start. Lessons, reporting, checklists — all in one place. No tech skills needed.\n\nDownload: [Link]"
    },
    "flyer": {
        "intro": "🛡️ SAFENET\nProtect Your Family Online\n\n✓ 10 free safety lessons\n✓ One-click reporting tool\n✓ Family safety plan\n✓ Parent dashboard\n✓ Chrome extension\n\n💵 Pay What You Can • Always Free\n\nDownload at: [Link]\n\n#OnlineSafety #Parenting",
        "default": "SAFENET — Free Online Safety for Families\nLessons • Reporting • Safety Plans • Dashboard\nDownload: [Link]"
    },
    "google": {
        "intro": "SafeNet - Free Online Safety for Families\nKeep your family safe online with free lessons, reporting tools, and safety plans. No tech skills needed. Download today.\n\n[Link]",
        "default": "SafeNet: Free Parental Safety Toolkit\nInteractive lessons, reporting, and safety plans for families. Pay what you can.\n\n[Link]"
    }
}

SOCIAL_POSTS = {
    "intro": "🛡️ Meet SafeNet — the free toolkit that helps parents protect their kids online.\n\n✅ 10 safety lessons with quizzes\n✅ One-click reporting to authorities\n✅ Family safety plan builder\n✅ Parent dashboard with safety score\n✅ Chrome extension included\n\nNo tech skills needed. No subscriptions. Just real protection.\n\nDownload free → [Link] #SafeNet #OnlineSafety #Parenting",
    "tip": "💡 Online safety tip: Review your child's friend list and followers each month. Ask who each person is.\n\nSafeNet helps you stay on top of digital safety with checklists, tracking, and reminders. Get it free → [Link] #ParentingTip #OnlineSafety",
    "testimonial": '\u201cI\'m not tech-savvy at all, but I had SafeNet running in 5 minutes. My kids actually enjoyed the lessons.\u201d — Maria K.\n\nJoin thousands of parents using SafeNet to protect their families. Free → [Link] #SafeNet #Parenting',
    "feature": "📊 Did you know SafeNet has a Family Dashboard?\n\nSee your safety score at a glance. Track completed lessons and reports. Check off safety tasks as you go.\n\nAll free. All private. Get it → [Link] #SafeNet #Parenting",
    "callout": "Every child deserves a safe online experience. Every parent deserves tools that actually work.\n\nSafeNet is free. No trials. No subscriptions. No hidden fees.\n\nDownload → [Link] #SafeNet #OnlineSafety"
}

EMAIL_TEMPLATES = {
    "school": "Subject: Free online safety program for [Recipient]\n\nHi [Name],\n\nI'm reaching out to share SafeNet — a free, parent-friendly online safety toolkit designed for families.\n\nSafeNet includes:\n• 10 interactive safety lessons for kids (covering privacy, cyberbullying, phishing, and more)\n• A one-click reporting tool for flagging harmful content to NCMEC/law enforcement\n• A family safety plan generator\n• A parent dashboard with safety scoring\n• A Chrome extension for quick browser-based reporting\n\nIt's completely free, runs on any Windows computer, and requires no technical skills to use.\n\nI'd love to help you share this with your community. Would you be open to a quick chat?\n\nBest,\n[Your Name]",
    "community": "Subject: Helping families stay safe online\n\nHi everyone,\n\nI wanted to share SafeNet with your group — it's a free toolkit I've been working on that helps parents teach kids about online safety.\n\nIt's built for non-technical parents (no command line, no complicated setup). Just download, double-click, and start protecting your family.\n\nFeatures:\n• Interactive lessons for kids aged 8+\n• Reporting tools for harmful content\n• Family safety plan template\n• Parent dashboard with safety score\n\nIt's free forever. If you find it useful, a small donation helps us keep going.\n\nCheck it out: [Link]\n\nStay safe,\n[Your Name]",
    "press": "Subject: New free tool helps parents combat online threats\n\n[Date]\n\nFOR IMMEDIATE RELEASE\n\nSafeNet Launches Free Online Safety Toolkit for Parents\n\n[City, State] — SafeNet, a new free software application, launched today to help parents protect their children from online threats. The toolkit includes interactive safety lessons, a one-click reporting tool for flagging harmful content, a family safety plan generator, and a parent dashboard — all designed for non-technical users.\n\n\"Many parents feel overwhelmed by online safety,\" said [Your Name], creator of SafeNet. \"We built SafeNet to be the tool we wish we'd had — something that actually works, is completely free, and doesn't require a computer science degree.\"\n\nSafeNet runs on Windows and is available as a standalone download at [Link].\n\n###\n\nFor more information, visit [Link] or contact [Your Email].",
    "sponsor": "Subject: Sponsor SafeNet — help protect families online\n\nHi [Name],\n\nI'm reaching out to ask you to consider sponsoring SafeNet — a free online safety toolkit for parents.\n\nSafeNet provides:\n• Interactive safety lessons for children\n• Reporting tools for harmful online content\n• Family safety plans\n• Parent dashboards and checklists\n\nThe tool is completely free for families. We use a pay-what-you-can model to keep it accessible.\n\nSponsorship would help us:\n• Reach more families through targeted advertising\n• Develop new lessons and features\n• Maintain servers and infrastructure\n\nI'd love to discuss how we could work together.\n\nBest,\n[Your Name]"
}


def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            return redirect(url_for("main.login", next=request.path))
        db = get_db()
        user = db.execute("SELECT is_admin FROM users WHERE id=?", (session["user_id"],)).fetchone()
        db.close()
        if not user or not user["is_admin"]:
            return render_template("base.html"), 403
        return f(*a, **kw)
    return wrapper


@main_bp.route("/admin/marketing")
@admin_required
def admin_marketing():
    return render_template("admin_marketing.html")


@main_bp.route("/api/admin/analytics")
@admin_required
def admin_analytics():
    db = get_db()
    views = db.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type='page_view'").fetchone()[0]
    downloads = db.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type='download'").fetchone()[0]
    donations = db.execute("SELECT COUNT(*) FROM donations").fetchone()[0]
    campaigns = db.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    reports = db.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    db.close()
    return jsonify({
        "total_views": views, "total_downloads": downloads,
        "total_donations": donations, "total_campaigns": campaigns,
        "total_reports": reports, "total_users": users,
    })


@main_bp.route("/api/admin/generate-ad", methods=["POST"])
@admin_required
def generate_ad():
    data = request.json
    platform = data.get("platform", "facebook")
    angle = (data.get("angle", "") or "").lower()
    templates = AD_TEMPLATES.get(platform, AD_TEMPLATES["facebook"])
    keys = ["intro", "privacy", "anti-bullying"]
    chosen = templates.get("default", "")
    for key in keys:
        if key in angle:
            chosen = templates.get(key)
            break
    if not chosen:
        chosen = templates.get("intro", templates.get("default", ""))
    return jsonify({"content": chosen, "platform": platform})


@main_bp.route("/api/admin/generate-email", methods=["POST"])
@admin_required
def generate_email():
    data = request.json
    etype = data.get("type", "school")
    recipient = data.get("recipient", "there")
    template = EMAIL_TEMPLATES.get(etype, EMAIL_TEMPLATES["school"])
    template = template.replace("[Recipient]", recipient).replace("[Name]", recipient)
    return jsonify({"content": template, "type": etype})


@main_bp.route("/api/admin/generate-post", methods=["POST"])
@admin_required
def generate_post():
    data = request.json
    ptype = data.get("type", "intro")
    content = SOCIAL_POSTS.get(ptype, SOCIAL_POSTS["intro"])
    return jsonify({"content": content, "type": ptype})


@main_bp.route("/api/admin/create-campaign", methods=["POST"])
@admin_required
def create_campaign():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO campaigns (name, platform, content) VALUES (?, ?, ?)",
        (data.get("name", ""), data.get("platform", ""), data.get("content", "")),
    )
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


@main_bp.route("/api/admin/campaigns")
@admin_required
def list_campaigns():
    db = get_db()
    rows = db.execute("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 50").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@main_bp.route("/api/admin/sources")
@admin_required
def list_sources():
    db = get_db()
    rows = db.execute(
        "SELECT source, COUNT(*) as count FROM analytics_events WHERE source != '' GROUP BY source ORDER BY count DESC"
    ).fetchall()
    db.close()
    return jsonify([{"source": r["source"] or "direct", "count": r["count"]} for r in rows])


@main_bp.route("/api/admin/templates")
@admin_required
def list_templates():
    db = get_db()
    rows = db.execute("SELECT * FROM ad_templates ORDER BY created_at DESC LIMIT 20").fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@main_bp.route("/api/admin/save-template", methods=["POST"])
@admin_required
def save_template():
    data = request.json
    db = get_db()
    db.execute(
        "INSERT INTO ad_templates (name, platform, headline, body, cta) VALUES (?, ?, ?, ?, ?)",
        (data.get("name", ""), data.get("platform", ""),
         data.get("headline", ""), data.get("body", ""), data.get("cta", "")),
    )
    db.commit()
    db.close()
    return jsonify({"status": "ok"})


# ─── Demo login shortcut ─────────────────────────────────

@main_bp.route("/auth/demo")
def demo_login():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email='demo@safenet.local'").fetchone()
    db.close()
    if user:
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["is_admin"] = bool(user["is_admin"])
        log_activity(user["id"], "demo_login")
    return redirect(url_for("main.index"))
