from fastapi import APIRouter
from backend.services.response import success
from backend.aggregation import aggregate_reports

router = APIRouter()

@router.get("/dashboard/aggregated")
async def get_aggregated_data():
    data = aggregate_reports()
    return success(
        data=data,
        message="Aggregated outbreak signals"
    )
