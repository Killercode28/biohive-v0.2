from backend.services.ml.data_loader import AggregatedSignalLoader
from backend.services.ml.models.sarima_model import SarimaModel

def main():
    loader = AggregatedSignalLoader()
    df = loader.load_range()

    model = SarimaModel(symptom="total_fever")
    model.fit(df)

    preds = model.predict(horizon=7)

    print("\n=== SARIMA OUTPUT ===")
    print(preds)

if __name__ == "__main__":
    main()
