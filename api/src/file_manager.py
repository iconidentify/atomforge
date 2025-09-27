#!/usr/bin/env python3
"""
AtomForge File Manager
Handles script storage and file operations
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from database import get_db_connection

logger = logging.getLogger(__name__)

class Script:
    """Represents a saved script"""
    def __init__(self, id: Optional[int] = None, name: str = "", content: str = "",
                 created_at: Optional[str] = None, updated_at: Optional[str] = None,
                 is_favorite: bool = False):
        self.id = id
        self.name = name
        self.content = content
        self.created_at = created_at
        self.updated_at = updated_at
        self.is_favorite = is_favorite

    def to_dict(self) -> Dict[str, Any]:
        """Convert script to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_favorite': self.is_favorite,
            'content_length': len(self.content) if self.content else 0
        }

    @classmethod
    def from_db_row(cls, row) -> 'Script':
        """Create Script instance from database row"""
        return cls(
            id=row['id'],
            name=row['name'],
            content=row['content'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            is_favorite=bool(row['is_favorite'])
        )

class FileManager:
    """Manages script file operations"""

    @staticmethod
    def list_scripts(search: Optional[str] = None, favorites_only: bool = False) -> List[Script]:
        """List all scripts, optionally filtered by search term or favorites"""
        try:
            with get_db_connection() as conn:
                query = "SELECT * FROM scripts WHERE 1=1"
                params = []

                if search:
                    query += " AND (name LIKE ? OR content LIKE ?)"
                    search_term = f"%{search}%"
                    params.extend([search_term, search_term])

                if favorites_only:
                    query += " AND is_favorite = 1"

                query += " ORDER BY is_favorite DESC, updated_at DESC"

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                scripts = [Script.from_db_row(row) for row in rows]
                logger.info(f"Retrieved {len(scripts)} scripts (search: {search}, favorites_only: {favorites_only})")
                return scripts

        except Exception as e:
            logger.error(f"Failed to list scripts: {e}")
            return []

    @staticmethod
    def get_script(script_id: int) -> Optional[Script]:
        """Get a script by ID"""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
                row = cursor.fetchone()

                if row:
                    script = Script.from_db_row(row)
                    logger.info(f"Retrieved script: {script.name} (ID: {script_id})")
                    return script
                else:
                    logger.warning(f"Script not found: ID {script_id}")
                    return None

        except Exception as e:
            logger.error(f"Failed to get script {script_id}: {e}")
            return None

    @staticmethod
    def save_script(name: str, content: str, script_id: Optional[int] = None) -> Optional[Script]:
        """Save a script (create new or update existing)"""
        try:
            with get_db_connection() as conn:
                if script_id:
                    # Update existing script
                    conn.execute(
                        "UPDATE scripts SET name = ?, content = ? WHERE id = ?",
                        (name, content, script_id)
                    )
                    logger.info(f"Updated script: {name} (ID: {script_id})")

                    # Retrieve within the same transaction
                    cursor = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
                    row = cursor.fetchone()
                    if row:
                        return Script.from_db_row(row)
                    else:
                        logger.error(f"Script not found after update: ID {script_id}")
                        return None
                else:
                    # Create new script
                    cursor = conn.execute(
                        "INSERT INTO scripts (name, content) VALUES (?, ?)",
                        (name, content)
                    )
                    script_id = cursor.lastrowid
                    logger.info(f"Created new script: {name} (ID: {script_id})")

                    # Retrieve within the same transaction
                    cursor = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,))
                    row = cursor.fetchone()
                    if row:
                        return Script.from_db_row(row)
                    else:
                        logger.error(f"Script not found after creation: ID {script_id}")
                        return None

        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"Script name already exists: {name}")
                raise ValueError(f"A script named '{name}' already exists")
            else:
                logger.error(f"Database integrity error saving script: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to save script '{name}': {e}")
            return None

    @staticmethod
    def delete_script(script_id: int) -> bool:
        """Delete a script by ID"""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))

                if cursor.rowcount > 0:
                    logger.info(f"Deleted script ID: {script_id}")
                    return True
                else:
                    logger.warning(f"Script not found for deletion: ID {script_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to delete script {script_id}: {e}")
            return False

    @staticmethod
    def duplicate_script(script_id: int, new_name: Optional[str] = None) -> Optional[Script]:
        """Duplicate an existing script"""
        try:
            original_script = FileManager.get_script(script_id)
            if not original_script:
                return None

            # Generate new name if not provided
            if not new_name:
                new_name = f"{original_script.name} (Copy)"

                # Handle name conflicts by adding numbers
                counter = 1
                while FileManager.script_name_exists(new_name):
                    counter += 1
                    new_name = f"{original_script.name} (Copy {counter})"

            return FileManager.save_script(new_name, original_script.content)

        except Exception as e:
            logger.error(f"Failed to duplicate script {script_id}: {e}")
            return None

    @staticmethod
    def toggle_favorite(script_id: int) -> Optional[bool]:
        """Toggle favorite status of a script"""
        try:
            with get_db_connection() as conn:
                # Get current favorite status
                cursor = conn.execute("SELECT is_favorite FROM scripts WHERE id = ?", (script_id,))
                row = cursor.fetchone()

                if not row:
                    logger.warning(f"Script not found for favorite toggle: ID {script_id}")
                    return None

                new_status = not bool(row['is_favorite'])
                conn.execute("UPDATE scripts SET is_favorite = ? WHERE id = ?", (new_status, script_id))

                logger.info(f"Toggled favorite for script ID {script_id}: {new_status}")
                return new_status

        except Exception as e:
            logger.error(f"Failed to toggle favorite for script {script_id}: {e}")
            return None

    @staticmethod
    def script_name_exists(name: str) -> bool:
        """Check if a script name already exists"""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM scripts WHERE name = ?", (name,))
                result = cursor.fetchone()
                return result['count'] > 0

        except Exception as e:
            logger.error(f"Failed to check script name existence: {e}")
            return False

    @staticmethod
    def get_recent_scripts(limit: int = 10) -> List[Script]:
        """Get recently updated scripts"""
        try:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM scripts ORDER BY updated_at DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()

                scripts = [Script.from_db_row(row) for row in rows]
                logger.info(f"Retrieved {len(scripts)} recent scripts")
                return scripts

        except Exception as e:
            logger.error(f"Failed to get recent scripts: {e}")
            return []

# Import sqlite3 here to avoid circular import issues
import sqlite3