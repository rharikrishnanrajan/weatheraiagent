# ==============================================================================
# AgriPulse: SQLite Database Layer – Profiles, Threads & Messages
# ==============================================================================
# WHAT THIS FILE DOES:
# 1. Opens and manages a SQLite database file (farm_advisor.db).
# 2. Creates three tables on first run: farm_profile, chat_threads, chat_messages.
# 3. Inserts a default "Farmer Joe" profile so the app works out-of-the-box.
# 4. Provides CRUD helper functions used by the API endpoints and agent tools.
#
# BEGINNER TIP: SQLite is a simple file-based database – no server required.
# The entire database is stored in a single file: backend/data/farm_advisor.db.
# You can open it with any SQLite browser to inspect data during development.
#
# TABLE RELATIONSHIPS:
#   farm_profile (1 row)  →  stores farmer settings
#   chat_threads          →  stores conversation sessions
#   chat_messages         →  stores messages, linked to a thread via thread_id
# ==============================================================================

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings

logger = logging.getLogger("farm_advisor.db")


# ------------------------------------------------------------------------------
# DATABASE CONNECTION HELPER
# ------------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """
    Opens a new SQLite connection to the database file.
    
    - check_same_thread=False allows the connection to be shared across async threads
      (needed for FastAPI's async request handlers).
    - row_factory=sqlite3.Row enables column-name access (row["column_name"])
      instead of positional access (row[0]).

    Returns:
        sqlite3.Connection: An open database connection.
    """
    conn = sqlite3.connect(settings.SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row   # Access columns by name: row["crops"]
    return conn


# ------------------------------------------------------------------------------
# DATABASE INITIALIZATION
# ------------------------------------------------------------------------------
def init_db():
    """
    Creates all required database tables if they don't already exist,
    and seeds the farm_profile table with a default profile on first run.

    Called once at FastAPI startup (see app/main.py lifespan).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # TABLE 1: farm_profile
    # Stores a single row (id=1) representing the registered farm.
    # The CHECK constraint enforces id=1 so there is always exactly one profile.
    # ------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farm_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        farmer_name TEXT NOT NULL,
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        crops TEXT NOT NULL,          -- JSON array stored as text: '["Tomato","Corn"]'
        field_size_hectares REAL NOT NULL,
        soil_type TEXT NOT NULL,
        irrigation_type TEXT NOT NULL,
        preferred_language TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # ------------------------------------------------------------------
    # TABLE 2: chat_threads
    # Each row = one conversation session (like a chat thread in messaging apps).
    # ------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_threads (
        thread_id TEXT PRIMARY KEY,   -- UUID identifying this conversation
        title TEXT NOT NULL,          -- Auto-generated or user-assigned title
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # ------------------------------------------------------------------
    # TABLE 3: chat_messages
    # Each row = one message in a conversation (user or assistant turn).
    # ON DELETE CASCADE means: when a thread is deleted, its messages are too.
    # ------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT NOT NULL,
        role TEXT NOT NULL,           -- 'user' or 'assistant'
        content TEXT NOT NULL,        -- The message text
        sources TEXT,                 -- JSON array of cited document filenames
        tool_calls TEXT,              -- JSON array of tool execution records
        created_at TEXT NOT NULL,
        FOREIGN KEY(thread_id) REFERENCES chat_threads(thread_id) ON DELETE CASCADE
    );
    """)

    # ------------------------------------------------------------------
    # SEED DEFAULT PROFILE
    # Only insert if no profile row exists yet (first-time setup).
    # ------------------------------------------------------------------
    cursor.execute("SELECT id FROM farm_profile WHERE id = 1")
    if not cursor.fetchone():
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT INTO farm_profile (
            id, farmer_name, location_name, latitude, longitude, crops,
            field_size_hectares, soil_type, irrigation_type, preferred_language,
            notes, created_at, updated_at
        ) VALUES (
            1, 'Farmer Joe', 'Sacramento, California', 38.5816, -121.4944,
            ?, 12.5, 'Loamy', 'Drip', 'en',
            'Standard seasonal rotation with organic pest management practices.',
            ?, ?
        )
        """, (json.dumps(["Tomato", "Corn", "Wheat"]), now, now))
        # Note: crops is serialized as a JSON string because SQLite has no native array type

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully at %s", settings.SQLITE_DB_PATH)


# ------------------------------------------------------------------------------
# FARM PROFILE OPERATIONS
# ------------------------------------------------------------------------------
def get_farm_profile() -> Dict[str, Any]:
    """
    Fetches the single farm profile row from the database.

    Returns:
        dict: All profile fields. The 'crops' field is deserialized from JSON string to list.
        {}: Empty dict if no profile row found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farm_profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}   # No profile exists yet

    data = dict(row)
    # Deserialize crops from JSON string → Python list (e.g. '["Tomato"]' → ["Tomato"])
    data["crops"] = json.loads(data["crops"]) if data["crops"] else []
    return data


def update_farm_profile(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges new values into the existing farm profile and persists to SQLite.

    Args:
        updates: Dictionary of field names to new values.
                 Only keys that exist in the profile schema are applied.

    Returns:
        dict: The full updated profile after changes.
    """
    # Load current values first so we can merge partial updates
    current = get_farm_profile()
    if not current:
        init_db()
        current = get_farm_profile()

    # Apply each provided update to the in-memory profile dict
    for k, v in updates.items():
        if v is not None and k in current:
            current[k] = v   # Overwrite only provided fields

    # Stamp the update time
    now = datetime.utcnow().isoformat()
    current["updated_at"] = now

    # Serialize crops list back to JSON string for storage
    crops_json = json.dumps(current["crops"])

    conn = get_connection()
    cursor = conn.cursor()
    # Write all fields with a full UPDATE (SQLite doesn't support partial column writes cleanly)
    cursor.execute("""
    UPDATE farm_profile SET
        farmer_name = ?,
        location_name = ?,
        latitude = ?,
        longitude = ?,
        crops = ?,
        field_size_hectares = ?,
        soil_type = ?,
        irrigation_type = ?,
        preferred_language = ?,
        notes = ?,
        updated_at = ?
    WHERE id = 1
    """, (
        current["farmer_name"],
        current["location_name"],
        current["latitude"],
        current["longitude"],
        crops_json,
        current["field_size_hectares"],
        current["soil_type"],
        current["irrigation_type"],
        current["preferred_language"],
        current.get("notes", ""),
        now
    ))
    conn.commit()
    conn.close()
    return current


# ------------------------------------------------------------------------------
# CHAT THREAD OPERATIONS
# ------------------------------------------------------------------------------
def create_or_update_thread(thread_id: str, title: Optional[str] = None):
    """
    Creates a new conversation thread or updates the timestamp on an existing one.
    Called automatically whenever a new message is sent.

    Args:
        thread_id: UUID string identifying the conversation.
        title: Optional custom title for the thread (e.g. first user message preview).
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Check if this thread already exists
    cursor.execute("SELECT thread_id, title FROM chat_threads WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()

    if row:
        # Thread exists – update the timestamp and optionally the title
        new_title = title if title else row["title"]
        cursor.execute(
            "UPDATE chat_threads SET updated_at = ?, title = ? WHERE thread_id = ?",
            (now, new_title, thread_id)
        )
    else:
        # New thread – create it with the provided or default title
        new_title = title or "New Advisory Session"
        cursor.execute(
            "INSERT INTO chat_threads (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, new_title, now, now)
        )

    conn.commit()
    conn.close()


def list_threads() -> List[Dict[str, Any]]:
    """
    Returns all chat threads ordered by most recently updated.
    Also includes a message_count for each thread (from a LEFT JOIN).

    Returns:
        List[dict]: Each dict has thread_id, title, created_at, updated_at, message_count.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.thread_id, t.title, t.created_at, t.updated_at, COUNT(m.id) as message_count
    FROM chat_threads t
    LEFT JOIN chat_messages m ON t.thread_id = m.thread_id
    GROUP BY t.thread_id
    ORDER BY t.updated_at DESC
    """)   # LEFT JOIN: threads with no messages still appear (message_count = 0)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all messages in a thread in chronological order.
    Deserializes sources and tool_calls JSON fields back into Python objects.

    Args:
        thread_id: UUID identifying the conversation to retrieve.

    Returns:
        List[dict]: Message records ordered by id ascending (oldest first).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT role, content, sources, tool_calls, created_at
    FROM chat_messages
    WHERE thread_id = ?
    ORDER BY id ASC
    """, (thread_id,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        # Deserialize JSON-encoded fields back to Python lists
        item["sources"] = json.loads(item["sources"]) if item["sources"] else []
        item["tool_calls"] = json.loads(item["tool_calls"]) if item["tool_calls"] else []
        result.append(item)
    return result


# ------------------------------------------------------------------------------
# MESSAGE OPERATIONS
# ------------------------------------------------------------------------------
def add_message(
    thread_id: str,
    role: str,
    content: str,
    sources: Optional[List[str]] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None
):
    """
    Persists a single chat message to the database.
    Automatically creates or updates the parent thread record.

    Args:
        thread_id: UUID of the conversation this message belongs to.
        role: Either 'user' or 'assistant'.
        content: The full text of the message.
        sources: Optional list of cited source filenames (e.g. ['irrigation_guide.md']).
        tool_calls: Optional list of tool execution records from the agent.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Ensure the parent thread row exists before inserting the message
    create_or_update_thread(thread_id)

    cursor.execute("""
    INSERT INTO chat_messages (thread_id, role, content, sources, tool_calls, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        thread_id,
        role,
        content,
        json.dumps(sources or []),      # Serialize list → JSON string
        json.dumps(tool_calls or []),   # Serialize list → JSON string
        now
    ))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------------------
# THREAD DELETION
# ------------------------------------------------------------------------------
def delete_thread(thread_id: str):
    """
    Permanently removes a thread and ALL its messages from the database.
    The ON DELETE CASCADE constraint on chat_messages handles the cascade automatically,
    but we also delete messages explicitly for clarity.

    Args:
        thread_id: UUID of the thread to remove.
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Delete messages first (explicit, though cascade would handle it too)
    cursor.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
    cursor.execute("DELETE FROM chat_threads WHERE thread_id = ?", (thread_id,))
    conn.commit()
    conn.close()
