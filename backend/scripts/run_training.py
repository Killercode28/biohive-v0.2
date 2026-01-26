"""
Complete training pipeline for BioHIVE forecasting
Runs end-to-end: data loading → feature engineering → model training → save to DB
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from datetime import date

from backend.store import SessionLocal
from backend.services.ml.data_loader import AggregatedSignalLoader
from backend.services.ml.feature_engineering import TimeSeriesFeatureEngineer
from backend.services.ml.trainer import train_all_symptoms
from backend.services.ml.database_saver import ForecastDatabaseSaver


def main():
    """Run complete training pipeline"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║        BioHIVE Forecast Training Pipeline                 ║
    ║     SARIMA + Prophet + XGBoost Ensemble                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    db = SessionLocal()
    
    try:
        # ============================================================
        # STEP 1: Load Data
        # ============================================================
        print("\n" + "="*70)
        print("STEP 1: LOADING DATA")
        print("="*70)
        
        loader = AggregatedSignalLoader()
        df = loader.load_range()
        
        if df.empty:
            print("❌ No data found! Run: python backend/scripts/generate_test_data.py")
            return 1
        
        print(f"✅ Loaded {len(df)} days of data")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        # ============================================================
        # STEP 2: Feature Engineering
        # ============================================================
        print("\n" + "="*70)
        print("STEP 2: FEATURE ENGINEERING")
        print("="*70)
        
        engineer = TimeSeriesFeatureEngineer(df)
        features = engineer.build_features()
        
        print(f"✅ Created {features.shape[1]} features")
        
        # ============================================================
        # STEP 3: Prepare Data
        # ============================================================
        print("\n" + "="*70)
        print("STEP 3: PREPARING DATA")
        print("="*70)
        
        df_indexed = df.copy()
        df_indexed['date'] = pd.to_datetime(df_indexed['date'])
        df_indexed.set_index('date', inplace=True)
        
        print(f"✅ Data prepared for training")
        
        # ============================================================
        # STEP 4: Train Models
        # ============================================================
        print("\n" + "="*70)
        print("STEP 4: TRAINING ENSEMBLE MODELS")
        print("="*70)
        
        forecast_horizon = 7
        symptoms = ['total_fever', 'total_cough', 'total_gi']
        
        print(f"Horizon: {forecast_horizon} days")
        print(f"Symptoms: {symptoms}")
        
        ensemble_predictions = train_all_symptoms(
            df=df_indexed,
            features=features,
            symptoms=symptoms,
            horizon=forecast_horizon
        )
        
        print(f"\n✅ Generated {len(ensemble_predictions)} ensemble predictions")
        
        # ============================================================
        # STEP 5: Save to Database
        # ============================================================
        print("\n" + "="*70)
        print("STEP 5: SAVING TO DATABASE")
        print("="*70)
        
        saver = ForecastDatabaseSaver(db)
        forecast_date = date.today()
        
        saved_count = saver.save_predictions(
            predictions=ensemble_predictions,
            forecast_date=forecast_date
        )
        
        # ============================================================
        # STEP 6: Verify
        # ============================================================
        print("\n" + "="*70)
        print("STEP 6: VERIFICATION")
        print("="*70)
        
        verification = saver.verify_saved_predictions(forecast_date)
        
        if verification['success']:
            print(f"✅ Verification passed!")
            print(f"   Total predictions: {verification['total_predictions']}")
            print(f"   Symptoms: {verification['symptoms']}")
            print(f"   Predictions per symptom: {verification['predictions_per_symptom']}")
            print(f"   Date range: {verification['date_range']['start']} to {verification['date_range']['end']}")
        else:
            print(f"❌ Verification failed: {verification['message']}")
            return 1
        
        # ============================================================
        # SUCCESS
        # ============================================================
        print("\n" + "="*70)
        print("✅ TRAINING PIPELINE COMPLETE!")
        print("="*70)
        print(f"Forecast date: {forecast_date}")
        print(f"Predictions saved: {saved_count}")
        print(f"Horizon: {forecast_horizon} days")
        print(f"\nPredictions are now available via API:")
        print(f"   GET /api/v1/dashboard/forecast")
        print("="*70 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)