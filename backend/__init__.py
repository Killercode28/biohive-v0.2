"""
BioHIVE ML Module
Machine Learning and Forecasting Services for Disease Surveillance
"""

__version__ = "1.0.0"

# Model configuration
ENSEMBLE_WEIGHTS = {
    'sarima': 0.40,
    'prophet': 0.30,
    'xgboost': 0.30
}

FORECAST_HORIZON = 3
TRAINING_WINDOW = 60