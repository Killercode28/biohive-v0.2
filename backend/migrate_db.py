"""
Database Migration Script
Migrates from hard limits to warning-based system
Run: python migrate_db.py
"""

import sqlite3
import os

def migrate_database():
    """
    Add new columns to daily_reports table:
    - suspicion_score (INTEGER)
    - requires_review (BOOLEAN)
    """
    
    db_path = 'biohive.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        print("💡 Run 'python app.py' first to create the database")
        return
    
    print("🔄 Starting database migration...")
    print(f"📁 Database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(daily_reports)")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations_needed = []
        
        if 'suspicion_score' not in columns:
            migrations_needed.append('suspicion_score')
        
        if 'requires_review' not in columns:
            migrations_needed.append('requires_review')
        
        if not migrations_needed:
            print("✅ Database already up to date!")
            conn.close()
            return
        
        print(f"📝 Need to add columns: {', '.join(migrations_needed)}")
        
        # Add suspicion_score column
        if 'suspicion_score' in migrations_needed:
            print("   Adding suspicion_score column...")
            cursor.execute("""
                ALTER TABLE daily_reports 
                ADD COLUMN suspicion_score INTEGER DEFAULT 0
            """)
            print("   ✅ suspicion_score column added")
        
        # Add requires_review column
        if 'requires_review' in migrations_needed:
            print("   Adding requires_review column...")
            cursor.execute("""
                ALTER TABLE daily_reports 
                ADD COLUMN requires_review BOOLEAN DEFAULT 0
            """)
            print("   ✅ requires_review column added")
        
        # Remove old check constraints (if possible in SQLite)
        # Note: SQLite doesn't support DROP CONSTRAINT, so we note it
        print("\n⚠️  Note: Old check constraints still exist in schema")
        print("   They won't affect new data, but you may see warnings")
        print("   For clean migration, consider recreating the database")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        print("🚀 You can now restart your server")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("💡 Try deleting biohive.db and running 'python app.py' to recreate")


def recreate_database():
    """
    Complete database recreation (clean slate)
    CAUTION: This will delete ALL existing data!
    """
    
    db_path = 'biohive.db'
    
    print("🚨 WARNING: This will DELETE all existing data!")
    response = input("Are you sure? Type 'yes' to continue: ")
    
    if response.lower() != 'yes':
        print("❌ Aborted")
        return
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Deleted {db_path}")
    
    print("✅ Database deleted")
    print("💡 Run 'python app.py' to recreate with new schema")


if __name__ == "__main__":
    print("=" * 60)
    print("  BioHIVE Database Migration Tool")
    print("=" * 60)
    print()
    print("Choose an option:")
    print("1. Migrate existing database (keeps data)")
    print("2. Recreate database (DELETES all data)")
    print("3. Exit")
    print()
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == '1':
        migrate_database()
    elif choice == '2':
        recreate_database()
    elif choice == '3':
        print("👋 Exiting")
    else:
        print("❌ Invalid choice")