from backend.services.ml.data_loader import AggregatedSignalLoader
from backend.services.ml.feature_engineering import TimeSeriesFeatureEngineer

def main():
    loader = AggregatedSignalLoader()
    df = loader.load_range()

    fe = TimeSeriesFeatureEngineer(df)
    features = fe.build_features()

    print("\n=== FEATURE ENGINEERING OUTPUT ===")
    print(features.head())
    print("\nShape:", features.shape)
    print("Columns:", features.columns.tolist())

if __name__ == "__main__":
    main()
