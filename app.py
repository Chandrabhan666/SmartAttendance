from functools import wraps
from flask import Flask, render_template, request, redirect, session, send_from_directory, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import datetime
import base64
import json
import os
import random
import requests
import numpy as np

try:
    import cv2
except Exception:
    cv2 = None

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "college_secret_key")

raw_db_url = os.environ.get("DATABASE_URL", "sqlite:///attendance.db")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

if raw_db_url.startswith("postgresql://") and "sslmode=" not in raw_db_url:
    sep = "&" if "?" in raw_db_url else "?"
    raw_db_url = f"{raw_db_url}{sep}sslmode=require"

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "connect_args": {"connect_timeout": 10},
}

AUTH_FILE = "auth_users.json"
STUDENT_FILE = "student_data.json"
ANNOUNCEMENT_FILE = "announcements.json"
SYLLABUS_FILE = "syllabus.json"

os.makedirs("uploads", exist_ok=True)
os.makedirs("notes", exist_ok=True)
os.makedirs("model", exist_ok=True)

db = SQLAlchemy(app)


class Student(db.Model):
    __tablename__ = "students"
    student_id = db.Column(db.String(40), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    branch = db.Column(db.String(80), nullable=True)
    year = db.Column(db.String(50), nullable=True)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    linked_student_id = db.Column(db.String(40), db.ForeignKey("students.student_id"), nullable=True)


class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.String(40), db.ForeignKey("students.student_id"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False, index=True)
    time = db.Column(db.String(8), nullable=False)


class Announcement(db.Model):
    __tablename__ = "announcements"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(10), nullable=False)


class Resource(db.Model):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kind = db.Column(db.String(30), nullable=False, index=True)  # notes or syllabus
    subject = db.Column(db.String(200), nullable=True)
    topic = db.Column(db.String(200), nullable=True)
    file_name = db.Column(db.String(300), nullable=False)
    storage_path = db.Column(db.String(500), nullable=False)
    file_url = db.Column(db.String(1000), nullable=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)


DEFAULT_AUTH_USERS = {
    "admins": {
        "admin": {
            "password": "0010",
            "name": "System Admin"
        }
    },
    "teachers": {
        "teacher1": {
            "password": "teach123",
            "name": "Default Teacher"
        }
    },
    "parents": {},
    "students": {}
}


def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def current_role():
    return session.get("role")


def require_roles(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if current_role() not in roles:
                return redirect("/login")
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def seed_data():
    students_data = load_json(STUDENT_FILE, {})

    for sid, info in students_data.items():
        if not Student.query.filter_by(student_id=sid).first():
            db.session.add(
                Student(
                    student_id=sid,
                    name=info.get("name", "Student"),
                    branch=info.get("branch", ""),
                    year=info.get("year", ""),
                )
            )

    db.session.commit()

    auth = load_json(AUTH_FILE, DEFAULT_AUTH_USERS)

    def add_user_if_missing(username, role, password, name, linked_student_id=None):
        if not User.query.filter_by(username=username, role=role, linked_student_id=linked_student_id).first():
            db.session.add(
                User(
                    username=username,
                    role=role,
                    password=password,
                    name=name,
                    linked_student_id=linked_student_id,
                )
            )

    for username, details in auth.get("admins", {}).items():
        add_user_if_missing(username, "admin", details.get("password", ""), details.get("name", username))

    for username, details in auth.get("teachers", {}).items():
        add_user_if_missing(username, "teacher", details.get("password", ""), details.get("name", username))

    student_accounts = auth.get("students", {})
    for sid in students_data.keys():
        details = student_accounts.get(sid, {})
        add_user_if_missing(
            sid,
            "student",
            details.get("password", sid[-4:] if len(sid) >= 4 else sid),
            details.get("name", students_data[sid].get("name", sid)),
            sid,
        )

    for username, details in auth.get("parents", {}).items():
        linked_students = details.get("students", [])
        if not linked_students:
            continue
        for sid in linked_students:
            if Student.query.filter_by(student_id=sid).first():
                add_user_if_missing(
                    username,
                    "parent",
                    details.get("password", ""),
                    details.get("name", username),
                    sid,
                )

    db.session.commit()

    if Announcement.query.count() == 0:
        for item in load_json(ANNOUNCEMENT_FILE, []):
            db.session.add(
                Announcement(
                    title=item.get("title", "Untitled"),
                    description=item.get("description", ""),
                    date=item.get("date", str(datetime.date.today())),
                )
            )
        db.session.commit()

    if Resource.query.filter_by(kind="syllabus").count() == 0:
        syllabus = load_json(SYLLABUS_FILE, {})
        for subject, pdf in syllabus.items():
            path = os.path.join("uploads", pdf)
            if os.path.exists(path):
                db.session.add(
                    Resource(
                        kind="syllabus",
                        subject=subject,
                        file_name=pdf,
                        storage_path=pdf,
                        file_url=None,
                    )
                )
        db.session.commit()

    if Resource.query.filter_by(kind="notes").count() == 0 and os.path.exists("notes"):
        for file_name in os.listdir("notes"):
            if file_name.lower().endswith(".pdf"):
                db.session.add(
                    Resource(
                        kind="notes",
                        subject="Notes",
                        topic="",
                        file_name=file_name,
                        storage_path=file_name,
                        file_url=None,
                    )
                )
        db.session.commit()


def init_db():
    with app.app_context():
        try:
            db.create_all()
            seed_data()
        except SQLAlchemyError as exc:
            # Keep web process alive even if DB is temporarily unreachable.
            # This allows Render health checks and manual retry without crash loops.
            app.logger.error("Database init failed at startup: %s", exc)


init_db()


@app.context_processor
def inject_session_data():
    return {
        "session_role": session.get("role"),
        "session_display_name": session.get("display_name"),
        "parent_students": session.get("parent_students", []),
    }


def store_uploaded_file(file_obj, folder):
    file_name = secure_filename(file_obj.filename)
    if not file_name:
        return None, None, None

    content = file_obj.read()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET")

    if supabase_url and service_key and bucket:
        unique_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file_name}"
        storage_path = f"{folder}/{unique_name}"
        endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{storage_path}"

        headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "x-upsert": "true",
            "Content-Type": file_obj.mimetype or "application/pdf",
        }

        response = requests.post(endpoint, headers=headers, data=content, timeout=40)
        if response.status_code in (200, 201):
            public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{storage_path}"
            return file_name, storage_path, public_url

    local_path = os.path.join(folder, file_name)
    with open(local_path, "wb") as f:
        f.write(content)

    return file_name, file_name, None


def get_selected_student_for_view(requested_sid=None):
    role = current_role()

    if role == "student":
        sid = session.get("student")
        student = Student.query.filter_by(student_id=sid).first()
        return sid, student

    if role == "parent":
        parent_students = session.get("parent_students", [])
        sid = requested_sid if requested_sid in parent_students else (parent_students[0] if parent_students else None)
        student = Student.query.filter_by(student_id=sid).first() if sid else None
        return sid, student

    return None, None


@app.route("/")
def home():
    return redirect("/login")


@app.route("/login")
def login_portal():
    return render_template("login_portal.html")


@app.route("/login/student", methods=["GET", "POST"])
def login_student():
    if request.method == "POST":
        sid = request.form["student_id"].strip()
        password = request.form["password"]

        try:
            user = User.query.filter_by(role="student", username=sid).first()
        except SQLAlchemyError:
            return render_template("login_student.html", error="Server busy. Please try again in a few seconds.")

        if user and user.password == password:
            session.clear()
            session["role"] = "student"
            session["student"] = user.linked_student_id
            session["display_name"] = user.name or sid
            return redirect("/student/dashboard")

        return render_template("login_student.html", error="Invalid Student Credentials")

    return render_template("login_student.html")


@app.route("/login/parent", methods=["GET", "POST"])
def login_parent():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        try:
            parent_rows = User.query.filter_by(role="parent", username=username).all()
        except SQLAlchemyError:
            return render_template("login_parent.html", error="Server busy. Please try again in a few seconds.")
        if parent_rows and parent_rows[0].password == password:
            linked_students = [row.linked_student_id for row in parent_rows if row.linked_student_id]

            session.clear()
            session["role"] = "parent"
            session["parent"] = username
            session["display_name"] = parent_rows[0].name or username
            session["parent_students"] = linked_students
            return redirect("/parent/dashboard")

        return render_template("login_parent.html", error="Invalid Parent Credentials")

    return render_template("login_parent.html")


@app.route("/login/teacher", methods=["GET", "POST"])
def login_teacher():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        try:
            user = User.query.filter_by(role="teacher", username=username).first()
        except SQLAlchemyError:
            return render_template("login_teacher.html", error="Server busy. Please try again in a few seconds.")
        if user and user.password == password:
            session.clear()
            session["role"] = "teacher"
            session["teacher"] = username
            session["display_name"] = user.name or username
            return redirect("/teacher/dashboard")

        return render_template("login_teacher.html", error="Invalid Teacher Credentials")

    return render_template("login_teacher.html")


@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        try:
            user = User.query.filter_by(role="admin", username=username).first()
        except SQLAlchemyError:
            return render_template("login_admin.html", error="Server busy. Please try again in a few seconds.")
        if user and user.password == password:
            session.clear()
            session["role"] = "admin"
            session["admin"] = username
            session["display_name"] = user.name or username
            return redirect("/teacher/dashboard")

        return render_template("login_admin.html", error="Invalid Admin Credentials")

    return render_template("login_admin.html")


@app.route("/student/dashboard")
@require_roles("student", "parent")
def student_dashboard():
    requested_sid = request.args.get("student_id")
    sid, student = get_selected_student_for_view(requested_sid)

    if not sid or not student:
        return render_template("dashboard_student.html", no_data=True)

    today = datetime.date.today().strftime("%Y-%m-%d")
    month_key = datetime.date.today().strftime("%Y-%m")

    present_today = Attendance.query.filter_by(student_id=sid, date=today).count()
    total_records = Attendance.query.filter_by(student_id=sid).count()
    this_month_records = Attendance.query.filter(
        Attendance.student_id == sid, Attendance.date.like(f"{month_key}%")
    ).count()
    latest = (
        Attendance.query.filter_by(student_id=sid)
        .order_by(Attendance.date.desc(), Attendance.time.desc())
        .first()
    )

    status = "Present ✅" if present_today else "Absent ❌"

    return render_template(
        "dashboard_student.html",
        student=student,
        selected_student_id=sid,
        today_status=status,
        total_records=total_records,
        this_month_records=this_month_records,
        latest_mark=(latest.date, latest.time) if latest else None,
        no_data=False,
    )


@app.route("/parent/dashboard")
@require_roles("parent")
def parent_dashboard():
    parent_students = session.get("parent_students", [])
    today = datetime.date.today().strftime("%Y-%m-%d")

    child_rows = []
    for sid in parent_students:
        child = Student.query.filter_by(student_id=sid).first()
        if not child:
            continue

        total = Attendance.query.filter_by(student_id=sid).count()
        present_today = Attendance.query.filter_by(student_id=sid, date=today).count()

        child_rows.append(
            {
                "id": sid,
                "name": child.name,
                "branch": child.branch or "-",
                "year": child.year or "-",
                "total": total,
                "today_status": "Present ✅" if present_today else "Absent ❌",
            }
        )

    return render_template("dashboard_parent.html", children=child_rows)


@app.route("/student/attendance")
@require_roles("student", "parent")
def student_attendance():
    requested_sid = request.args.get("student_id")
    sid, student = get_selected_student_for_view(requested_sid)

    if not sid:
        return render_template("student_attendance.html", attendance=[], student=None, selected_student_id=None)

    rows = (
        Attendance.query.filter_by(student_id=sid)
        .order_by(Attendance.date.desc(), Attendance.time.desc())
        .all()
    )
    attendance_rows = [(row.date, row.time) for row in rows]

    return render_template(
        "student_attendance.html",
        attendance=attendance_rows,
        student=student,
        selected_student_id=sid,
    )


@app.route("/routine")
@require_roles("student", "parent")
def routine():
    return render_template("routine.html")


@app.route("/activity")
@require_roles("student", "parent")
def activity():
    return render_template(
        "activity.html",
        activity=random.choice(
            [
                "Revise notes",
                "Practice coding",
                "Read textbook",
                "Watch lecture video",
            ]
        ),
    )


@app.route("/notes")
@require_roles("student", "parent")
def notes():
    resources = Resource.query.filter_by(kind="notes").order_by(Resource.uploaded_at.desc()).all()
    return render_template("notes.html", resources=resources)


@app.route("/announcements")
@require_roles("student", "parent")
def announcements():
    data = Announcement.query.order_by(Announcement.date.desc(), Announcement.id.desc()).all()
    return render_template("announcements.html", announcements=data)


@app.route("/curriculum")
@require_roles("student", "parent")
def curriculum():
    resources = Resource.query.filter_by(kind="syllabus").order_by(Resource.uploaded_at.desc()).all()
    return render_template("curriculum.html", resources=resources)


@app.route("/teacher/dashboard")
@require_roles("teacher", "admin")
def teacher_dashboard():
    total_students = Student.query.count()
    total_records = Attendance.query.count()

    today = datetime.date.today().strftime("%Y-%m-%d")
    today_attendance = db.session.query(Attendance.student_id).filter_by(date=today).distinct().count()
    today_absent = max(total_students - today_attendance, 0)

    recent_rows = (
        Attendance.query.order_by(Attendance.date.desc(), Attendance.time.desc()).limit(10).all()
    )
    recent_records = [(r.student_id, r.date, r.time) for r in recent_rows]
    status_msg = request.args.get("status", "")
    error_msg = request.args.get("error", "")

    return render_template(
        "dashboard_teacher.html",
        total_students=total_students,
        total_records=total_records,
        today_attendance=today_attendance,
        today_absent=today_absent,
        recent_records=recent_records,
        status_msg=status_msg,
        error_msg=error_msg,
    )


@app.route("/mark-attendance")
@require_roles("teacher", "admin")
def mark_attendance():
    # On cloud hosting (Render), server has no physical webcam.
    if os.environ.get("RENDER") == "true":
        return redirect("/teacher/dashboard?error=Cloud server has no camera. Use manual attendance below.")

    if cv2 is None or not os.path.exists("model/face_model.xml"):
        return redirect("/teacher/dashboard?error=Face model not found. Train model locally first.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("model/face_model.xml")

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        return redirect("/teacher/dashboard?error=Camera not available. Check local camera permissions.")

    show_preview = True
    start_time = datetime.datetime.now()
    timeout_seconds = 20

    while True:
        if (datetime.datetime.now() - start_time).total_seconds() > timeout_seconds:
            break

        ret, frame = cam.read()
        if not ret or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            label, _ = recognizer.predict(gray[y: y + h, x: x + w])
            sid = str(label)
            ok, msg = _mark_attendance_once(sid)

            cam.release()
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass
            if ok:
                return redirect(f"/teacher/dashboard?status={msg}")
            return redirect(f"/teacher/dashboard?error={msg}")

        if show_preview:
            try:
                cv2.imshow("Face Attendance", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (13, 27):
                    break
            except cv2.error:
                show_preview = False

    cam.release()
    try:
        cv2.destroyAllWindows()
    except cv2.error:
        pass
    return redirect("/teacher/dashboard")


def _load_face_tools():
    if cv2 is None:
        return None, None, "OpenCV is not available on server."
    if not hasattr(cv2, "face"):
        return None, None, "OpenCV face module is not available."
    if not os.path.exists("model/face_model.xml"):
        return None, None, "Face model not found. Train model locally first."

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("model/face_model.xml")
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return recognizer, face_cascade, None


def _mark_attendance_once(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return False, "Student ID not found."

    today = datetime.date.today().strftime("%Y-%m-%d")
    exists_today = Attendance.query.filter_by(student_id=student_id, date=today).first()
    if exists_today:
        return True, "Attendance already marked for today."

    now = datetime.datetime.now()
    db.session.add(
        Attendance(
            student_id=student_id,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
        )
    )
    db.session.commit()
    return True, "Attendance marked successfully."


@app.route("/teacher/face-attendance")
@require_roles("teacher", "admin")
def teacher_face_attendance():
    is_cloud = os.environ.get("RENDER") == "true"
    return render_template("face_attendance.html", is_cloud=is_cloud)


@app.route("/teacher/face-attendance/verify", methods=["POST"])
@require_roles("teacher", "admin")
def teacher_face_attendance_verify():
    recognizer, face_cascade, err = _load_face_tools()
    if err:
        return jsonify({"ok": False, "message": err}), 400

    payload = request.get_json(silent=True) or {}
    image_data = payload.get("image", "")
    if not image_data or "," not in image_data:
        return jsonify({"ok": False, "message": "Invalid image payload."}), 400

    try:
        encoded = image_data.split(",", 1)[1]
        frame_bytes = base64.b64decode(encoded)
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
    except Exception:
        return jsonify({"ok": False, "message": "Failed to decode image."}), 400

    if frame is None:
        return jsonify({"ok": False, "message": "Empty frame received."}), 400

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) == 0:
        return jsonify({"ok": False, "message": "No face detected. Keep face in frame."}), 200

    best_sid = None
    best_conf = None
    for (x, y, w, h) in faces:
        sid_label, confidence = recognizer.predict(gray[y: y + h, x: x + w])
        sid = str(sid_label)
        if confidence <= 80 and Student.query.filter_by(student_id=sid).first():
            if best_conf is None or confidence < best_conf:
                best_conf = confidence
                best_sid = sid

    if not best_sid:
        return jsonify({"ok": False, "message": "Face not recognized. Try better lighting/angle."}), 200

    ok, msg = _mark_attendance_once(best_sid)
    return jsonify(
        {
            "ok": ok,
            "message": msg,
            "student_id": best_sid,
            "confidence": round(float(best_conf), 2) if best_conf is not None else None,
        }
    )


@app.route("/mark-attendance-manual", methods=["POST"])
@require_roles("teacher", "admin")
def mark_attendance_manual():
    sid = request.form.get("student_id", "").strip()
    if not sid:
        return redirect("/teacher/dashboard?error=Please enter a student ID.")
    ok, msg = _mark_attendance_once(sid)
    if ok:
        return redirect(f"/teacher/dashboard?status={msg}")
    return redirect(f"/teacher/dashboard?error={msg}")


@app.route("/teacher/monthly-graph")
@require_roles("teacher", "admin")
def teacher_monthly_graph():
    rows = Attendance.query.all()
    months = {}

    for row in rows:
        m = row.date[:7]
        months[m] = months.get(m, 0) + 1

    return render_template(
        "monthly_graph.html",
        bar_labels=list(months.keys()),
        bar_values=list(months.values()),
    )


@app.route("/upload-syllabus", methods=["GET", "POST"])
@require_roles("teacher", "admin")
def upload_syllabus():
    if request.method == "POST":
        sub = request.form["subject"]
        file = request.files["file"]

        file_name, storage_path, file_url = store_uploaded_file(file, "uploads")
        if not file_name:
            return "Invalid file", 400

        db.session.add(
            Resource(
                kind="syllabus",
                subject=sub,
                topic="",
                file_name=file_name,
                storage_path=storage_path,
                file_url=file_url,
            )
        )
        db.session.commit()
        return redirect("/curriculum")

    return render_template("upload_syllabus.html")


@app.route("/teacher/upload-notes", methods=["GET", "POST"])
@require_roles("teacher", "admin")
def upload_notes():
    if request.method == "POST":
        subject = request.form.get("subject", "Notes")
        topic = request.form.get("topic", "")
        file = request.files["file"]

        file_name, storage_path, file_url = store_uploaded_file(file, "notes")
        if not file_name:
            return "Invalid file", 400

        db.session.add(
            Resource(
                kind="notes",
                subject=subject,
                topic=topic,
                file_name=file_name,
                storage_path=storage_path,
                file_url=file_url,
            )
        )
        db.session.commit()

        return redirect("/teacher/dashboard")
    return render_template("upload_notes.html")


@app.route("/teacher/add-announcement", methods=["GET", "POST"])
@require_roles("teacher", "admin")
def add_announcement():
    if request.method == "POST":
        db.session.add(
            Announcement(
                title=request.form["title"],
                description=request.form["description"],
                date=str(datetime.date.today()),
            )
        )
        db.session.commit()
        return redirect("/teacher/dashboard")
    return render_template("add_announcement.html")


@app.route("/resource/<int:resource_id>")
@require_roles("student", "parent", "teacher", "admin")
def view_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)

    if resource.file_url:
        return redirect(resource.file_url)

    if resource.kind == "syllabus":
        base_folder = "uploads"
    else:
        base_folder = "notes"

    local_name = os.path.basename(resource.storage_path)
    if os.path.exists(os.path.join(base_folder, local_name)):
        return send_from_directory(base_folder, local_name)

    return "File not found", 404


@app.route("/view-pdf/<name>")
@require_roles("student", "parent", "teacher", "admin")
def view_pdf(name):
    safe_name = os.path.basename(name)

    if os.path.exists("uploads/" + safe_name):
        return send_from_directory("uploads", safe_name)
    if os.path.exists("notes/" + safe_name):
        return send_from_directory("notes", safe_name)

    resource = Resource.query.filter_by(file_name=safe_name).order_by(Resource.id.desc()).first()
    if resource:
        return redirect(url_for("view_resource", resource_id=resource.id))

    return "File not found", 404


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)
