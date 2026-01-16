from collections import defaultdict
from backend.store import node_reports

def compute_risk_level(fever_count: int) -> str:
    if fever_count < 30:
        return "LOW"
    elif fever_count < 70:
        return "MEDIUM"
    else:
        return "HIGH"

def aggregate_reports():
    aggregated = defaultdict(lambda: {
        "fever_count": 0,
        "cough_count": 0,
        "gi_count": 0,
        "reports": 0
    })

    for report in node_reports:
        key = (report["date"], report["zone_id"])

        aggregated[key]["fever_count"] += report["fever_count"]
        aggregated[key]["cough_count"] += report["cough_count"]
        aggregated[key]["gi_count"] += report["gi_count"]
        aggregated[key]["reports"] += 1

    result = []

    for (date, zone_id), values in aggregated.items():
        risk_level = compute_risk_level(values["fever_count"])

        result.append({
            "date": date,
            "zone_id": zone_id,
            **values,
            "risk_level": risk_level
        })

    return result
