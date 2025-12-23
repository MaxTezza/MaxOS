"""Tests for rollback manager."""
import json
from pathlib import Path

import pytest


@pytest.fixture
def temp_env(tmp_path):
    """Create temporary environment for testing."""
    trash_dir = tmp_path / "trash"
    db_path = tmp_path / "transactions.db"
    
    return {
        "trash_dir": trash_dir,
        "db_path": db_path,
        "tmp_path": tmp_path,
    }


def test_rollback_manager_init(temp_env):
    """Test rollback manager initialization."""
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        retention_days=30,
        max_trash_size_gb=50,
    )
    
    assert manager.trash_dir == temp_env["trash_dir"]
    assert manager.retention_days == 30
    assert manager.max_trash_size_gb == 50
    
    # Trash directory should be created
    assert temp_env["trash_dir"].exists()


def test_calculate_checksum(temp_env):
    """Test checksum calculation."""
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager(trash_dir=temp_env["trash_dir"])
    
    # Create a test file
    test_file = temp_env["tmp_path"] / "test.txt"
    test_file.write_text("Hello, World!")
    
    checksum1 = manager.calculate_checksum(test_file)
    
    # Checksum should be consistent
    checksum2 = manager.calculate_checksum(test_file)
    assert checksum1 == checksum2
    
    # Checksum should be SHA256 (64 hex characters)
    assert len(checksum1) == 64
    
    # Different content should have different checksum
    test_file.write_text("Different content")
    checksum3 = manager.calculate_checksum(test_file)
    assert checksum3 != checksum1


def test_move_to_trash(temp_env):
    """Test moving file to trash."""
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager(trash_dir=temp_env["trash_dir"])
    
    # Create a test file
    test_file = temp_env["tmp_path"] / "test.txt"
    test_file.write_text("Test content")
    
    # Move to trash
    trash_path = manager.move_to_trash(test_file, transaction_id=1)
    
    # Original file should be gone
    assert not test_file.exists()
    
    # File should be in trash
    assert trash_path.exists()
    assert trash_path.read_text() == "Test content"
    
    # Metadata file should exist
    metadata_path = trash_path.parent / f".{trash_path.name}.metadata.json"
    assert metadata_path.exists()
    
    # Check metadata
    metadata = json.loads(metadata_path.read_text())
    assert metadata["original_path"] == str(test_file)
    assert metadata["transaction_id"] == 1


def test_rollback_copy(temp_env):
    """Test rolling back a copy operation."""
    from max_os.core.rollback import RollbackManager
    from max_os.core.transactions import TransactionLogger
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    logger = TransactionLogger(db_path=temp_env["db_path"])
    
    # Create test files
    source = temp_env["tmp_path"] / "source.txt"
    dest = temp_env["tmp_path"] / "dest.txt"
    source.write_text("Content")
    dest.write_text("Content")
    
    # Create transaction
    tx_id = logger.log_transaction(
        operation="copy",
        status="completed",
        user_approved=True,
        metadata={
            "copied_files": [
                {"destination": str(dest)},
            ],
        },
    )
    
    # Rollback
    transaction = logger.get_transaction(tx_id)
    success = manager.rollback_copy(transaction)
    
    assert success is True
    assert not dest.exists()
    assert source.exists()


def test_rollback_move(temp_env):
    """Test rolling back a move operation."""
    from max_os.core.rollback import RollbackManager
    from max_os.core.transactions import TransactionLogger
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    logger = TransactionLogger(db_path=temp_env["db_path"])
    
    # Create test files
    original = temp_env["tmp_path"] / "original.txt"
    moved = temp_env["tmp_path"] / "moved.txt"
    moved.write_text("Content")
    
    # Create transaction
    tx_id = logger.log_transaction(
        operation="move",
        status="completed",
        user_approved=True,
        rollback_info={
            "moved_files": [
                {
                    "original_path": str(original),
                    "destination": str(moved),
                },
            ],
        },
    )
    
    # Rollback
    transaction = logger.get_transaction(tx_id)
    success = manager.rollback_move(transaction)
    
    assert success is True
    assert original.exists()
    assert not moved.exists()


def test_rollback_delete(temp_env):
    """Test rolling back a delete operation."""
    from max_os.core.rollback import RollbackManager
    from max_os.core.transactions import TransactionLogger
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    logger = TransactionLogger(db_path=temp_env["db_path"])
    
    # Create and trash a file
    original = temp_env["tmp_path"] / "deleted.txt"
    original.write_text("Original content")
    
    # Move to trash
    trash_path = manager.move_to_trash(original, transaction_id=1)
    
    # Create transaction
    tx_id = logger.log_transaction(
        operation="delete",
        status="completed",
        user_approved=True,
    )
    
    # Rollback (restore from trash)
    transaction = logger.get_transaction(tx_id)
    success = manager.rollback_delete(transaction)
    
    assert success is True
    assert original.exists()
    assert original.read_text() == "Original content"


def test_rollback_mkdir(temp_env):
    """Test rolling back a mkdir operation."""
    from max_os.core.rollback import RollbackManager
    from max_os.core.transactions import TransactionLogger
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    logger = TransactionLogger(db_path=temp_env["db_path"])
    
    # Create a directory
    new_dir = temp_env["tmp_path"] / "newdir"
    new_dir.mkdir()
    
    # Create transaction
    tx_id = logger.log_transaction(
        operation="mkdir",
        status="completed",
        user_approved=True,
        metadata={"path": str(new_dir)},
    )
    
    # Rollback
    transaction = logger.get_transaction(tx_id)
    success = manager.rollback_mkdir(transaction)
    
    assert success is True
    assert not new_dir.exists()


def test_rollback_mkdir_not_empty(temp_env):
    """Test that rollback fails for non-empty directory."""
    from max_os.core.rollback import RollbackManager
    from max_os.core.transactions import TransactionLogger
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    logger = TransactionLogger(db_path=temp_env["db_path"])
    
    # Create a directory with a file
    new_dir = temp_env["tmp_path"] / "newdir"
    new_dir.mkdir()
    (new_dir / "file.txt").write_text("content")
    
    # Create transaction
    tx_id = logger.log_transaction(
        operation="mkdir",
        status="completed",
        user_approved=True,
        metadata={"path": str(new_dir)},
    )
    
    # Rollback should fail
    transaction = logger.get_transaction(tx_id)
    success = manager.rollback_mkdir(transaction)
    
    assert success is False
    assert new_dir.exists()


def test_rollback_transaction(temp_env):
    """Test rollback_transaction method."""
    from max_os.core.rollback import RollbackManager
    from max_os.core.transactions import TransactionLogger
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    logger = TransactionLogger(db_path=temp_env["db_path"])
    
    # Create a directory
    new_dir = temp_env["tmp_path"] / "newdir"
    new_dir.mkdir()
    
    # Create transaction
    tx_id = logger.log_transaction(
        operation="mkdir",
        status="completed",
        user_approved=True,
        metadata={"path": str(new_dir)},
    )
    
    # Rollback using transaction ID
    success, message = manager.rollback_transaction(tx_id)
    
    assert success is True
    assert "successfully rolled back" in message.lower()
    assert not new_dir.exists()
    
    # Transaction status should be updated
    transaction = logger.get_transaction(tx_id)
    assert transaction["status"] == "rolled_back"


def test_rollback_transaction_not_found(temp_env):
    """Test rollback of nonexistent transaction."""
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        db_path=temp_env["db_path"],
    )
    
    success, message = manager.rollback_transaction(99999)
    
    assert success is False
    assert "not found" in message.lower()


def test_list_trash(temp_env):
    """Test listing trash contents."""
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager(trash_dir=temp_env["trash_dir"])
    
    # Create and trash some files
    file1 = temp_env["tmp_path"] / "file1.txt"
    file2 = temp_env["tmp_path"] / "file2.txt"
    file1.write_text("Content 1")
    file2.write_text("Content 2")
    
    manager.move_to_trash(file1, transaction_id=1)
    manager.move_to_trash(file2, transaction_id=2)
    
    # List trash
    trash_list = manager.list_trash()
    
    assert len(trash_list) == 2
    assert any(item["transaction_id"] == 1 for item in trash_list)
    assert any(item["transaction_id"] == 2 for item in trash_list)


def test_cleanup_old_trash(temp_env):
    """Test cleanup of old trash files."""
    from datetime import datetime, timedelta
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager(
        trash_dir=temp_env["trash_dir"],
        retention_days=1,  # 1 day retention
    )
    
    # Create and trash a file
    file1 = temp_env["tmp_path"] / "old_file.txt"
    file1.write_text("Old content")
    trash_path = manager.move_to_trash(file1, transaction_id=1)
    
    # Manually update the metadata to make it old
    metadata_path = trash_path.parent / f".{trash_path.name}.metadata.json"
    metadata = json.loads(metadata_path.read_text())
    old_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
    metadata["timestamp"] = old_timestamp
    metadata_path.write_text(json.dumps(metadata))
    
    # Run cleanup
    files_deleted, bytes_freed = manager.cleanup_old_trash()
    
    assert files_deleted == 1
    assert bytes_freed > 0
    assert not trash_path.exists()


def test_default_trash_location():
    """Test that default trash location is ~/.maxos/trash/."""
    from max_os.core.rollback import RollbackManager
    
    manager = RollbackManager()
    
    expected_path = Path.home() / ".maxos" / "trash"
    assert manager.trash_dir == expected_path
    
    # Cleanup
    if expected_path.exists():
        import shutil
        shutil.rmtree(expected_path)
