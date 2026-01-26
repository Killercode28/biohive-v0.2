"""
XGBoost Regressor for BioHIVE
"""

import pandas as pd
import xgboost as xgb


class XGBoostModel:
    def __init__(self, symptom: str):
        self.symptom = symptom
        self.model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
        )
        self.feature_columns = None

    def fit(self, df: pd.DataFrame):
        df = df.dropna().copy()

        self.feature_columns = [
            c for c in df.columns
            if c not in ("date", "risk_level", self.symptom)
        ]

        X = df[self.feature_columns]
        y = df[self.symptom]

        self.model.fit(X, y)

    def predict(self, df_future: pd.DataFrame) -> pd.DataFrame:
        df_future = df_future[self.feature_columns].copy()
        preds = self.model.predict(df_future)

        return pd.DataFrame({
            "date": df_future.index,
            "symptom": self.symptom,
            "predicted": preds,
            "lower": preds * 0.9,
            "upper": preds * 1.1,
            "model_name": "XGBOOST",
            "confidence": 0.75,  # Added confidence
        })