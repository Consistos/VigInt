#!/usr/bin/env python3
"""Add token tracking columns to api_usage table"""

import os
from sqlalchemy import create_engine, text
from config import config

def migrate():
    """Add missing columns to api_usage table"""
    db_url = config.database_url
    engine = create_engine(db_url)
    
    print(f"Connecting to database: {db_url[:30]}...")
    
    with engine.connect() as conn:
        # Add columns if they don't exist
        try:
            conn.execute(text("""
                ALTER TABLE api_usage 
                ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS completion_tokens INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS total_tokens INTEGER DEFAULT 0;
            """))
            conn.commit()
            print("✅ Migration successful! Added token tracking columns.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == '__main__':
    migrate()
