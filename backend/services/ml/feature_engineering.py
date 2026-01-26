"""
Feature Engineering for BioHIVE
Builds time-series ML features from aggregated signals
"""

import pandas as pd


class TimeSeriesFeatureEngineer:
    pass


class TimeSeriesFeatureEngineer:
    """
    Deterministic feature builder for time-series models
    """

    def __init__(self, df: pd.DataFrame):
        if df is None or df.empty:
            raise ValueError("Input DataFrame is empty")

        self.df = df.copy()
        self._validate_columns()

    def _validate_columns(self):
        required = {
            "date",
            "total_fever",
            "total_cough",
            "total_gi",
            "participating_nodes",
            "risk_score",
        }

        missing = required - set(self.df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _add_time_features(self):
        self.df["date"] = pd.to_datetime(self.df["date"])
        self.df["day_of_week"] = self.df["date"].dt.weekday
        self.df["week_of_year"] = self.df["date"].dt.isocalendar().week.astype(int)
        self.df["month"] = self.df["date"].dt.month

    def _add_lags(self, col, lags=(1, 7, 14)):
        for lag in lags:
            self.df[f"{col}_lag_{lag}"] = self.df[col].shift(lag)

    def _add_rolling(self, col, windows=(7, 14)):
        for w in windows:
            self.df[f"{col}_roll_mean_{w}"] = self.df[col].rolling(w).mean()
            self.df[f"{col}_roll_std_{w}"] = self.df[col].rolling(w).std()

    def build_features(self) -> pd.DataFrame:
        self._add_time_features()

        for col in ["total_fever", "total_cough", "total_gi", "risk_score"]:
            self._add_lags(col)
            self._add_rolling(col)

        self.df = self.df.sort_values("date").reset_index(drop=True)
        return self.df
