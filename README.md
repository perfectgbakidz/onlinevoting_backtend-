# NACOS E-Voting Backend (Production-ready scaffold)

## Overview
This is a production-minded FastAPI scaffold for the NACOS E-Voting system using SQLite for storage.

## Quickstart
1. Create a virtualenv and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Edit `.env` to change configuration (SECRET_KEY, SQLALCHEMY_DATABASE_URI, etc.).
4. Start the app (development):
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open http://127.0.0.1:8000/docs for interactive API docs.

## Notes
- This scaffold includes role-based dependencies, password hashing, structured schemas, audit logging, and basic validations.
- For production, switch to PostgreSQL or another server DB and ensure `SECRET_KEY` is secure.
