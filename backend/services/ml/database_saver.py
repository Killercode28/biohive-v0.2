"""
Save forecast predictions to database
"""

import pandas as pd
from datetime import datetime, date
from typing import List

from sqlalchemy.orm import Session
from backend.schemas import ForecastResult


class ForecastDatabaseSaver:
    """
    Save ensemble predictions to ForecastResult table.
    
    Handles:
    - Converting DataFrame predictions to database records
    - Batch insertion
    - Duplicate handling
    - Validation
    """
    
    def __init__(self, db: Session):
        """
        Initialize saver.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def save_predictions(
        self,
        predictions: pd.DataFrame,
        forecast_date: date = None
    ) -> int:
        """
        Save predictions to database.
        
        Args:
            predictions: DataFrame with columns:
                - date: prediction date
                - symptom: symptom name
                - predicted: predicted value
                - lower: lower confidence bound
                - upper: upper confidence bound
                - model_name: model identifier
                - confidence: confidence score
            forecast_date: Date when forecast was generated (default: today)
        
        Returns:
            Number of records saved
        """
        if forecast_date is None:
            forecast_date = date.today()
        
        print(f"\n💾 Saving {len(predictions)} predictions to database...")
        print(f"   Forecast date: {forecast_date}")
        
        # Convert DataFrame to database records
        records = []
        
        for _, row in predictions.iterrows():
            # Convert prediction date to date object
            pred_date = row['date']
            if isinstance(pred_date, pd.Timestamp):
                pred_date = pred_date.date()
            
            record = ForecastResult(
                forecast_date=forecast_date,
                prediction_date=pred_date,
                symptom=row['symptom'],
                predicted_value=int(round(row['predicted'])),
                lower_bound=int(round(row['lower'])),
                upper_bound=int(round(row['upper'])),
                confidence=float(row['confidence']),
                model_name=row['model_name'],
                created_at=datetime.utcnow()
            )
            records.append(record)
        
        # Check for existing records and remove duplicates
        existing_count = self._remove_existing_forecasts(forecast_date)
        if existing_count > 0:
            print(f"   Removed {existing_count} existing forecasts for {forecast_date}")
        
        # Save to database
        try:
            self.db.add_all(records)
            self.db.commit()
            print(f"✅ Successfully saved {len(records)} predictions")
            return len(records)
        
        except Exception as e:
            self.db.rollback()
            print(f"❌ Error saving predictions: {e}")
            raise
    
    def _remove_existing_forecasts(self, forecast_date: date) -> int:
        """
        Remove existing forecasts for the given date.
        
        Args:
            forecast_date: Forecast date to clear
        
        Returns:
            Number of records deleted
        """
        deleted = self.db.query(ForecastResult).filter(
            ForecastResult.forecast_date == forecast_date
        ).delete()
        
        return deleted
    
    def get_latest_forecast_date(self) -> date:
        """
        Get the most recent forecast date in database.
        
        Returns:
            Latest forecast date or None
        """
        result = self.db.query(ForecastResult.forecast_date).order_by(
            ForecastResult.forecast_date.desc()
        ).first()
        
        return result[0] if result else None
    
    def verify_saved_predictions(self, forecast_date: date) -> dict:
        """
        Verify predictions were saved correctly.
        
        Args:
            forecast_date: Forecast date to verify
        
        Returns:
            Dictionary with verification results
        """
        records = self.db.query(ForecastResult).filter(
            ForecastResult.forecast_date == forecast_date
        ).all()
        
        if not records:
            return {
                'success': False,
                'message': f'No predictions found for {forecast_date}'
            }
        
        # Group by symptom
        symptoms = {}
        for record in records:
            symptom = record.symptom
            if symptom not in symptoms:
                symptoms[symptom] = []
            symptoms[symptom].append(record)
        
        return {
            'success': True,
            'total_predictions': len(records),
            'forecast_date': forecast_date,
            'symptoms': list(symptoms.keys()),
            'predictions_per_symptom': {k: len(v) for k, v in symptoms.items()},
            'date_range': {
                'start': min(r.prediction_date for r in records),
                'end': max(r.prediction_date for r in records)
            }
        }