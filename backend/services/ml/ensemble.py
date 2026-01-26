"""
Ensemble Forecaster for BioHIVE
Combines predictions from multiple models using weighted average
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class ForecastEnsembler:
    """
    Ensemble multiple forecast models using weighted average.
    
    Default weights:
    - SARIMA: 40% (statistical baseline)
    - Prophet: 30% (robust forecasting)
    - XGBoost: 30% (ML pattern recognition)
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize ensemble with model weights.
        
        Args:
            weights: Dictionary of model weights (must sum to 1.0)
                    Default: {'SARIMA': 0.4, 'PROPHET': 0.3, 'XGBOOST': 0.3}
        """
        if weights is None:
            self.weights = {
                'SARIMA': 0.40,
                'PROPHET': 0.30,
                'XGBOOST': 0.30
            }
        else:
            # Validate weights sum to 1.0
            total = sum(weights.values())
            if not np.isclose(total, 1.0):
                raise ValueError(f"Weights must sum to 1.0, got {total}")
            self.weights = weights
        
        print(f"🎯 Ensemble initialized with weights: {self.weights}")
    
    def ensemble(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Combine predictions using weighted average.
        
        Args:
            df: DataFrame with columns:
                - date: prediction date
                - symptom: symptom type
                - predicted: predicted value
                - lower: lower confidence bound
                - upper: upper confidence bound
                - model_name: model identifier
        
        Returns:
            DataFrame with ensemble predictions
        """
        # Group by date and symptom
        grouped = df.groupby(["date", "symptom"])
        
        ensemble_results = []
        
        for (pred_date, symptom), group in grouped:
            # Calculate weighted average for each metric
            weighted_pred = 0.0
            weighted_lower = 0.0
            weighted_upper = 0.0
            total_weight = 0.0
            
            for _, row in group.iterrows():
                model_name = row['model_name']
                weight = self.weights.get(model_name, 0.0)
                
                if weight > 0:
                    weighted_pred += row['predicted'] * weight
                    weighted_lower += row['lower'] * weight
                    weighted_upper += row['upper'] * weight
                    total_weight += weight
            
            # Normalize if weights don't sum to 1.0 (some models might be missing)
            if total_weight > 0:
                weighted_pred /= total_weight
                weighted_lower /= total_weight
                weighted_upper /= total_weight
            
            # Calculate ensemble confidence (average of model confidences)
            avg_confidence = group['confidence'].mean() if 'confidence' in group.columns else 0.75
            
            ensemble_results.append({
                'date': pred_date,
                'symptom': symptom,
                'predicted': weighted_pred,
                'lower': weighted_lower,
                'upper': weighted_upper,
                'model_name': 'ENSEMBLE',
                'confidence': avg_confidence
            })
        
        ensemble_df = pd.DataFrame(ensemble_results)
        
        print(f"✅ Ensemble created: {len(ensemble_df)} predictions")
        return ensemble_df
    
    def ensemble_with_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensemble with fallback to median if weighted average fails.
        
        Args:
            df: DataFrame with predictions
        
        Returns:
            DataFrame with ensemble predictions
        """
        try:
            return self.ensemble(df)
        except Exception as e:
            print(f"⚠️  Weighted ensemble failed: {e}")
            print(f"   Falling back to median ensemble...")
            return self._median_ensemble(df)
    
    def _median_ensemble(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fallback: Use median instead of weighted average.
        
        Args:
            df: DataFrame with predictions
        
        Returns:
            DataFrame with median ensemble
        """
        grouped = df.groupby(["date", "symptom"])
        
        final = grouped.agg(
            predicted=("predicted", "median"),
            lower=("lower", "median"),
            upper=("upper", "median"),
        ).reset_index()
        
        final["model_name"] = "ENSEMBLE"
        final["confidence"] = 0.75
        
        return final