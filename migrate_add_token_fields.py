#!/usr/bin/env python3
"""
Database migration script to add token tracking fields to APIUsage table

This script adds the following columns to the api_usage table:
- prompt_tokens: Number of tokens in the prompt
- completion_tokens: Number of tokens in the completion
- total_tokens: Total tokens used (prompt + completion)

Usage:
    python3 migrate_add_token_fields.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vigint.models import db
from flask import Flask
from config import config


def create_app():
    """Create Flask app for database migration"""
    app = Flask(__name__)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app


def migrate_database():
    """Add token tracking fields to api_usage table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect, Integer
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('api_usage')]
            
            if 'prompt_tokens' in columns:
                print("✅ Token fields already exist in api_usage table")
                return True
            
            print("🔄 Adding token tracking fields to api_usage table...")
            
            # Add the new columns using raw SQL
            with db.engine.connect() as conn:
                # Add prompt_tokens column
                conn.execute(db.text(
                    "ALTER TABLE api_usage ADD COLUMN prompt_tokens INTEGER DEFAULT 0"
                ))
                print("  ✅ Added prompt_tokens column")
                
                # Add completion_tokens column
                conn.execute(db.text(
                    "ALTER TABLE api_usage ADD COLUMN completion_tokens INTEGER DEFAULT 0"
                ))
                print("  ✅ Added completion_tokens column")
                
                # Add total_tokens column
                conn.execute(db.text(
                    "ALTER TABLE api_usage ADD COLUMN total_tokens INTEGER DEFAULT 0"
                ))
                print("  ✅ Added total_tokens column")
                
                conn.commit()
            
            print("\n✅ Migration completed successfully!")
            print("\n📊 Token tracking is now enabled for RTSP stream analysis")
            print("   - Token counts will be logged for each Gemini API call")
            print("   - Token usage will be included in billing reports")
            print("   - Use the token data for cost optimization and analytics")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("Database Migration: Add Token Tracking Fields")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration successful! You can now track token usage.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Migration failed. Please check the errors above.")
        print("=" * 60)
        sys.exit(1)
