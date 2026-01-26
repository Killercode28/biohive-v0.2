"""
Prophet Model (cmdstanpy backend)
"""

import pandas as pd
from prophet import Prophet


class ProphetModel:
    def __init__(self, symptom: str):
        self.symptom = symptom
        self.model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,
        )

    def fit(self, df: pd.DataFrame):
        prophet_df = df[["date", self.symptom]].rename(
            columns={"date": "ds", self.symptom: "y"}
        )

        self.model.fit(prophet_df)

    def predict(self, horizon: int = 14) -> pd.DataFrame:
        future = self.model.make_future_dataframe(periods=horizon)
        forecast = self.model.predict(future).tail(horizon)

        return pd.DataFrame({
            "date": forecast["ds"],
            "symptom": self.symptom,
            "predicted": forecast["yhat"],
            "lower": forecast["yhat_lower"],
            "upper": forecast["yhat_upper"],
            "model_name": "PROPHET",
            "confidence": 0.80,  # Added confidence
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