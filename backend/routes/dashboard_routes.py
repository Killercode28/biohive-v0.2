from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, datetime

from backend.store import get_db
from backend.services.response import success, error_response
from backend.services.aggregation import AggregationService
from backend.services.forecasting import ForecastService

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)


# =========================================================
# Aggregated data
# =========================================================
@router.get("/aggregated")
def get_aggregated(
    date_str: str = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
    refresh: bool = Query(False, description="Force re-computation of aggregated data"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated symptom data for a specific date.
    
    Query Parameters:
        date: Date in YYYY-MM-DD format (e.g., "2026-01-25")
        refresh: If true, force re-computation of aggregated data (default: false)
    
    Returns:
        Aggregated data for the specified date
    """
    try:
        # Parse date string to date object
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        service = AggregationService(db)
        
        # If refresh is requested or no data exists, compute it
        if refresh:
            data = service.aggregate_date(target_date)
        else:
            data = service.get_aggregated_data(target_date)
            # If no aggregated data exists, compute it
            if not data:
                data = service.aggregate_date(target_date)

        return success(data)
        
    except ValueError as e:
        return error_response(
            code="INVALID_DATE",
            message=f"Invalid date format. Use YYYY-MM-DD: {str(e)}",
            status_code=400
        )
    except Exception as e:
        return error_response(
            code="AGGREGATION_ERROR",
            message=f"Failed to get aggregated data: {str(e)}",
            status_code=500
        )


# =========================================================
# Forecast endpoint
# =========================================================
@router.get("/forecast")
def get_forecast(
    days: int = Query(7, ge=1, le=30, description="Number of days to forecast"),
    symptom: str = Query(None, description="Symptom type: fever, cough, gi, or all"),
    db: Session = Depends(get_db)
):
    """
    Get latest forecasts from database.
    
    Query Parameters:
        days: Number of days to forecast (1-30, default: 7)
        symptom: Optional symptom filter (fever, cough, gi, all)
    
    Returns:
        Latest forecast data
    """
    try:
        service = ForecastService(db)
        
        # Call the correct method name
        data = service.get_forecast(symptom=symptom, days=days)
        
        return success(data)
        
    except ValueError as e:
        return error_response(
            code="INVALID_PARAMETER",
            message=str(e),
            status_code=400
        )
    except Exception as e:
        return error_response(
            code="FORECAST_ERROR",
            message=f"Failed to get forecast: {str(e)}",
            status_code=500
        )


# =========================================================
# Forecast summary endpoint
# =========================================================
@router.get("/forecast/summary")
def get_forecast_summary(db: Session = Depends(get_db)):
    """
    Get summary of all available forecasts.
    
    Returns:
        High-level forecast statistics
    """
    try:
        service = ForecastService(db)
        data = service.get_forecast_summary()
        return success(data)
        
    except Exception as e:
        return error_response(
            code="FORECAST_ERROR",
            message=f"Failed to get forecast summary: {str(e)}",
            status_code=500
        )