#!/usr/bin/env python3
"""
AtomForge Database Management
SQLite database for script storage and file operations
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database file path - store in the API directory
DB_PATH = Path(__file__).parent.parent / "data" / "atomforge.db"

def init_database():
    """Initialize the AtomForge database and create tables"""
    try:
        # Ensure data directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    UNIQUE(name)
                );

                CREATE INDEX IF NOT EXISTS idx_scripts_name ON scripts(name);
                CREATE INDEX IF NOT EXISTS idx_scripts_updated_at ON scripts(updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_scripts_favorite ON scripts(is_favorite DESC);

                -- Trigger to update updated_at timestamp
                CREATE TRIGGER IF NOT EXISTS update_script_timestamp
                AFTER UPDATE ON scripts
                FOR EACH ROW
                BEGIN
                    UPDATE scripts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END;
            """)

        logger.info(f"Database initialized successfully at {DB_PATH}")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

@contextmanager
def get_db_connection():
    """Get a database connection with proper cleanup"""
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def test_database_connection():
    """Test database connectivity and basic operations"""
    try:
        with get_db_connection() as conn:
            result = conn.execute("SELECT COUNT(*) as count FROM scripts").fetchone()
            logger.info(f"Database connection successful. Script count: {result['count']}")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False