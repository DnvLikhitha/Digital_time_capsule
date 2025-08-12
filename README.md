
# Digital Time Capsule (FastAPI + PostgreSQL)

A starter full-stack project for the "Digital Time Capsule" using FastAPI and PostgreSQL.
Frontend is served via Jinja2 templates (no Node/React required).

## Features
- Create capsules with title, message, unlock date, and file uploads.
- Files stored on disk (`uploads/`), metadata in PostgreSQL.
- Background scheduler automatically unlocks capsules when their date arrives.
- Simple, aesthetic UI with glassmorphism and gentle animations.
- Manual unlock endpoint for testing/admin.

## Requirements
- Python 3.10+
- PostgreSQL (create a database and user)
- Recommended: virtualenv

## Setup (local)
1. Clone or unzip the project.
2. Create a Python virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .\.venv\Scripts\activate  # Windows (PowerShell)
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create Postgres database and note the DATABASE_URL, for example:
   `postgresql://dtc_user:password@localhost:5432/dtc_db`
5. Copy `.env.example` to `.env` and edit `DATABASE_URL` and other optional settings.
6. Initialize the database (the app will auto-create tables on first run).
7. Run the app:
   ```bash
   uvicorn backend.main:app --reload
   ```
8. Open http://127.0.0.1:8000

## Files of interest
- `backend/main.py` -- FastAPI app and routes
- `backend/database.py` -- SQLAlchemy engine & session
- `backend/models.py` -- ORM models (Capsule, File)
- `backend/crud.py` -- DB helper functions
- `backend/templates/` -- HTML templates (index, create, detail)
- `backend/static/` -- CSS, JS, images
- `uploads/` -- Uploaded files (created at runtime)

## Notes
- For production, store files in cloud storage (Azure Blob) and use managed scheduling (Azure Functions).
- Add authentication before using with real user data.
