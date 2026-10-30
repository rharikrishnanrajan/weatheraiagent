import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings

logger = logging.getLogger("farm_advisor.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Farm Profile Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farm_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        farmer_name TEXT NOT NULL,
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        crops TEXT NOT NULL,
        field_size_hectares REAL NOT NULL,
        soil_type TEXT NOT NULL,
        irrigation_type TEXT NOT NULL,
        preferred_language TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 2. Chat Threads Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_threads (
        thread_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 3. Chat Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources TEXT,
        tool_calls TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(thread_id) REFERENCES chat_threads(thread_id) ON DELETE CASCADE
    );
    """)

    # Insert default farm profile if not exists
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

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully at %s", settings.SQLITE_DB_PATH)

def get_farm_profile() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM farm_profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {}
        
    data = dict(row)
    data["crops"] = json.loads(data["crops"]) if data["crops"] else []
    return data

def update_farm_profile(updates: Dict[str, Any]) -> Dict[str, Any]:
    current = get_farm_profile()
    if not current:
        init_db()
        current = get_farm_profile()

    for k, v in updates.items():
        if v is not None and k in current:
            current[k] = v

    now = datetime.utcnow().isoformat()
    current["updated_at"] = now
    crops_json = json.dumps(current["crops"])

    conn = get_connection()
    cursor = conn.cursor()
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

def create_or_update_thread(thread_id: str, title: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("SELECT thread_id, title FROM chat_threads WHERE thread_id = ?", (thread_id,))
    row = cursor.fetchone()
    if row:
        new_title = title if title else row["title"]
        cursor.execute("UPDATE chat_threads SET updated_at = ?, title = ? WHERE thread_id = ?", (now, new_title, thread_id))
    else:
        new_title = title or "New Advisory Session"
        cursor.execute("INSERT INTO chat_threads (thread_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                       (thread_id, new_title, now, now))
    conn.commit()
    conn.close()

def list_threads() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.thread_id, t.title, t.created_at, t.updated_at, COUNT(m.id) as message_count
    FROM chat_threads t
    LEFT JOIN chat_messages m ON t.thread_id = m.thread_id
    GROUP BY t.thread_id
    ORDER BY t.updated_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
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
        item["sources"] = json.loads(item["sources"]) if item["sources"] else []
        item["tool_calls"] = json.loads(item["tool_calls"]) if item["tool_calls"] else []
        result.append(item)
    return result

def add_message(thread_id: str, role: str, content: str, sources: Optional[List[str]] = None, tool_calls: Optional[List[Dict[str, Any]]] = None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    create_or_update_thread(thread_id)
    cursor.execute("""
    INSERT INTO chat_messages (thread_id, role, content, sources, tool_calls, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        thread_id,
        role,
        content,
        json.dumps(sources or []),
        json.dumps(tool_calls or []),
        now
    ))
    conn.commit()
    conn.close()

def delete_thread(thread_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE thread_id = ?", (thread_id,))
    cursor.execute("DELETE FROM chat_threads WHERE thread_id = ?", (thread_id,))
    conn.commit()
    conn.close()
