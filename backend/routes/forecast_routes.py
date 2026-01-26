"""
Forecast Routes
ML-powered forecasting endpoints for BioHIVE
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional

from backend.store import get_db
from backend.services.response import success, error_response
from backend.services.forecasting import ForecastService

router = APIRouter(
    prefix="/forecast",
    tags=["forecast"]
)


@router.get("/")
def get_forecast(
    days: int = Query(7, ge=1, le=30, description="Number of days to forecast"),
    symptom: Optional[str] = Query(None, description="Symptom type: fever, cough, gi, or all"),
    model: Optional[str] = Query(None, description="Specific model name (optional)"),
    db: Session = Depends(get_db)
):
    """
    Get ML-generated forecasts.
    
    Query Parameters:
        days: Number of days to forecast (1-30, default: 7)
        symptom: Optional symptom filter (fever, cough, gi, all)
        model: Optional model filter (prophet, sarima, xgboost, ensemble)
    
    Returns:
        Forecast data with predictions and confidence intervals
    """
    try:
        service = ForecastService(db)
        
        if model:
            # Get forecast from specific model
            data = service.get_forecast_by_model(
                model_name=model,
                symptom=symptom,
                days=days
            )
        else:
            # Get latest forecast (any model)
            data = service.get_forecast(
                symptom=symptom,
                days=days
            )
        
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


@router.get("/summary")
def get_forecast_summary(db: Session = Depends(get_db)):
    """
    Get summary of all available forecasts.
    
    Returns:
        High-level forecast statistics including:
        - Total forecasts available
        - Latest forecast date
        - Available models
        - Symptoms covered
        - Date coverage
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


@router.get("/models")
def get_available_models(db: Session = Depends(get_db)):
    """
    Get list of available ML models.
    
    Returns:
        List of model names that have generated forecasts
    """
    try:
        service = ForecastService(db)
        models = service.get_available_models()
        
        return success({
            "models": models,
            "total": len(models)
        })
        
    except Exception as e:
        return error_response(
            code="FORECAST_ERROR",
            message=f"Failed to get available models: {str(e)}",
            status_code=500
        )


@router.get("/by-model/{model_name}")
def get_forecast_by_model(
    model_name: str,
    days: int = Query(7, ge=1, le=30),
    symptom: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get forecasts from a specific ML model.
    
    Path Parameters:
        model_name: Name of the model (e.g., prophet, sarima, xgboost, ensemble)
    
    Query Parameters:
        days: Number of days to forecast (1-30, default: 7)
        symptom: Optional symptom filter
    
    Returns:
        Forecast data from the specified model
    """
    try:
        service = ForecastService(db)
        data = service.get_forecast_by_model(
            model_name=model_name,
            symptom=symptom,
            days=days
        )
        
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
            message=f"Failed to get forecast for model '{model_name}': {str(e)}",
            status_code=500
        )


@router.get("/latest-date")
def get_latest_forecast_date(db: Session = Depends(get_db)):
    """
    Get the most recent forecast generation date.
    
    Returns:
        Latest date when forecasts were generated
    """
    try:
        service = ForecastService(db)
        latest_date = service.get_latest_forecast_date()
        
        if latest_date is None:
            return success({
                "latest_date": None,
                "message": "No forecasts available yet"
            })
        
        return success({
            "latest_date": latest_date.isoformat(),
            "message": "Latest forecast date retrieved"
        })
        
    except Exception as e:
        return error_response(
            code="FORECAST_ERROR",
            message=f"Failed to get latest forecast date: {str(e)}",
            status_code=500
        )


@router.get("/compare-models")
def compare_models(
    symptom: str = Query(..., description="Symptom to compare (fever, cough, gi)"),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Compare forecasts from different models for the same symptom.
    
    Query Parameters:
        symptom: Symptom to compare (required)
        days: Number of days to forecast
    
    Returns:
        Forecasts from all available models for comparison
    """
    try:
        service = ForecastService(db)
        available_models = service.get_available_models()
        
        if not available_models:
            return success({
                "symptom": symptom,
                "models": [],
                "message": "No forecasts available yet"
            })
        
        # Get forecasts from each model
        model_forecasts = {}
        for model in available_models:
            try:
                forecast = service.get_forecast_by_model(
                    model_name=model,
                    symptom=symptom,
                    days=days
                )
                model_forecasts[model] = forecast
            except Exception as e:
                # If a model doesn't have data for this symptom, skip it
                continue
        
        return success({
            "symptom": symptom,
            "days": days,
            "models": model_forecasts,
            "total_models": len(model_forecasts)
        })
        
    except ValueError as e:
        return error_response(
            code="INVALID_PARAMETER",
            message=str(e),
            status_code=400
        )
    except Exception as e:
        return error_response(
            code="FORECAST_ERROR",
            message=f"Failed to compare models: {str(e)}",
            status_code=500
        )