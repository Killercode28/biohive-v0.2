"""
Script to generate synthetic test data for BioHIVE
Run this once to populate the database with historical data for ML training

Usage:
    python backend/scripts/generate_test_data.py [--days DAYS] [--nodes NODES] [--seed SEED]

Examples:
    python backend/scripts/generate_test_data.py
    python backend/scripts/generate_test_data.py --days 60 --nodes 10
    python backend/scripts/generate_test_data.py --days 90 --seed 42
"""

import sys
import argparse
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.store import SessionLocal, init_db
from backend.services.ml.data_generator import SyntheticDataGenerator


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate synthetic surveillance data for BioHIVE'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days to generate (default: 90)'
    )
    parser.add_argument(
        '--nodes',
        type=int,
        default=8,
        help='Number of participating nodes/clinics (default: 8)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Random seed for reproducibility (default: None)'
    )
    
    return parser.parse_args()


def main():
    """Generate synthetic data and save to database"""
    
    # Parse arguments
    args = parse_arguments()
    
    print("""
    ╔═══════════════════════════════════════════╗
    ║   BioHIVE Synthetic Data Generator        ║
    ║   Generating historical surveillance data ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # Initialize database
    print("🔧 Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create generator
        generator = SyntheticDataGenerator(db)
        
        # Generate data
        result = generator.generate_and_save(
            days=args.days,
            participating_nodes=args.nodes,
            seed=args.seed
        )
        
        # Summary
        print(f"\n" + "="*50)
        print(f"✅ DATA GENERATION COMPLETE!")
        print(f"="*50)
        print(f"📊 {result['days_saved']} records saved to database")
        print(f"📅 Date range: {result['date_range']['start']} to {result['date_range']['end']}")
        print(f"🎯 Ready for ML model training")
        
        if result['days_saved'] == 0:
            print(f"\n⚠️  No new data was added (dates already exist)")
            print(f"   To regenerate, delete existing data first:")
            print(f"   sqlite3 biohive.db 'DELETE FROM aggregated_signals;'")
        
    except Exception as e:
        print(f"\n❌ Error during data generation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        db.close()
    
    print("\n🎯 Next steps:")
    print("   1. Verify data: sqlite3 biohive.db 'SELECT COUNT(*) FROM aggregated_signals;'")
    print("   2. Run training: python backend/scripts/run_training.py")
    print()


if __name__ == "__main__":
    main()