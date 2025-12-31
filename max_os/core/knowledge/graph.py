"""
The Mind Palace: A Local Knowledge Graph.
Stores facts as Triples (Subject, Predicate, Object).
Example: ("User", "likes", "Heavy Metal")
"""

import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import structlog
from pathlib import Path

logger = structlog.get_logger("max_os.knowledge.graph")

@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = "interaction"
    timestamp: str = ""

class GraphStore:
    def __init__(self, db_path: str = "~/.maxos/mind_palace.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(subject, predicate, object)
                )
            """)
            # Semantic search index (future) could go here

    def add_fact(self, subject: str, predicate: str, object_: str, confidence: float = 1.0, source: str = "user") -> bool:
        """Adds a fact to the graph. Updates confidence if exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO facts (subject, predicate, object, confidence, source)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(subject, predicate, object) 
                    DO UPDATE SET confidence = max(confidence, excluded.confidence), timestamp = CURRENT_TIMESTAMP
                """, (subject.lower(), predicate.lower(), object_.lower(), confidence, source))
            logger.info("Fact learned", fact=f"{subject} {predicate} {object_}")
            return True
        except Exception as e:
            logger.error("Failed to add fact", error=str(e))
            return False

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Simple keyword search for facts.
        Query: "metal" -> Returns facts about metal.
        """
        q = f"%{query.lower()}%"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT subject, predicate, object, confidence 
                FROM facts 
                WHERE subject LIKE ? OR predicate LIKE ? OR object LIKE ?
                ORDER BY confidence DESC
                LIMIT 10
            """, (q, q, q))
            
            results = []
            for row in cursor:
                results.append({
                    "subject": row[0],
                    "predicate": row[1],
                    "object": row[2],
                    "confidence": row[3]
                })
            return results

    def get_context_string(self, topic: str) -> str:
        """Returns a formatted string of relevant facts for the LLM context."""
        facts = self.search(topic)
        if not facts:
            return ""
        
        lines = ["Relevant Knowledge:"]
        for f in facts:
            lines.append(f"- {f['subject']} {f['predicate']} {f['object']}")
        return "\n".join(lines)

    def export_all(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT subject, predicate, object FROM facts")
            return [{"s": r[0], "p": r[1], "o": r[2]} for r in cursor]
