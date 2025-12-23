"""Tests for transaction logger."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_transactions.db"
    return db_path


def test_transaction_logger_init(temp_db):
    """Test transaction logger initialization."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    # Database file should exist
    assert temp_db.exists()
    
    # Table should be created
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'"
        )
        assert cursor.fetchone() is not None


def test_log_transaction(temp_db):
    """Test logging a transaction."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    metadata = {
        "source": "/home/user/file.txt",
        "destination": "/home/user/backup/file.txt",
        "size": 1024,
    }
    
    rollback_info = {
        "copied_files": ["/home/user/backup/file.txt"],
    }
    
    tx_id = logger.log_transaction(
        operation="copy",
        status="completed",
        user_approved=True,
        metadata=metadata,
        rollback_info=rollback_info,
    )
    
    assert tx_id > 0
    
    # Verify transaction was logged
    transaction = logger.get_transaction(tx_id)
    assert transaction is not None
    assert transaction["operation"] == "copy"
    assert transaction["status"] == "completed"
    assert transaction["user_approved"] is True
    assert transaction["metadata"] == metadata
    assert transaction["rollback_info"] == rollback_info


def test_update_transaction(temp_db):
    """Test updating a transaction."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    # Create initial transaction
    tx_id = logger.log_transaction(
        operation="copy",
        status="pending",
        user_approved=True,
    )
    
    # Update status
    logger.update_transaction(tx_id, status="completed")
    
    transaction = logger.get_transaction(tx_id)
    assert transaction["status"] == "completed"
    
    # Update metadata
    new_metadata = {"result": "success"}
    logger.update_transaction(tx_id, metadata=new_metadata)
    
    transaction = logger.get_transaction(tx_id)
    assert transaction["metadata"] == new_metadata


def test_list_transactions(temp_db):
    """Test listing transactions."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    # Create multiple transactions
    tx1 = logger.log_transaction(operation="copy", status="completed", user_approved=True)
    tx2 = logger.log_transaction(operation="move", status="completed", user_approved=True)
    tx3 = logger.log_transaction(operation="delete", status="completed", user_approved=False)
    
    # List all transactions
    all_txs = logger.list_transactions()
    assert len(all_txs) == 3
    
    # Filter by operation
    copy_txs = logger.list_transactions(operation="copy")
    assert len(copy_txs) == 1
    assert copy_txs[0]["operation"] == "copy"
    
    # Filter by status
    completed_txs = logger.list_transactions(status="completed")
    assert len(completed_txs) == 3


def test_list_transactions_pagination(temp_db):
    """Test transaction listing with pagination."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    # Create 10 transactions
    for i in range(10):
        logger.log_transaction(
            operation="copy",
            status="completed",
            user_approved=True,
        )
    
    # Test limit
    page1 = logger.list_transactions(limit=5)
    assert len(page1) == 5
    
    # Test offset
    page2 = logger.list_transactions(limit=5, offset=5)
    assert len(page2) == 5
    
    # IDs should be different (ordered DESC)
    assert page1[0]["id"] != page2[0]["id"]


def test_get_recent_transactions(temp_db):
    """Test getting recent transactions."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    # Create transactions
    logger.log_transaction(operation="copy", status="completed", user_approved=True)
    logger.log_transaction(operation="move", status="completed", user_approved=True)
    
    # Get recent transactions
    recent = logger.get_recent_transactions(days=7)
    assert len(recent) >= 2


def test_get_nonexistent_transaction(temp_db):
    """Test getting a nonexistent transaction."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    transaction = logger.get_transaction(99999)
    assert transaction is None


def test_transaction_timestamp_format(temp_db):
    """Test that transaction timestamps are ISO format."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger(db_path=temp_db)
    
    tx_id = logger.log_transaction(
        operation="copy",
        status="completed",
        user_approved=True,
    )
    
    transaction = logger.get_transaction(tx_id)
    
    # Should be able to parse timestamp
    timestamp = datetime.fromisoformat(transaction["timestamp"])
    assert timestamp is not None
    
    # Should be recent (within last minute)
    now = datetime.now()
    time_diff = (now - timestamp).total_seconds()
    assert time_diff < 60


def test_default_db_location():
    """Test that default database location is ~/.maxos/transactions.db."""
    from max_os.core.transactions import TransactionLogger
    
    logger = TransactionLogger()
    
    expected_path = Path.home() / ".maxos" / "transactions.db"
    assert logger.db_path == expected_path
    
    # Cleanup
    if expected_path.exists():
        expected_path.unlink()
