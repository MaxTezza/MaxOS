#!/usr/bin/env python3
"""Integration test for confirmation and rollback framework."""
import asyncio
import tempfile
from pathlib import Path

import pytest

from max_os.agents.base import AgentRequest
from max_os.agents.filesystem import FileSystemAgent
from max_os.core.rollback import RollbackManager
from max_os.core.transactions import TransactionLogger


@pytest.mark.asyncio
async def test_copy_rollback():
    """Test copy operation with rollback."""
    print("\n=== Testing Copy Operation with Rollback ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test.db"
        trash_dir = tmp_path / "trash"
        
        # Create test file
        source = tmp_path / "source.txt"
        source.write_text("Test content")
        dest = tmp_path / "dest.txt"
        
        # Initialize agent with test config
        config = {
            "root_whitelist": [str(tmp_path)],
            "confirmation": {
                "enabled": False,  # Disable for automated testing
            },
            "rollback": {
                "trash_retention_days": 30,
            },
            "transactions": {
                "db_path": str(db_path),
            },
        }
        
        agent = FileSystemAgent(config=config)
        agent.rollback_manager = RollbackManager(
            trash_dir=trash_dir,
            db_path=db_path,
        )
        agent.transaction_logger = TransactionLogger(db_path=db_path)
        
        # Perform copy
        request = AgentRequest(
            intent="file.copy",
            text="copy source to dest",
            context={
                "source_path": str(source),
                "dest_path": str(dest),
                "confirmation_mode": "api",
            },
        )
        
        response = agent._handle_copy(request)
        
        print(f"✓ Copy status: {response.status}")
        print(f"✓ Transaction ID: {response.payload.get('transaction_id')}")
        
        assert response.status == "success"
        assert dest.exists()
        assert dest.read_text() == "Test content"
        
        # Rollback
        tx_id = response.payload["transaction_id"]
        success, message = agent.rollback_manager.rollback_transaction(tx_id)
        
        print(f"✓ Rollback success: {success}")
        print(f"✓ Rollback message: {message}")
        
        assert success is True
        assert not dest.exists()
        
        print("✅ Copy rollback test PASSED\n")


@pytest.mark.asyncio
async def test_move_rollback():
    """Test move operation with rollback."""
    print("=== Testing Move Operation with Rollback ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test.db"
        trash_dir = tmp_path / "trash"
        
        # Create test file
        source = tmp_path / "source.txt"
        source.write_text("Test content")
        dest = tmp_path / "dest.txt"
        
        # Initialize agent
        config = {
            "root_whitelist": [str(tmp_path)],
            "confirmation": {"enabled": False},
            "transactions": {"db_path": str(db_path)},
        }
        
        agent = FileSystemAgent(config=config)
        agent.rollback_manager = RollbackManager(
            trash_dir=trash_dir,
            db_path=db_path,
        )
        agent.transaction_logger = TransactionLogger(db_path=db_path)
        
        # Perform move
        request = AgentRequest(
            intent="file.move",
            text="move source to dest",
            context={
                "source_path": str(source),
                "dest_path": str(dest),
                "confirmation_mode": "api",
            },
        )
        
        response = agent._handle_move(request)
        
        print(f"✓ Move status: {response.status}")
        print(f"✓ Transaction ID: {response.payload.get('transaction_id')}")
        
        assert response.status == "success"
        assert not source.exists()
        assert dest.exists()
        
        # Rollback
        tx_id = response.payload["transaction_id"]
        success, message = agent.rollback_manager.rollback_transaction(tx_id)
        
        print(f"✓ Rollback success: {success}")
        print(f"✓ Rollback message: {message}")
        
        assert success is True
        assert source.exists()
        assert not dest.exists()
        
        print("✅ Move rollback test PASSED\n")


@pytest.mark.asyncio
async def test_delete_restore():
    """Test delete operation with restore from trash."""
    print("=== Testing Delete Operation with Restore ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test.db"
        trash_dir = tmp_path / "trash"
        
        # Create test file
        target = tmp_path / "to_delete.txt"
        target.write_text("Important content")
        
        # Initialize agent
        config = {
            "root_whitelist": [str(tmp_path)],
            "confirmation": {"enabled": False},
            "transactions": {"db_path": str(db_path)},
        }
        
        agent = FileSystemAgent(config=config)
        agent.rollback_manager = RollbackManager(
            trash_dir=trash_dir,
            db_path=db_path,
        )
        agent.transaction_logger = TransactionLogger(db_path=db_path)
        
        # Perform delete
        request = AgentRequest(
            intent="file.delete",
            text="delete file",
            context={
                "path": str(target),
                "confirmation_mode": "api",
            },
        )
        
        response = agent._handle_delete(request)
        
        print(f"✓ Delete status: {response.status}")
        print(f"✓ Transaction ID: {response.payload.get('transaction_id')}")
        print(f"✓ Recoverable: {response.payload.get('recoverable')}")
        
        assert response.status == "success"
        assert not target.exists()
        
        # Check trash
        trash_files = agent.rollback_manager.list_trash()
        print(f"✓ Files in trash: {len(trash_files)}")
        assert len(trash_files) == 1
        
        # Restore
        tx_id = response.payload["transaction_id"]
        success, message = agent.rollback_manager.rollback_transaction(tx_id)
        
        print(f"✓ Restore success: {success}")
        print(f"✓ Restore message: {message}")
        
        assert success is True
        assert target.exists()
        assert target.read_text() == "Important content"
        
        print("✅ Delete restore test PASSED\n")


@pytest.mark.asyncio
async def test_mkdir_rollback():
    """Test mkdir operation with rollback."""
    print("=== Testing Mkdir Operation with Rollback ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test.db"
        trash_dir = tmp_path / "trash"
        
        new_dir = tmp_path / "newdir"
        
        # Initialize agent
        config = {
            "root_whitelist": [str(tmp_path)],
            "confirmation": {"enabled": False},
            "transactions": {"db_path": str(db_path)},
        }
        
        agent = FileSystemAgent(config=config)
        agent.rollback_manager = RollbackManager(
            trash_dir=trash_dir,
            db_path=db_path,
        )
        agent.transaction_logger = TransactionLogger(db_path=db_path)
        
        # Perform mkdir
        request = AgentRequest(
            intent="file.mkdir",
            text="create directory",
            context={
                "path": str(new_dir),
                "confirmation_mode": "api",
            },
        )
        
        response = agent._handle_create_dir(request)
        
        print(f"✓ Mkdir status: {response.status}")
        print(f"✓ Transaction ID: {response.payload.get('transaction_id')}")
        
        assert response.status == "success"
        assert new_dir.exists()
        
        # Rollback
        tx_id = response.payload["transaction_id"]
        success, message = agent.rollback_manager.rollback_transaction(tx_id)
        
        print(f"✓ Rollback success: {success}")
        print(f"✓ Rollback message: {message}")
        
        assert success is True
        assert not new_dir.exists()
        
        print("✅ Mkdir rollback test PASSED\n")


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("Running Confirmation & Rollback Integration Tests")
    print("=" * 60)
    
    await test_copy_rollback()
    await test_move_rollback()
    await test_delete_restore()
    await test_mkdir_rollback()
    
    print("=" * 60)
    print("✅ All integration tests PASSED!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
