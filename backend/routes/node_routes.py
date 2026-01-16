from fastapi import APIRouter
from backend.services.response import success
from backend.schemas import NodeReport
from backend.store import node_reports

router = APIRouter()

@router.post("/node/report")
async def submit_node_report(report: NodeReport):
    data = report.dict()

    # Passive anomaly tagging
    anomalies = []

    if report.fever_count > 100:
        anomalies.append("unusually_high_fever_count")
    if report.cough_count > 100:
        anomalies.append("unusually_high_cough_count")
    if report.gi_count > 60:
        anomalies.append("unusually_high_gi_count")

    if anomalies:
        data["anomalies"] = anomalies

    node_reports.append(data)

    return success(
        data=data,
        message="Node report stored in memory"
    )
@router.get("/node/reports")
async def get_all_node_reports():
    return success(
        data={
            "count": len(node_reports),
            "reports": node_reports
        },
        message="All node reports (in-memory)"
    )
