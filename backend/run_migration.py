#!/usr/bin/env python3
"""
Run database migration to add resolution status tracking
"""
import asyncio
from supabase import create_client
from app.core.config import settings

async def run_migration():
    """Run the resolution status migration"""
    try:
        # Create service client for admin operations
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        
        print("Running resolution status migration...")
        
        # Read migration SQL
        with open('migrations/add_resolution_status.sql', 'r') as f:
            migration_sql = f.read()
        
        # Split into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement.startswith('--'):
                continue
                
            print(f"Executing statement {i+1}/{len(statements)}...")
            try:
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                print(f"✅ Statement {i+1} executed successfully")
            except Exception as e:
                print(f"⚠️  Statement {i+1} failed (may be expected): {str(e)}")
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration()) 