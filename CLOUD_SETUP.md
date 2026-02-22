# SmartAttendance Cloud Setup (Free First)

This guide explains in simple words how your project now works in cloud and what to do next.

## 1) What changed in your code

Your app is now converted from local-only style to cloud-ready style:

1. Database changed from local JSON/SQLite dependency to SQL models that work with cloud PostgreSQL.
2. Role login is centralized in DB for: `student`, `parent`, `teacher`, `admin`.
3. Attendance, announcements, notes metadata, and syllabus metadata are now DB-driven.
4. File uploads support cloud storage (Supabase Storage) if env vars are set.
5. Local fallback is still kept for easy testing on laptop.
6. Added deployment files for Render cloud hosting (`requirements.txt`, `render.yaml`).

## 2) Why this solves localhost problem

Before:
- App ran on your laptop (`localhost`), others could not reliably access.

Now:
- You can deploy once on cloud.
- Students/parents/teachers/admin use one URL from anywhere.
- Data is shared in one central DB.

## 3) Free setup (no payment now)

Use free tiers:
1. Render Free (host Flask app)
2. Supabase Free (Postgres + Storage + Auth-ready platform)

## 4) Step-by-step deployment

1. Create Supabase project (Free).
2. In Supabase SQL Editor, no manual SQL needed; app auto-creates tables on first run.
3. Create a public storage bucket in Supabase named `smartattendance`.
4. Copy values:
   - `DATABASE_URL` (Supabase Postgres pooled connection string)
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_STORAGE_BUCKET=smartattendance`
5. Push this code to GitHub.
6. Create Render Web Service from that repo.
7. Render auto-reads `render.yaml`.
8. Set env vars in Render dashboard.
9. Deploy.
10. Share Render URL with students.

## 5) What remains local-only

Face attendance with webcam (`/mark-attendance`) needs camera hardware. On cloud server there is no webcam.

Use one of these options:
1. Keep webcam attendance only on teacher laptop (local utility mode).
2. Replace with manual attendance form/API for cloud production.

## 6) Credentials currently seeded

From your files, users are auto-seeded at startup:
- Admin: `admin / 0010`
- Teacher: `teacher1 / teach123`
- Student IDs and passwords from `auth_users.json`
- Parent credentials from `auth_users.json`

## 7) If someone asks “how did cloud conversion happen?”

You can explain:

1. We moved data from local files to central database models.
2. We changed login system to role-based DB auth.
3. We added cloud storage support for uploaded documents.
4. We prepared deployment config for Render.
5. We use environment variables for secrets and cloud connections.
6. After deployment, everyone accesses the same URL and same central data.

## 8) Important free-tier reality

1. Render free service can sleep when idle.
2. First request after idle may be slow.
3. This is normal in free plans.

For college project/demo, this is usually acceptable.

