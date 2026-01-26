from backend.services.ml.data_loader import AggregatedSignalLoader

def main():
    loader = AggregatedSignalLoader()
    df = loader.load_range()

    print("\n=== DATA LOADER OUTPUT ===")
    print(df.head())
    print("\nShape:", df.shape)
    print("Columns:", df.columns.tolist())

if __name__ == "__main__":
    main()
