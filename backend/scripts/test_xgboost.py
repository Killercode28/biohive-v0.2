from backend.services.ml.data_loader import AggregatedSignalLoader
from backend.services.ml.feature_engineering import TimeSeriesFeatureEngineer
from backend.services.ml.models.xgboost_model import XGBoostModel

def main():
    loader = AggregatedSignalLoader()
    df = loader.load_range()

    fe = TimeSeriesFeatureEngineer(df)
    features = fe.build_features()

    model = XGBoostModel(symptom="total_fever")
    model.fit(features)

    preds = model.predict(features.tail(7))

    print("\n=== XGBOOST OUTPUT ===")
    print(preds)

if __name__ == "__main__":
    main()
