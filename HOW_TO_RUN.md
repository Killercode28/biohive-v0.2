# How To Run BioHIVE Backend

## Requirements
- Python 3.10+
- pip installed

## Install Dependencies
```bash
pip install fastapi uvicorn
Run Server (IMPORTANT)

Always run from project root:

uvicorn backend.app:app --reload

Access API

Swagger UI: http://127.0.0.1:8000/docs

Health Check: http://127.0.0.1:8000/api/v1/health

Important Notes

In-memory data is LOST on server restart

Do not run multiple uvicorn instances

Port must be 8000


Save.

---

# STEP 3 — COMMIT THIS STATE (CRITICAL)

This is the **handoff point**.

```bash
git add .
git commit -m "v0.1: collaboration baseline locked"
git tag v0.1-collaboration-baseline
git push --tags