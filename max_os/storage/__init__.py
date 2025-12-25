"""Storage layer for MaxOS - Firestore, Cloud Storage, Redis, and SQLite."""

from max_os.storage.firestore_client import FirestoreClient
from max_os.storage.storage_manager import StorageManager

__all__ = ["FirestoreClient", "StorageManager"]
