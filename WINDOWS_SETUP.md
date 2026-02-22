# SmartAttendance Windows Setup

This guide is for local run on Windows (PowerShell).

## 1) Open project

```powershell
cd C:\path\to\SmartAttendance
```

## 2) Create virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Install dependencies

```powershell
pip install -r requirements.txt
```

## 4) Create `.env` file

Create a file named `.env` in project root and add:

```env
SECRET_KEY=your-random-secret
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-1-ap-south-1.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_STORAGE_BUCKET=smartattendance
```

## 5) Run app

```powershell
py app.py
```

Open: `http://127.0.0.1:5000/login`

## Notes

1. Because `.env` is now auto-loaded in `app.py`, Windows users do not need manual `setx` commands.
2. For cloud hosting (Render), set env vars in Render dashboard instead of local `.env`.
