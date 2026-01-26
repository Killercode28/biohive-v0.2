"""
BioHIVE ML Module
Machine Learning and Forecasting Services for Disease Surveillance

Three-Model Ensemble:
- SARIMA: Statistical time series model for trends and seasonality
- Prophet: Facebook's forecasting tool for robust predictions
- XGBoost: Gradient boosting for complex pattern recognition
"""

__version__ = "1.0.0"

# Model configuration
ENSEMBLE_WEIGHTS = {
    'sarima': 0.40,    # 40% - Statistical baseline
    'prophet': 0.30,   # 30% - Robust forecasting
    'xgboost': 0.30    # 30% - ML pattern recognition
}

FORECAST_HORIZON = 3  # Predict 3 days ahead
TRAINING_WINDOW = 60  # Use last 60 days for training

# Note: Classes will be imported as they are created
# from backend.services.ml.data_loader import MLDataLoader
# from backend.services.ml.ensemble import EnsembleForecaster