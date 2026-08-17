import sqlite3
import os
import time
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("JarvisMemory")

DB_PATH = os.getenv("MEMORY_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_memory.db"))

def init_db():
    """Initialize persistent SQLite database tables for long-term memory and history."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # 1. Long-term key-value / semantic memory facts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    category TEXT,
                    key TEXT,
                    value TEXT,
                    created_at REAL,
                    updated_at REAL,
                    UNIQUE(user_id, category, key)
                )
            """)
            # 2. Multi-turn conversation messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()
            logger.info("✅ SQLite Memory Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize memory DB: {e}")

# Initialize on module load
init_db()

class MemoryManager:
    """Manages persistent long-term memories and conversation histories across sessions and restarts."""

    @staticmethod
    def save_fact(user_id: int, key: str, value: str, category: str = "general") -> str:
        """Save or update a long-term memory fact about the user, their preferences, projects, or instructions."""
        now = time.time()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO memories (user_id, category, key, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, category, key) DO UPDATE SET
                        value=excluded.value,
                        updated_at=excluded.updated_at
                """, (user_id, category.lower().strip(), key.strip(), value.strip(), now, now))
                conn.commit()
                logger.info(f"💾 Memory saved for user {user_id}: [{category}] {key} = {value}")
                return f"Memory stored permanently: [{category}] {key}: {value}"
        except Exception as e:
            logger.error(f"Error saving memory fact: {e}")
            return f"Error saving memory: {str(e)}"

    @staticmethod
    def get_memories_summary(user_id: int) -> str:
        """Retrieve all remembered facts about a user as a structured string for prompt context."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT category, key, value FROM memories
                    WHERE user_id = ? OR user_id = 0
                    ORDER BY category, key
                """, (user_id,))
                rows = cursor.fetchall()
                if not rows:
                    return "No specific long-term memories recorded yet."
                
                lines = []
                for cat, k, v in rows:
                    lines.append(f"• [{cat.upper()}] {k}: {v}")
                return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error reading memories: {e}")
            return "No memories available."

    @staticmethod
    def search_memories(user_id: int, query: str) -> List[Dict[str, Any]]:
        """Search stored long-term memories matching a keyword."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                like_query = f"%{query}%"
                cursor.execute("""
                    SELECT category, key, value, updated_at FROM memories
                    WHERE (user_id = ? OR user_id = 0)
                      AND (key LIKE ? OR value LIKE ? OR category LIKE ?)
                    ORDER BY updated_at DESC
                """, (user_id, like_query, like_query, like_query))
                rows = cursor.fetchall()
                results = []
                for cat, k, v, ut in rows:
                    results.append({"category": cat, "key": k, "value": v, "updated_at": ut})
                return results
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []

    @staticmethod
    def delete_memory(user_id: int, key: str, category: str = "general") -> str:
        """Delete a stored memory."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM memories WHERE user_id = ? AND category = ? AND key = ?
                """, (user_id, category.lower().strip(), key.strip()))
                conn.commit()
                return f"Deleted memory '{key}' from category '{category}'."
        except Exception as e:
            return f"Error deleting memory: {str(e)}"

    @staticmethod
    def record_message(user_id: int, role: str, content: str):
        """Save a message turn to persistent history."""
        now = time.time()
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversation_history (user_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (user_id, role, content, now))
                conn.commit()
        except Exception as e:
            logger.error(f"Error recording message history: {e}")

    @staticmethod
    def get_recent_history(user_id: int, limit: int = 24) -> List[Dict[str, str]]:
        """Get the latest N conversation messages formatted for Gemini chat history."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT role, content FROM conversation_history
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                """, (user_id, limit))
                rows = cursor.fetchall()
                # Reverse so they are in chronological order
                history = []
                for role, content in reversed(rows):
                    history.append({"role": role, "content": content})
                return history
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return []

    @staticmethod
    def search_full_chat_history(user_id: int, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search across every single message ever sent or discussed in past conversations."""
        import datetime
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                like_query = f"%{query}%"
                cursor.execute("""
                    SELECT role, content, timestamp FROM conversation_history
                    WHERE (user_id = ? OR user_id = 0)
                      AND content LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, like_query, limit))
                rows = cursor.fetchall()
                results = []
                for role, content, ts in rows:
                    dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                    speaker = "User" if role == "user" else "Jarvis"
                    results.append({
                        "speaker": speaker,
                        "date": dt_str,
                        "content": content
                    })
                return results
        except Exception as e:
            logger.error(f"Error searching chat history: {e}")
            return []

    @staticmethod
    def get_history_stats(user_id: int) -> Dict[str, Any]:
        """Get statistics about user's lifelong conversation archive."""
        import datetime
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), MIN(timestamp) FROM conversation_history WHERE user_id = ? OR user_id = 0", (user_id,))
                msg_count, min_ts = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(*) FROM memories WHERE user_id = ? OR user_id = 0", (user_id,))
                memory_count = cursor.fetchone()[0]

                first_date = datetime.datetime.fromtimestamp(min_ts).strftime("%Y-%m-%d") if min_ts else "Today"
                return {
                    "total_messages": msg_count or 0,
                    "total_memories": memory_count or 0,
                    "first_chat_date": first_date
                }
        except Exception as e:
            logger.error(f"Error getting history stats: {e}")
            return {"total_messages": 0, "total_memories": 0, "first_chat_date": "N/A"}
