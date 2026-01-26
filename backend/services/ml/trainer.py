"""
Forecast Training Orchestrator for BioHIVE
Coordinates training of multiple models and ensemble creation
"""

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Tuple, List

from backend.services.ml.models.sarima_model import SarimaModel
from backend.services.ml.models.prophet_model import ProphetModel
from backend.services.ml.models.xgboost_model import XGBoostModel
from backend.services.ml.ensemble import ForecastEnsembler


class ForecastTrainer:
    """
    Train multiple forecasting models and create ensemble predictions.
    
    Orchestrates:
    1. SARIMA training and prediction
    2. Prophet training and prediction
    3. XGBoost training and prediction
    4. Ensemble combination
    """
    
    def __init__(self, symptom: str, horizon: int = 7):
        """
        Initialize trainer.
        
        Args:
            symptom: Symptom to forecast ('total_fever', 'total_cough', 'total_gi')
            horizon: Number of days to forecast ahead (default: 7)
        """
        self.symptom = symptom
        self.horizon = horizon
        
        print(f"\n🎯 ForecastTrainer initialized")
        print(f"   Symptom: {symptom}")
        print(f"   Horizon: {horizon} days")
    
    def run(self, df: pd.DataFrame, features: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Train all models and create ensemble.
        
        Args:
            df: Time series DataFrame with symptom data (from data_loader)
            features: Feature-engineered DataFrame (from feature_engineering)
        
        Returns:
            Tuple of (raw_predictions, ensemble_predictions)
        """
        predictions = []
        
        # Prepare data: SARIMA/Prophet need 'date' as column, not index
        if isinstance(df.index, pd.DatetimeIndex):
            df_for_models = df.reset_index()
        else:
            df_for_models = df.copy()
        
        print(f"\n{'='*60}")
        print(f"TRAINING MODELS FOR: {self.symptom.upper()}")
        print(f"{'='*60}")
        
        # ---------- SARIMA ----------
        print(f"\n[1/3] Training SARIMA...")
        try:
            sarima = SarimaModel(symptom=self.symptom)
            sarima_pred = sarima.fit_predict(df_for_models, horizon=self.horizon)
            predictions.append(sarima_pred)
            print(f"✅ SARIMA: {len(sarima_pred)} predictions")
        except Exception as e:
            print(f"❌ SARIMA failed: {e}")
        
        # ---------- PROPHET ----------
        print(f"\n[2/3] Training Prophet...")
        try:
            prophet = ProphetModel(symptom=self.symptom)
            prophet_pred = prophet.fit_predict(df_for_models, horizon=self.horizon)
            predictions.append(prophet_pred)
            print(f"✅ Prophet: {len(prophet_pred)} predictions")
        except Exception as e:
            print(f"❌ Prophet failed: {e}")
        
        # ---------- XGBOOST ----------
        print(f"\n[3/3] Training XGBoost...")
        try:
            xgb_pred = self._train_xgboost(df, features)
            predictions.append(xgb_pred)
            print(f"✅ XGBoost: {len(xgb_pred)} predictions")
        except Exception as e:
            print(f"❌ XGBoost failed: {e}")
        
        # Check if we have any predictions
        if not predictions:
            raise RuntimeError("All models failed! No predictions available.")
        
        print(f"\n{'='*60}")
        print(f"CREATING ENSEMBLE")
        print(f"{'='*60}")
        
        # Combine raw predictions
        raw = pd.concat(predictions, ignore_index=True)
        print(f"✅ Combined raw predictions: {len(raw)} total")
        
        # Create ensemble
        ensembler = ForecastEnsembler()
        final = ensembler.ensemble(raw)
        print(f"✅ Ensemble created: {len(final)} predictions")
        
        return raw, final
    
    def _train_xgboost(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Train XGBoost model and generate predictions."""
        
        # Initialize model
        xgb = XGBoostModel(symptom=self.symptom)
        
        # Train on features
        xgb.fit(features)
        
        # Generate future features
        future_features = self._generate_future_features(df, features)
        
        # Make predictions
        xgb_preds = xgb.predict(future_features)
        
        # Add dates
        last_date = df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df['date'].max())
        
        future_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=self.horizon,
            freq="D",
        )
        
        xgb_preds["date"] = future_dates
        
        return xgb_preds
    
    def _generate_future_features(self, df: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Generate future features for XGBoost prediction."""
        
        # Get last known values
        last_row = features.iloc[-1].copy()
        
        # Get last date
        if isinstance(df.index, pd.DatetimeIndex):
            last_date = df.index[-1]
        else:
            last_date = pd.to_datetime(df['date'].max())
        
        future_features = []
        
        for i in range(1, self.horizon + 1):
            future_date = last_date + timedelta(days=i)
            
            # Create feature row
            feat_row = last_row.copy()
            
            # Update time-based features
            if 'day_of_week' in feat_row:
                feat_row['day_of_week'] = future_date.dayofweek
            if 'week_of_year' in feat_row:
                feat_row['week_of_year'] = future_date.isocalendar()[1]
            if 'month' in feat_row:
                feat_row['month'] = future_date.month
            if 'is_weekend' in feat_row:
                feat_row['is_weekend'] = 1 if future_date.dayofweek >= 5 else 0
            
            future_features.append(feat_row)
        
        future_df = pd.DataFrame(future_features)
        
        return future_df


def train_all_symptoms(df: pd.DataFrame, features: pd.DataFrame, symptoms: List[str] = None, horizon: int = 7) -> pd.DataFrame:
    """
    Train forecasts for multiple symptoms.
    
    Args:
        df: Time series DataFrame
        features: Feature-engineered DataFrame
        symptoms: List of symptoms to forecast
        horizon: Forecast horizon in days
    
    Returns:
        DataFrame with all ensemble predictions
    """
    if symptoms is None:
        symptoms = ['total_fever', 'total_cough', 'total_gi']
    
    all_ensembles = []
    
    for symptom in symptoms:
        print(f"\n{'#'*70}")
        print(f"# FORECASTING: {symptom.upper()}")
        print(f"{'#'*70}")
        
        trainer = ForecastTrainer(symptom=symptom, horizon=horizon)
        
        try:
            raw, ensemble = trainer.run(df, features)
            all_ensembles.append(ensemble)
        except Exception as e:
            print(f"❌ Failed to train {symptom}: {e}")
            continue
    
    if not all_ensembles:
        raise RuntimeError("All symptom forecasts failed!")
    
    # Combine all symptom forecasts
    final_ensemble = pd.concat(all_ensembles, ignore_index=True)
    
    print(f"\n{'='*70}")
    print(f"✅ ALL FORECASTS COMPLETE")
    print(f"   Total predictions: {len(final_ensemble)}")
    print(f"   Symptoms: {symptoms}")
    print(f"{'='*70}\n")
    
    return final_ensemble