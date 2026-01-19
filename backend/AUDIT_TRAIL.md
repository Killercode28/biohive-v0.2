# 🔒 Audit Trail Documentation - BioHIVE

## Final Design Characterization

**"The audit trail implements a tamper-evident cryptographic integrity mechanism using SHA-256 hashing and hash chaining. It ensures that stored reports cannot be altered without detection, while validation and anomaly detection are handled separately. The design satisfies all contract requirements without unnecessary over-engineering."**

---

## 1️⃣ Core Audit Trail Implementation

### What Was Added

The audit trail provides **cryptographic integrity** and **tamper detection** for submitted reports.

### Key Features

- ✅ **SHA-256 hashing** of report data
- ✅ **Deterministic hashing** using sorted JSON keys
- ✅ **Hash chaining** (`current_hash` + `previous_hash`)
- ✅ **Persistent storage** of audit records in database
- ✅ **Timestamped entries** for ordering and traceability

### Result

Any modification to stored reports or audit records is **detectable**.

---

## 2️⃣ Report-Level Verification

### Purpose

Verify individual reports haven't been tampered with after storage.

### Process

1. Retrieve stored audit hash
2. Retrieve stored report data
3. Recompute hash from current report data
4. Compare stored vs computed hash

### Implementation

```python
verification = audit_service.verify_report(report_id)
```

### Endpoint

```http
GET /api/v1/node/audit/verify/{report_id}
```

### Response

```json
{
  "valid": true,
  "report_id": "...",
  "stored_hash": "a1b2c3...",
  "computed_hash": "a1b2c3...",
  "match": true,
  "timestamp": "2026-01-18T...",
  "error": null
}
```

### Result

Allows **validation of specific reports on demand**.

---

## 3️⃣ Full Chain Verification

### Purpose

Ensure entire audit history integrity, not just single records.

### Process

1. Retrieve all audit entries in chronological order
2. Verify first entry has no `previous_hash`
3. For each subsequent entry, verify `previous_hash` matches prior entry's `current_hash`
4. Detect any broken links or reordered entries

### Implementation

```python
verification = audit_service.verify_chain()
```

### Endpoint

```http
GET /api/v1/node/audit/verify-chain
```

### Response

```json
{
  "valid": true,
  "total_entries": 150,
  "verified_entries": 150,
  "broken_links": [],
  "chain_integrity": 1.0,
  "error": null
}
```

### Result

Ensures **entire audit history integrity**, not just individual records.

---

## 4️⃣ Separation of Concerns

### Design Decision

**Audit Trail** and **Validation System** serve different purposes:

| Audit Trail | Validation/Warning System |
|------------|---------------------------|
| Detects tampering **after** storage | Detects suspicious input **before** acceptance |
| Cryptographic integrity | Data quality assessment |
| Tamper-evident | Truth assessment |
| Answers: "Was data modified?" | Answers: "Is data suspicious?" |

### Implementation

- **Audit Trail**: `services/audit.py`
- **Validation**: `services/validation.py`

### Result

Audit trail is **tamper-evident**, not a truth-validation mechanism (correct by design).

---

## 5️⃣ Persistence Integrity

### Implementation

- ✅ **Transactional DB operations** (`flush`, `commit`, `rollback`)
- ✅ **Atomic insertion** of reports + audit entries
- ✅ **Error handling** with rollback on failure

### Code Example

```python
# Create report
new_report = DailyReport(...)
db.add(new_report)
db.flush()  # Get report_id without committing

# Create audit entry
audit_result = audit_service.add_to_chain(report_id, hash)

# Commit both atomically
db.commit()
```

### Result

No **partial writes** or **inconsistent states**.

---

## 6️⃣ Duplicate Handling

### Design Decision

Duplicate report checks (same `node_id + date`) are handled via:

- Database unique constraints
- Validation logic (before audit trail)

### Implementation

```sql
UNIQUE(node_id, date)
```

```python
if existing_report:
    raise ValidationError('Report already exists')
```

### Result

Audit trail remains **clean** and **append-only**.

---

## 7️⃣ Health Check Integration

### Purpose

Monitor audit trail reliability indirectly via database health.

### Implementation

```http
GET /health
```

### Response

```json
{
  "status": "healthy",
  "database": {
    "status": "connected",
    "nodes": 8
  }
}
```

### Endpoint

```http
GET /api/v1/node/audit/statistics
```

### Response

```json
{
  "total_entries": 150,
  "chain_health": "HEALTHY",
  "chain_integrity": 1.0,
  "oldest_entry": "2026-01-10T...",
  "newest_entry": "2026-01-18T..."
}
```

### Result

Audit trail reliability is **monitored** via DB health checks.

---

## 8️⃣ Security Hardening (Explicitly Deferred)

### What Was NOT Added

Advanced features such as:

- ❌ HMAC / secret-key hashing
- ❌ External ledgers
- ❌ Blockchain anchoring
- ❌ Digital signatures
- ❌ Key rotation

### Reason

- Not required by Integration Contract
- Considered **over-engineering** for project scope
- Current design satisfies all requirements

### Future Enhancement

These can be added later if needed without breaking existing design.

---

## 📊 API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/node/report` | POST | Submit report (creates audit entry) |
| `/node/audit/verify/{report_id}` | GET | Verify single report |
| `/node/audit/verify-chain` | GET | Verify entire chain |
| `/node/audit/history/{report_id}` | GET | Get report audit history |
| `/node/audit/statistics` | GET | Get chain statistics |

---

## 🧪 Testing

### Run Test Suite

```bash
python test_audit_trail.py
```

### Manual Testing

```bash
# Submit report
curl -X POST "http://localhost:5000/api/v1/node/report" \
  -H "Content-Type: application/json" \
  -d '{"node_id":"clinic_1","token":"test","date":"2026-01-18","symptoms":{"fever":10,"cough":15,"gi":5}}'

# Verify report (get report_id from above)
curl "http://localhost:5000/api/v1/node/audit/verify/{report_id}"

# Verify chain
curl "http://localhost:5000/api/v1/node/audit/verify-chain"

# Get statistics
curl "http://localhost:5000/api/v1/node/audit/statistics"
```

---

## 🔍 How Tampering is Detected

### Scenario 1: Report Data Modified

1. Attacker changes `fever_count` from 10 to 100 in database
2. Verification recomputes hash from current data
3. New hash: `xyz789...`
4. Stored hash: `abc123...`
5. **Mismatch detected** → Tampering flagged

### Scenario 2: Audit Entry Deleted

1. Attacker deletes audit entry at position 50
2. Chain verification checks links
3. Position 51's `previous_hash` points to deleted entry
4. **Broken link detected** → Tampering flagged

### Scenario 3: Hash Modified

1. Attacker changes stored hash to match modified data
2. Chain verification checks links
3. Modified hash breaks chain link to next entry
4. **Chain broken** → Tampering flagged

---

## 📐 Database Schema

### audit_trail table

```sql
CREATE TABLE audit_trail (
    id VARCHAR(36) PRIMARY KEY,
    report_id VARCHAR(36) NOT NULL,
    current_hash VARCHAR(64) NOT NULL,
    previous_hash VARCHAR(64),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES daily_reports(report_id)
);
```

### Hash Chaining Example

```
Entry 1: hash=abc123, prev=NULL
Entry 2: hash=def456, prev=abc123  ← Links to Entry 1
Entry 3: hash=ghi789, prev=def456  ← Links to Entry 2
```

If Entry 2 is modified, Entry 3's `previous_hash` won't match, breaking the chain.

---

## ✅ Design Principles

1. **Tamper-Evident**: Modifications are detectable, not preventable
2. **Append-Only**: No deletions or reordering
3. **Cryptographically Secure**: SHA-256 standard
4. **Deterministic**: Same data always produces same hash
5. **Separate Concerns**: Integrity ≠ Truth validation
6. **Transactional**: Atomic operations
7. **Verifiable**: Both individual and chain-level verification

---

## 🎯 Use Cases

### ✅ Supported Use Cases

- Detect if report data was modified after submission
- Verify entire audit history hasn't been tampered with
- Prove data integrity to external auditors
- Identify when/where tampering occurred
- Track chronological report submission

### ❌ Not Supported (By Design)

- Prevent false data submission (handled by validation)
- Detect lies in original submission (not the audit trail's job)
- Prevent authorized database modifications (that's access control)

---

## 📚 Further Reading

- [SHA-256 Specification](https://en.wikipedia.org/wiki/SHA-2)
- [Hash Chains](https://en.wikipedia.org/wiki/Hash_chain)
- [Merkle Trees](https://en.wikipedia.org/wiki/Merkle_tree) (future enhancement)

---

**Last Updated**: 2026-01-18  
**Version**: 1.0  
**Status**: Production Ready ✅