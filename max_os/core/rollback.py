"""Rollback system for filesystem operations."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from max_os.core.transactions import TransactionLogger


class RollbackManager:
    """Manager for rolling back filesystem operations."""

    def __init__(
        self,
        trash_dir: str | Path | None = None,
        retention_days: int = 30,
        max_trash_size_gb: int = 50,
        db_path: str | Path | None = None,
    ):
        """Initialize rollback manager.

        Args:
            trash_dir: Path to trash directory (default: ~/.maxos/trash/)
            retention_days: Number of days to retain deleted files
            max_trash_size_gb: Maximum trash size in GB
            db_path: Path to transaction database (default: ~/.maxos/transactions.db)
        """
        if trash_dir is None:
            trash_dir = Path.home() / ".maxos" / "trash"
        else:
            trash_dir = Path(trash_dir).expanduser()

        self.trash_dir = trash_dir
        self.retention_days = retention_days
        self.max_trash_size_gb = max_trash_size_gb

        # Create trash directory with restricted permissions
        self.trash_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        self.transaction_logger = TransactionLogger(db_path=db_path)

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of SHA256 checksum
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def move_to_trash(
        self, file_path: Path, transaction_id: int, original_path: Path | None = None
    ) -> Path:
        """Move a file to trash.

        Args:
            file_path: Path to file to trash
            transaction_id: Transaction ID
            original_path: Original path (if different from file_path)

        Returns:
            Path to trashed file
        """
        if original_path is None:
            original_path = file_path

        # Create transaction subdirectory
        trash_tx_dir = self.trash_dir / str(transaction_id)
        trash_tx_dir.mkdir(parents=True, exist_ok=True)

        # Preserve directory structure
        relative_path = original_path.name
        trash_path = trash_tx_dir / relative_path

        # If name collision, add suffix
        counter = 1
        while trash_path.exists():
            trash_path = trash_tx_dir / f"{original_path.stem}_{counter}{original_path.suffix}"
            counter += 1

        # Move file to trash
        shutil.move(str(file_path), str(trash_path))

        # Create metadata file
        metadata = {
            "original_path": str(original_path),
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction_id,
            "size_bytes": trash_path.stat().st_size,
        }

        metadata_path = trash_path.parent / f".{trash_path.name}.metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2))

        return trash_path

    def rollback_copy(self, transaction: dict[str, Any]) -> bool:
        """Rollback a copy operation by deleting copied files.

        Args:
            transaction: Transaction dict

        Returns:
            True if successful
        """
        metadata = transaction.get("metadata", {})
        copied_files = metadata.get("copied_files", [])

        success = True
        for file_info in copied_files:
            dest_path = Path(file_info["destination"])
            if dest_path.exists():
                try:
                    dest_path.unlink()
                except Exception as e:
                    print(f"Failed to delete {dest_path}: {e}")
                    success = False

        if success:
            self.transaction_logger.update_transaction(transaction["id"], status="rolled_back")

        return success

    def rollback_move(self, transaction: dict[str, Any]) -> bool:
        """Rollback a move operation by moving files back.

        Args:
            transaction: Transaction dict

        Returns:
            True if successful
        """
        rollback_info = transaction.get("rollback_info", {})
        moved_files = rollback_info.get("moved_files", [])

        success = True
        for file_info in moved_files:
            source = Path(file_info["original_path"])
            dest = Path(file_info["destination"])

            if dest.exists():
                try:
                    # Restore original directory if needed
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dest), str(source))
                except Exception as e:
                    print(f"Failed to restore {dest} to {source}: {e}")
                    success = False

        if success:
            self.transaction_logger.update_transaction(transaction["id"], status="rolled_back")

        return success

    def rollback_delete(self, transaction: dict[str, Any]) -> bool:
        """Rollback a delete operation by restoring from trash.

        Args:
            transaction: Transaction dict

        Returns:
            True if successful
        """
        transaction_id = transaction["id"]
        trash_tx_dir = self.trash_dir / str(transaction_id)

        if not trash_tx_dir.exists():
            print(f"Trash directory for transaction {transaction_id} not found")
            return False

        success = True
        for trash_file in trash_tx_dir.iterdir():
            if trash_file.name.startswith("."):
                continue  # Skip metadata files

            # Read metadata
            metadata_path = trash_file.parent / f".{trash_file.name}.metadata.json"
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())
                original_path = Path(metadata["original_path"])

                try:
                    # Restore original directory if needed
                    original_path.parent.mkdir(parents=True, exist_ok=True)

                    # If original path exists, add suffix
                    restore_path = original_path
                    counter = 1
                    while restore_path.exists():
                        restore_path = original_path.parent / f"{original_path.stem}_restored_{counter}{original_path.suffix}"
                        counter += 1

                    shutil.move(str(trash_file), str(restore_path))
                    metadata_path.unlink()  # Remove metadata file
                except Exception as e:
                    print(f"Failed to restore {trash_file}: {e}")
                    success = False

        if success:
            # Remove transaction directory if empty
            try:
                trash_tx_dir.rmdir()
            except OSError:
                pass  # Directory not empty, that's okay

            self.transaction_logger.update_transaction(transaction_id, status="rolled_back")

        return success

    def rollback_mkdir(self, transaction: dict[str, Any]) -> bool:
        """Rollback a mkdir operation by removing directory if empty.

        Args:
            transaction: Transaction dict

        Returns:
            True if successful
        """
        metadata = transaction.get("metadata", {})
        created_path = Path(metadata.get("path", ""))

        if not created_path.exists():
            return True  # Already gone

        try:
            # Only remove if empty
            created_path.rmdir()
            self.transaction_logger.update_transaction(transaction["id"], status="rolled_back")
            return True
        except OSError:
            print(f"Cannot remove {created_path}: directory not empty or error occurred")
            return False

    def rollback_transaction(self, transaction_id: int) -> tuple[bool, str]:
        """Rollback a transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            Tuple of (success: bool, message: str)
        """
        transaction = self.transaction_logger.get_transaction(transaction_id)

        if transaction is None:
            return False, f"Transaction {transaction_id} not found"

        if transaction["status"] == "rolled_back":
            return False, f"Transaction {transaction_id} already rolled back"

        if transaction["status"] not in ("completed", "failed"):
            return False, f"Cannot rollback transaction with status: {transaction['status']}"

        operation = transaction["operation"]

        if operation == "copy":
            success = self.rollback_copy(transaction)
        elif operation == "move":
            success = self.rollback_move(transaction)
        elif operation == "delete":
            success = self.rollback_delete(transaction)
        elif operation == "mkdir":
            success = self.rollback_mkdir(transaction)
        else:
            return False, f"Unknown operation: {operation}"

        if success:
            return True, f"Successfully rolled back {operation} operation"
        else:
            return False, f"Failed to rollback {operation} operation"

    def list_trash(self) -> list[dict[str, Any]]:
        """List files in trash.

        Returns:
            List of trash file info dicts
        """
        trash_files = []

        for tx_dir in self.trash_dir.iterdir():
            if not tx_dir.is_dir():
                continue

            for trash_file in tx_dir.iterdir():
                if trash_file.name.startswith("."):
                    continue

                metadata_path = trash_file.parent / f".{trash_file.name}.metadata.json"
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text())
                    trash_files.append({
                        "transaction_id": int(tx_dir.name),
                        "trash_path": str(trash_file),
                        "original_path": metadata["original_path"],
                        "timestamp": metadata["timestamp"],
                        "size_bytes": metadata["size_bytes"],
                    })

        return sorted(trash_files, key=lambda x: x["timestamp"], reverse=True)

    def cleanup_old_trash(self) -> tuple[int, int]:
        """Clean up trash files older than retention period.

        Returns:
            Tuple of (files_deleted: int, bytes_freed: int)
        """
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        files_deleted = 0
        bytes_freed = 0

        for tx_dir in self.trash_dir.iterdir():
            if not tx_dir.is_dir():
                continue

            for trash_file in tx_dir.iterdir():
                if trash_file.name.startswith("."):
                    continue

                metadata_path = trash_file.parent / f".{trash_file.name}.metadata.json"
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text())
                    timestamp = datetime.fromisoformat(metadata["timestamp"])

                    if timestamp < cutoff:
                        size = trash_file.stat().st_size
                        trash_file.unlink()
                        metadata_path.unlink()
                        files_deleted += 1
                        bytes_freed += size

            # Remove empty transaction directories
            try:
                tx_dir.rmdir()
            except OSError:
                pass  # Not empty

        return files_deleted, bytes_freed
