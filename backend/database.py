import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'atlas_memory.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # Create conversations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Create messages table (multimodal expanded)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            message_type TEXT DEFAULT 'text',
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    ''')
    
    # Try adding new columns if the table existed from before
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN message_type TEXT DEFAULT 'text'")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN file_path TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def create_conversation(conversation_id: str, title: str = "New Chat"):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conversation_id, title)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    finally:
        conn.close()

def add_message(conversation_id: str, role: str, content: str, message_type: str = 'text', file_path: str = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, message_type, file_path) VALUES (?, ?, ?, ?, ?)",
        (conversation_id, role, content, message_type, file_path)
    )
    conn.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    conn.commit()
    conn.close()

def get_conversation_history(conversation_id: str):
    conn = get_db()
    cursor = conn.execute(
        "SELECT role, content, message_type, file_path FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "message_type": row["message_type"], "file_path": row["file_path"]} for row in rows]

def get_all_conversations():
    conn = get_db()
    cursor = conn.execute("SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_conversation(conversation_id: str):
    conn = get_db()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()

def clear_all_conversations():
    conn = get_db()
    conn.execute("DELETE FROM messages")
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()
