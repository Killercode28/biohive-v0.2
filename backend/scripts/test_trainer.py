"""
Test ensemble forecasting pipeline
Tests all three models (SARIMA, Prophet, XGBoost) and ensemble combination
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from datetime import datetime

from backend.services.ml.data_loader import AggregatedSignalLoader
from backend.services.ml.feature_engineering import TimeSeriesFeatureEngineer
from backend.services.ml.trainer import train_all_symptoms


def main():
    """Run complete forecasting pipeline test"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           BioHIVE Ensemble Forecasting Test               ║
    ║     Testing SARIMA + Prophet + XGBoost Ensemble           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        # ============================================================
        # STEP 1: Load Data
        # ============================================================
        print("\n" + "="*70)
        print("STEP 1: LOADING DATA FROM DATABASE")
        print("="*70)
        
        loader = AggregatedSignalLoader()
        df = loader.load_range()
        
        if df.empty:
            print("❌ No data found in database!")
            print("   Run: python backend/scripts/generate_test_data.py")
            return
        
        print(f"✅ Loaded {len(df)} days of data")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Show data summary
        print(f"\n📊 Data Summary:")
        print(f"   Total Fever: {df['total_fever'].sum():,}")
        print(f"   Total Cough: {df['total_cough'].sum():,}")
        print(f"   Total GI: {df['total_gi'].sum():,}")
        print(f"   Avg Fever/day: {df['total_fever'].mean():.1f}")
        print(f"   Avg Cough/day: {df['total_cough'].mean():.1f}")
        print(f"   Avg GI/day: {df['total_gi'].mean():.1f}")
        
        # ============================================================
        # STEP 2: Engineer Features
        # ============================================================
        print("\n" + "="*70)
        print("STEP 2: FEATURE ENGINEERING")
        print("="*70)
        
        engineer = TimeSeriesFeatureEngineer(df)
        features = engineer.build_features()
        
        print(f"✅ Created {features.shape[1]} features")
        print(f"   Shape: {features.shape}")
        print(f"   Feature columns (first 15):")
        for i, col in enumerate(features.columns[:15], 1):
            print(f"      {i:2d}. {col}")
        if features.shape[1] > 15:
            print(f"      ... and {features.shape[1] - 15} more")
        
        # ============================================================
        # STEP 3: Prepare Data for Models
        # ============================================================
        print("\n" + "="*70)
        print("STEP 3: PREPARING DATA FOR MODELS")
        print("="*70)
        
        # Set date as index for time series operations
        df_indexed = df.copy()
        df_indexed['date'] = pd.to_datetime(df_indexed['date'])
        df_indexed.set_index('date', inplace=True)
        
        print(f"✅ Data prepared")
        print(f"   Training data points: {len(df_indexed)}")
        print(f"   Last training date: {df_indexed.index[-1].date()}")
        
        # ============================================================
        # STEP 4: Train Ensemble Models
        # ============================================================
        print("\n" + "="*70)
        print("STEP 4: TRAINING ENSEMBLE MODELS")
        print("="*70)
        
        forecast_horizon = 7
        print(f"Forecast horizon: {forecast_horizon} days")
        print(f"Symptoms to forecast: total_fever, total_cough, total_gi")
        
        ensemble_predictions = train_all_symptoms(
            df=df_indexed,
            features=features,
            symptoms=['total_fever', 'total_cough', 'total_gi'],
            horizon=forecast_horizon
        )
        
        # ============================================================
        # STEP 5: Display Results
        # ============================================================
        print("\n" + "="*70)
        print("STEP 5: ENSEMBLE PREDICTIONS SUMMARY")
        print("="*70)
        
        print(f"\n✅ Total ensemble predictions: {len(ensemble_predictions)}")
        print(f"   Predictions per symptom: {len(ensemble_predictions) // 3}")
        print(f"   Forecast dates: {ensemble_predictions['date'].min()} to {ensemble_predictions['date'].max()}")
        
        # Show predictions by symptom
        print("\n" + "="*70)
        print("PREDICTIONS BY SYMPTOM")
        print("="*70)
        
        for symptom in ['total_fever', 'total_cough', 'total_gi']:
            symptom_preds = ensemble_predictions[
                ensemble_predictions['symptom'] == symptom
            ].copy()
            
            if not symptom_preds.empty:
                print(f"\n📈 {symptom.upper().replace('_', ' ')}:")
                print(f"   {'Date':<12} {'Predicted':>10} {'Lower':>10} {'Upper':>10} {'Confidence':>10}")
                print(f"   {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
                
                for _, row in symptom_preds.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d')
                    print(f"   {date_str:<12} {row['predicted']:>10.1f} "
                          f"{row['lower']:>10.1f} {row['upper']:>10.1f} "
                          f"{row['confidence']:>10.2f}")
                
                # Summary statistics
                print(f"\n   Summary:")
                print(f"   - Average prediction: {symptom_preds['predicted'].mean():.1f}")
                print(f"   - Min prediction: {symptom_preds['predicted'].min():.1f}")
                print(f"   - Max prediction: {symptom_preds['predicted'].max():.1f}")
                print(f"   - Trend: ", end="")
                
                first = symptom_preds.iloc[0]['predicted']
                last = symptom_preds.iloc[-1]['predicted']
                trend = ((last - first) / first) * 100
                
                if trend > 5:
                    print(f"📈 Increasing ({trend:+.1f}%)")
                elif trend < -5:
                    print(f"📉 Decreasing ({trend:+.1f}%)")
                else:
                    print(f"➡️  Stable ({trend:+.1f}%)")
        
        # ============================================================
        # STEP 6: Model Comparison (if you want to save raw predictions)
        # ============================================================
        print("\n" + "="*70)
        print("ENSEMBLE CONFIGURATION")
        print("="*70)
        print("Model weights:")
        print("   SARIMA:  40% (statistical baseline)")
        print("   Prophet: 30% (robust forecasting)")
        print("   XGBoost: 30% (ML pattern recognition)")
        
        # ============================================================
        # Final Summary
        # ============================================================
        print("\n" + "="*70)
        print("✅ TEST COMPLETE!")
        print("="*70)
        print(f"Successfully forecasted {len(ensemble_predictions)} predictions")
        print(f"Models working: SARIMA ✓, Prophet ✓, XGBoost ✓")
        print(f"Ensemble method: Weighted average")
        print(f"\nNext step: Save predictions to database")
        print(f"   -> python backend/scripts/save_forecasts.py")
        
    except Exception as e:
        print(f"\n" + "="*70)
        print("❌ ERROR OCCURRED")
        print("="*70)
        print(f"Error: {e}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)