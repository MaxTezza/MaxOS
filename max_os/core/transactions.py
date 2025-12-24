"""Transaction logging system for filesystem operations."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class TransactionLogger:
    """SQLite-based transaction logger for filesystem operations."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize transaction logger.

        Args:
            db_path: Path to SQLite database file (default: ~/.maxos/transactions.db)
        """
        if db_path is None:
            db_path = Path.home() / ".maxos" / "transactions.db"
        else:
            db_path = Path(db_path).expanduser()

        # Create .maxos directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    user_approved BOOLEAN,
                    metadata TEXT,
                    rollback_info TEXT
                )
            """)
            conn.commit()

    def log_transaction(
        self,
        operation: str,
        status: str,
        user_approved: bool = True,
        metadata: dict[str, Any] | None = None,
        rollback_info: dict[str, Any] | None = None,
    ) -> int:
        """Log a transaction.

        Args:
            operation: Operation type ('copy', 'move', 'delete', 'mkdir')
            status: Transaction status ('pending', 'completed', 'failed', 'rolled_back')
            user_approved: Whether user approved the operation
            metadata: Operation metadata (paths, sizes, checksums, etc.)
            rollback_info: Information needed to rollback the operation

        Returns:
            Transaction ID
        """
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        rollback_json = json.dumps(rollback_info) if rollback_info else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (timestamp, operation, status, user_approved, metadata, rollback_info)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (timestamp, operation, status, user_approved, metadata_json, rollback_json),
            )
            conn.commit()
            return cursor.lastrowid

    def update_transaction(
        self,
        transaction_id: int,
        status: str | None = None,
        metadata: dict[str, Any] | None = None,
        rollback_info: dict[str, Any] | None = None,
    ) -> None:
        """Update an existing transaction.

        Args:
            transaction_id: Transaction ID to update
            status: New status (if provided)
            metadata: Updated metadata (if provided)
            rollback_info: Updated rollback info (if provided)
        """
        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if rollback_info is not None:
            updates.append("rollback_info = ?")
            params.append(json.dumps(rollback_info))

        if not updates:
            return

        params.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
            conn.commit()

    def get_transaction(self, transaction_id: int) -> dict[str, Any] | None:
        """Get a transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction dict or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "operation": row["operation"],
                "status": row["status"],
                "user_approved": bool(row["user_approved"]),
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "rollback_info": json.loads(row["rollback_info"]) if row["rollback_info"] else None,
            }

    def list_transactions(
        self,
        operation: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List transactions with optional filtering.

        Args:
            operation: Filter by operation type
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of transaction dicts
        """
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if operation:
            query += " AND operation = ?"
            params.append(operation)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "operation": row["operation"],
                    "status": row["status"],
                    "user_approved": bool(row["user_approved"]),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "rollback_info": (
                        json.loads(row["rollback_info"]) if row["rollback_info"] else None
                    ),
                }
                for row in rows
            ]

    def get_recent_transactions(self, days: int = 7, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent transactions.

        Args:
            days: Number of days to look back
            limit: Maximum number of results

        Returns:
            List of transaction dicts
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM transactions
                WHERE timestamp >= ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (cutoff_str, limit),
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "operation": row["operation"],
                    "status": row["status"],
                    "user_approved": bool(row["user_approved"]),
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "rollback_info": (
                        json.loads(row["rollback_info"]) if row["rollback_info"] else None
                    ),
                }
                for row in rows
            ]
