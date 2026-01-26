"""
SARIMA Model for BioHIVE
Statistical baseline model (no ML magic)
"""

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


class SarimaModel:
    def __init__(self, symptom: str):
        self.symptom = symptom
        self.model = None
        self.fitted = None

    def fit(self, df: pd.DataFrame):
        """
        df must contain:
        - date
        - target column (symptom)
        """
        series = (
            df.set_index("date")[self.symptom]
            .astype(float)
            .sort_index()
        )

        self.model = SARIMAX(
            series,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )

        self.fitted = self.model.fit(disp=False)

    def predict(self, horizon: int = 14) -> pd.DataFrame:
        forecast = self.fitted.get_forecast(steps=horizon)
        conf = forecast.conf_int()

        dates = pd.date_range(
            start=self.fitted.data.dates[-1] + pd.Timedelta(days=1),
            periods=horizon,
        )

        return pd.DataFrame({
            "date": dates,
            "symptom": self.symptom,
            "predicted": forecast.predicted_mean.values,
            "lower": conf.iloc[:, 0].values,
            "upper": conf.iloc[:, 1].values,
            "model_name": "SARIMA",
            "confidence": 0.85,  # Added confidence
        })
    
    def fit_predict(self, df: pd.DataFrame, horizon: int = 7) -> pd.DataFrame:
        """
        Convenience method: fit and predict in one call.
        
        Args:
            df: DataFrame with date and symptom columns
            horizon: Number of days to forecast
        
        Returns:
            DataFrame with predictions
        """
        self.fit(df)
        return self.predict(horizon)