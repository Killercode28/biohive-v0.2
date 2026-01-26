from backend.services.ml.data_loader import AggregatedSignalLoader
from backend.services.ml.models.prophet_model import ProphetModel

def main():
    loader = AggregatedSignalLoader()
    df = loader.load_range()

    model = ProphetModel(symptom="total_fever")
    model.fit(df)

    preds = model.predict(horizon=7)

    print("\n=== PROPHET OUTPUT ===")
    print(preds)

if __name__ == "__main__":
    main()
