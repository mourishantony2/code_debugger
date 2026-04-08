# Debug Code Event Platform

A full-stack Flask web application for conducting code debugging competitions — similar to HackerRank debugging contests.

---
## Live Demo

https://code-debugger-4jkz.onrender.com/

---

## Features

- **Participant registration** (name, college, register number)
- **Multi-language support** (Python, C — admin can add more)
- **Question-by-question exam flow** with no back navigation
- **Countdown timer** per question (green → yellow → red)
- **5-attempt limit** with visual pip indicators
- **Score calculation**: base score (100) + time bonus (up to 40) − wrong-attempt penalty (10 each)
- **Code comparison** (whitespace-insensitive, case-sensitive)
- **Admin dashboard** — manage languages, problems, view participants, submissions, leaderboard
- **Excel export** (pandas + openpyxl)
- **Security JS**: disables right-click, DevTools, copy/paste, F12, refresh, back navigation
- **Fullscreen enforcement** with auto-logout on exit

---

## Project Structure

```
code_debugger/
├── app.py                  # App factory + DB init
├── config.py               # Config class (secrets, DB URI)
├── models.py               # SQLAlchemy models
├── routes/
│   ├── auth.py             # Registration + logout
│   ├── admin.py            # Admin panel + CRUD + export
│   └── exam.py             # Exam flow + submission logic
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── admin_dashboard.html
│   ├── add_problem.html
│   ├── language_select.html
│   ├── exam.html
│   └── complete.html
├── static/
│   ├── css/style.css
│   └── js/
│       ├── exam.js
│       └── security.js
├── utils/
│   ├── scoring.py
│   └── excel_export.py
├── requirements.txt
└── README.md
```

---

## Quick Start (Local)

### 1. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
python app.py
```

The database (`debug_event.db`) is created automatically on first run.  
Python and C languages are seeded automatically.

Visit: **http://127.0.0.1:5000**

---

## Admin Access

| Field    | Value      |
|----------|------------|
| URL      | `/admin/login` |
| Username | `Admin`    |
| Password | `admin123` |

---

## Adding Questions (Admin)

1. Login as Admin → Dashboard
2. Click **Problems** tab → **Add Problem**
3. Fill in:
   - Language, Question Number, Time Limit
   - Problem Name
   - **Error Code** (shown to participant)
   - **Correct Code** (used for comparison — hidden from participants)
   - Expected Output (shown on correct answer)

---

## Scoring Formula

```
base_score   = 100
time_bonus   = (remaining_time / time_limit) × 40
penalty      = wrong_attempts × 10
final_score  = max(0, base_score + time_bonus − penalty)
```

---

## Deploy to Render (Free Tier)

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Create a Render Web Service

- Go to https://render.com → New → Web Service
- Connect your GitHub repo
- Fill in:

| Setting       | Value                      |
|---------------|----------------------------|
| Environment   | Python                     |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app`         |
| Branch        | `main`                     |

### 3. Add Environment Variable (optional but recommended)

| Key        | Value                        |
|------------|------------------------------|
| SECRET_KEY | `your-random-secret-here`    |

### 4. Deploy

Click **Create Web Service** — Render will build and deploy.

> **Note:** Render's free tier uses ephemeral storage, so the SQLite DB resets on redeploy. For a persistent database on Render, consider upgrading to a paid tier or using an external database like PostgreSQL (via Render's managed DB).

---

## Security Features

| Feature              | Implemented |
|----------------------|-------------|
| Right-click disabled | ✅          |
| Copy/paste disabled  | ✅          |
| F12 disabled         | ✅          |
| Ctrl+U disabled      | ✅          |
| Ctrl+R / F5 disabled | ✅          |
| Back navigation blocked | ✅       |
| Fullscreen enforced  | ✅          |
| Auto-logout on FS exit | ✅        |
| Code not executed (text compare only) | ✅ |
