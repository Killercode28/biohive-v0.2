# BioHIVE – Integration Rules (Read Before Coding)

## 🔒 Frozen Contracts (DO NOT MODIFY)
The following are locked and must not be changed without team discussion:

- API response format (services/response.py)
- NodeReport schema (backend/schemas.py)
- Existing endpoints:
  - POST /api/v1/node/report
  - GET /api/v1/node/reports
  - GET /api/v1/dashboard/aggregated
- Risk levels: LOW / MEDIUM / HIGH
- Aggregation by (date, zone_id)

## 🧱 File Ownership Rules

### app.py
- Owned by Lead
- Do NOT modify unless instructed

### schemas.py
- Single source of truth for data contracts
- Any change breaks integration

### routes/
- Team members may work ONLY inside their assigned route file
- Do not import directly from other route files

### aggregation.py
- Core logic
- Changes require approval

### store.py
- Temporary (in-memory)
- Will be replaced by DB later

## 🚫 What NOT To Do
- Do not change request/response formats
- Do not add new fields without discussion
- Do not refactor imports
- Do not add ML logic yet
- Do not add authentication yet

## ✅ How To Add New Features
1. Propose change
2. Confirm contract impact
3. Implement in isolation
4. Test via /docs
5. Merge

Breaking contracts without coordination will cause integration failure.
