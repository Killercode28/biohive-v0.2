"""
Test that saved forecasts can be retrieved via the forecasting service
"""

import sys
sys.path.insert(0, '.')

from backend.store import SessionLocal
from backend.services.forecasting import ForecastService


def main():
    """Test forecast retrieval"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         Test Saved Forecasts Retrieval                    ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    db = SessionLocal()
    
    try:
        service = ForecastService(db)
        
        # Get forecast summary
        print("\n📊 Forecast Summary:")
        print("="*70)
        summary = service.get_forecast_summary()
        
        if summary['total_forecasts'] == 0:
            print("❌ No forecasts found in database!")
            print("   Run: python backend/scripts/run_training.py")
            return 1
        
        print(f"Total forecasts: {summary['total_forecasts']}")
        print(f"Latest forecast date: {summary['latest_forecast_date']}")
        print(f"Available models: {summary['available_models']}")
        print(f"Symptoms covered: {summary['symptoms_covered']}")
        
        # Get latest forecast for each symptom
        print("\n📈 Latest Forecasts:")
        print("="*70)
        
        for symptom in ['fever', 'cough', 'gi']:
            print(f"\n{symptom.upper()}:")
            try:
                forecast = service.get_forecast(symptom=symptom, days=7)
                
                if forecast['forecasts'][symptom]:
                    preds = forecast['forecasts'][symptom]
                    print(f"  Predictions: {len(preds)}")
                    print(f"  First prediction: {preds[0]}")
                else:
                    print(f"  No predictions found")
                    
            except Exception as e:
                print(f"  Error: {e}")
        
        print("\n✅ Forecast retrieval test complete!")
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