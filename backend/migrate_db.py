#!/usr/bin/env python3
"""
Database migration script to add esi_classification column
"""

import os
import sys
from supabase import create_client
from app.core.config import settings

def migrate_database():
    """Add esi_classification column to symptom_logs table"""
    try:
        # Create service client for admin operations
        supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
        
        # Check if column exists
        try:
            result = supabase.table('symptom_logs').select('esi_classification').limit(1).execute()
            print("✅ esi_classification column already exists")
            return True
        except Exception as e:
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                print("❌ esi_classification column does not exist, adding it...")
                
                # Add the column using raw SQL
                # Note: Supabase doesn't support direct DDL through the client
                # This would need to be run manually in the Supabase SQL editor
                sql_command = """
                ALTER TABLE public.symptom_logs ADD COLUMN esi_classification TEXT;
                """
                
                print("Please run this SQL command in your Supabase SQL editor:")
                print(sql_command)
                return False
            else:
                print(f"Error checking column: {e}")
                return False
                
    except Exception as e:
        print(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Starting database migration...")
    success = migrate_database()
    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed - manual intervention required")
        sys.exit(1) 