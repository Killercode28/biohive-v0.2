from fastapi import APIRouter
from backend.services.response import success
from backend.services.aggregation import aggregate_reports
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.store import get_db
from backend.services.aggregation import AggregationService
from backend.services.forecasting import ForecastService
from backend.services.response import success

router = APIRouter()

@router.get("/dashboard/aggregated")
def get_aggregated(date: date, db: Session = Depends(get_db)):
    service = AggregationService(db)
    data = service.get_aggregated_data(date)

    if not data:
        data = service.aggregate_date(date)

    return success(data)
