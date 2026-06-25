# SafeNet — Family Online Safety Platform

SafeNet gives parents the tools to teach, monitor, and respond to online threats — all in one free app. No technical skills required.

## Features

- **Interactive Lessons** — 10 bite-sized safety lessons with quizzes (privacy, phishing, social media, cyberbullying, etc.)
- **Practice Scenarios** — 4 interactive real-world situations to walk through with your child
- **One-Click Reporting** — Report harmful content and generate downloadable reports for NCMEC / law enforcement
- **Family Dashboard** — Safety score, completed lessons, reports filed, checklist progress
- **Safety Plan Generator** — Create a customized family safety plan with rules, contacts, and step-by-step actions
- **OSINT Scanner** — Check if usernames appear across 25+ platforms; scan for exposed emails
- **Parent Mobile Dashboard** — Safety score, recent activity, daily tips — updated in real time
- **Admin Marketing Tools** — Ad templates, email templates, social media posts, campaign tracking
- **Auto-Update** — Checks for updates on launch, installs with one click
- **Chrome Extension** — Right-click any profile/post to flag it

## Quick Start

### Option 1: Download the EXE

Download `SafeNet.exe` from the [latest release](https://github.com/colbyatcheson01-source/safenet/releases/latest). Double-click to run — your browser opens to the dashboard.

### Option 2: Run from source

```bash
pip install -r requirements.txt
python run.py
```

Then open http://127.0.0.1:5000

### Local demo accounts (dev only)

| Role  | Email                | Password |
|-------|----------------------|----------|
| Admin | admin@safenet.local  | admin123 |
| Demo  | demo@safenet.local   | demo123  |

> Credentials are only seeded in local/dev mode. On Railway (production), no default accounts are created.

## Deployment

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

The repo includes Railway configuration (`Procfile`, `railway.json`, `runtime.txt`). Connect your fork to Railway — it auto-detects Python and deploys.

### Environment Variables

| Variable     | Description                          |
|-------------|--------------------------------------|
| `SECRET_KEY` | Flask secret key (auto-generated if not set) |

## Packaging

```powershell
.\package.ps1
```

Builds a standalone `SafeNet.exe` (~40 MB) using PyInstaller. No Python needed to run the result.

## Tech Stack

- **Backend:** Flask (Python 3.12)
- **Database:** SQLite
- **Server:** Waitress (local), Gunicorn (deployed)
- **Frontend:** Vanilla CSS + JS
- **Packaging:** PyInstaller

## License

Free for all use. Pay-what-you-can donations accepted.
