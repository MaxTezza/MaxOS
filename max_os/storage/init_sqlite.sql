-- SQLite schema for MaxOS local persistent storage
-- This provides offline fallback and audit trail

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    voice_input TEXT,
    gemini_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_to_firestore BOOLEAN DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_user_timestamp ON conversations(user_id, timestamp);

CREATE TABLE IF NOT EXISTS offline_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
