# SmartAttendance (Cloud + Offline Hybrid)

SmartAttendance is a role-based academic portal with attendance tracking (manual + face), notes/syllabus uploads, and announcements.

- Roles: `student`, `parent`, `teacher`, `admin`
- Attendance: manual marking + face recognition
- Hybrid: works on localhost (offline) and cloud (online)

## 1. Features

- Student dashboard: attendance status, records, notes, syllabus, announcements
- Parent dashboard: view linked student attendance
- Teacher/Admin dashboard:
  - Mark attendance (manual)
  - Face attendance (browser webcam mode)
  - Local webcam mode (OpenCV server-side camera, localhost only)
  - Upload notes/syllabus PDFs
  - Create announcements
- Cloud-ready database and storage (Supabase supported)

## 2. Tech Stack

- Backend: Flask + SQLAlchemy
- Face recognition: OpenCV (LBPH)
- DB: SQLite (local) or Postgres (Supabase)
- Storage: local folders (local) or Supabase Storage (cloud)
- Hosting: Render (recommended), Vercel (serverless option)

## 3. Project Structure

- `app.py` : main Flask app
- `templates/` : UI pages
- `static/` : static assets
- `dataset/` : captured face images (local training)
- `model/face_model.xml` : trained face model (generated locally)
- `uploads/` : syllabus PDFs (local fallback)
- `notes/` : notes PDFs (local fallback)
- `auth_users.json` : demo logins
- `student_data.json` : student directory (name/branch/year + contact)

## 4. Local Setup (Mac/Linux)

### 4.1 Install dependencies

```bash
cd /Users/chandrabhanpatel/Downloads/SmartAttendance
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2 Run the app

```bash
python3 app.py
```

Open:
- `http://127.0.0.1:5000/login`

## 5. Local Setup (Windows)

```bat
cd C:\path\to\SmartAttendance
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:
- `http://127.0.0.1:5000/login`

## 6. Face Recognition (Training + Adding Students)

Face attendance requires a trained model at `model/face_model.xml`.

### 6.1 Capture face images (local machine with webcam)

```bash
cd /Users/chandrabhanpatel/Downloads/SmartAttendance
python3 capture_faces.py
```

Follow prompts to capture images into `dataset/`.

### 6.2 Train model

```bash
python3 train_model.py
```

This generates/updates:
- `model/face_model.xml`

### 6.3 Add student details

Update `student_data.json`:

```json
{
  "12312037": {
    "name": "Rahul Patel",
    "branch": "CSE",
    "year": "3rd Year",
    "email": "rahulpatel152004@gmail.com",
    "phone": "6389759122"
  }
}
```

Update `auth_users.json` to add login credentials for the student/parent as needed.

## 7. Attendance Modes (Offline + Online)

### 7.1 Offline mode (localhost OpenCV camera)

- Teacher/Admin can use the **local webcam mode**.
- This uses `cv2.VideoCapture(0)` and only works on the machine that runs the server.

### 7.2 Online mode (cloud browser webcam)

- Teacher/Admin opens the Face Attendance page.
- Camera opens in the browser using `getUserMedia()`.
- The browser captures frames and sends them to the server for recognition.

Optimizations included:
- Burst capture (tries multiple frames)
- Lighting fallback in recognition
- In-memory model/cascade caching

## 8. Cloud Deployment (Render + Supabase) (Recommended)

### 8.1 Create Supabase project

1. Create a project in Supabase
2. Create a storage bucket (example: `smartattendance`)
3. Get:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - Postgres `DATABASE_URL` (use Session Pooler URI for IPv4 networks)

### 8.2 Render environment variables

Set these in Render:
- `SECRET_KEY`
- `DATABASE_URL` (Postgres URI, include `?sslmode=require`)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`

### 8.3 Render start command

Use:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
```

### 8.4 Deploy

- Connect Render to your GitHub repo
- Deploy latest commit
- Open the public URL

Note: Render free tier may sleep after inactivity. First request after sleep can take 30-60 seconds.

## 9. Cloud Deployment (Vercel) (Serverless)

This repo includes:
- `api/index.py` entrypoint
- `vercel.json` routes

### 9.1 Add environment variables in Vercel

Same variables as Render:
- `SECRET_KEY`
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`

### 9.2 Deploy

1. Import the GitHub repo into Vercel
2. Deploy
3. Test health endpoint:
   - `/healthz`
4. Then open:
   - `/login`

Important notes for Vercel:
- The filesystem is read-only except `/tmp`
- SQLite fallback uses `/tmp` automatically on Vercel
- Heavy OpenCV workloads can be slower on serverless than Render

## 10. Notifications (Optional)

The project supports attendance notifications (Email/SMS) if configured.

Email (SMTP) env vars:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_USE_TLS`

SMS (Twilio) env vars:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_PHONE`

Note: Twilio may require verified numbers / paid balance (trial restrictions).

## 11. Troubleshooting

### 11.1 Face not recognized

- Ensure `model/face_model.xml` exists and is trained with the correct student faces
- Face must be centered and close to the camera
- Use better lighting; burst capture helps but cannot fix extreme darkness

### 11.2 Render shows "Application loading"

- Free tier sleeping behavior; wait 30-60s and refresh

### 11.3 Vercel error: FUNCTION_INVOCATION_FAILED

Common causes:
- Missing env vars in Vercel
- DB unreachable during invocation
- Using local filesystem paths (fixed in this repo using `/tmp` on Vercel)

Check:
- Vercel Deployment -> Functions Logs

## 12. Security Notes

- Never commit `.env` or secret keys to GitHub
- If secrets were shared accidentally, rotate them in Supabase and update hosting env vars

