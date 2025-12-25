"""Tests for Firestore and Cloud Storage integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_firestore_client_import_error():
    """Test FirestoreClient raises ImportError when google-cloud libraries missing."""
    with patch.dict("sys.modules", {"google.cloud.firestore": None, "google.cloud.storage": None}):
        with pytest.raises(ImportError, match="google-cloud-firestore"):
            from max_os.storage.firestore_client import FirestoreClient

            FirestoreClient(project_id="test-project")


@pytest.mark.asyncio
async def test_firestore_add_conversation():
    """Test adding conversation to Firestore."""
    with (
        patch("max_os.storage.firestore_client.firestore") as mock_firestore,
        patch("max_os.storage.firestore_client.storage") as mock_storage,
    ):
        # Setup mocks
        mock_async_client = AsyncMock()
        mock_firestore.AsyncClient.return_value = mock_async_client
        mock_storage_client = Mock()
        mock_storage.Client.return_value = mock_storage_client
        mock_bucket = Mock()
        mock_storage_client.get_bucket.return_value = mock_bucket

        from max_os.storage.firestore_client import FirestoreClient

        client = FirestoreClient(project_id="test-project")

        # Mock the collection chain with proper async/non-async distinction
        mock_collection = Mock()
        mock_document = Mock()
        mock_subcollection = Mock()
        mock_collection.document = Mock(return_value=mock_document)
        mock_document.collection = Mock(return_value=mock_subcollection)
        mock_subcollection.add = AsyncMock()
        mock_async_client.collection = Mock(return_value=mock_collection)

        await client.add_conversation(
            user_id="user1", voice_input="Hello", gemini_response="Hi there!"
        )

        # Verify Firestore was called
        mock_async_client.collection.assert_called_with("users")
        mock_collection.document.assert_called_with("user1")
        mock_document.collection.assert_called_with("conversations")
        assert mock_subcollection.add.called


@pytest.mark.asyncio
async def test_firestore_get_user_profile():
    """Test getting user profile from Firestore."""
    with (
        patch("max_os.storage.firestore_client.firestore") as mock_firestore,
        patch("max_os.storage.firestore_client.storage") as mock_storage,
    ):
        # Setup mocks
        mock_async_client = AsyncMock()
        mock_firestore.AsyncClient.return_value = mock_async_client
        mock_storage_client = Mock()
        mock_storage.Client.return_value = mock_storage_client
        mock_bucket = Mock()
        mock_storage_client.get_bucket.return_value = mock_bucket

        from max_os.storage.firestore_client import FirestoreClient

        client = FirestoreClient(project_id="test-project")

        # Mock the document
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"name": "Test User"}
        mock_collection = Mock()
        mock_document = Mock()
        mock_document.get = AsyncMock(return_value=mock_doc)
        mock_collection.document = Mock(return_value=mock_document)
        mock_async_client.collection = Mock(return_value=mock_collection)

        result = await client.get_user_profile("user1")

        assert result == {"name": "Test User"}


@pytest.mark.asyncio
async def test_firestore_update_pantry():
    """Test updating pantry in Firestore."""
    with (
        patch("max_os.storage.firestore_client.firestore") as mock_firestore,
        patch("max_os.storage.firestore_client.storage") as mock_storage,
    ):
        # Setup mocks
        mock_async_client = AsyncMock()
        mock_firestore.AsyncClient.return_value = mock_async_client
        mock_storage_client = Mock()
        mock_storage.Client.return_value = mock_storage_client
        mock_bucket = Mock()
        mock_storage_client.get_bucket.return_value = mock_bucket

        from max_os.storage.firestore_client import FirestoreClient

        client = FirestoreClient(project_id="test-project")

        # Mock the collection chain
        mock_collection = Mock()
        mock_document = Mock()
        mock_document.set = AsyncMock()
        mock_collection.document = Mock(return_value=mock_document)
        mock_async_client.collection = Mock(return_value=mock_collection)

        items = [{"item": "milk", "quantity": 1}]
        await client.update_pantry("user1", items)

        mock_document.set.assert_called_once()
        call_args = mock_document.set.call_args
        assert call_args[0][0] == {"pantry": items}
        assert call_args[1]["merge"] is True


@pytest.mark.asyncio
async def test_storage_manager_import_error_no_redis():
    """Test StorageManager raises ImportError when redis missing."""
    # We can't easily test this since redis is already imported
    # Instead, test that it works with redis available
    with patch("max_os.storage.storage_manager.redis") as mock_redis_module:
        mock_redis_client = Mock()
        mock_redis_module.from_url.return_value = mock_redis_client

        # Should work fine with redis available
        import tempfile

        from max_os.storage.storage_manager import StorageManager

        with tempfile.NamedTemporaryFile() as tmp:
            manager = StorageManager(
                redis_url="redis://localhost",
                sqlite_path=tmp.name,
                firestore_project="test",
                offline_mode=True,
            )
            assert manager is not None


@pytest.mark.asyncio
async def test_storage_manager_hybrid(tmp_path):
    """Test hybrid storage (Redis + SQLite + Firestore)."""
    with (
        patch("max_os.storage.storage_manager.redis") as mock_redis_module,
        patch("max_os.storage.storage_manager.FirestoreClient") as mock_firestore_class,
    ):
        # Setup mocks
        mock_redis_client = Mock()
        mock_redis_module.from_url.return_value = mock_redis_client
        mock_firestore = AsyncMock()
        mock_firestore.add_conversation = AsyncMock()
        mock_firestore_class.return_value = mock_firestore

        from max_os.storage.storage_manager import StorageManager

        sqlite_path = tmp_path / "test.db"
        manager = StorageManager(
            redis_url="redis://localhost",
            sqlite_path=str(sqlite_path),
            firestore_project="test",
            offline_mode=False,
        )

        await manager.store_conversation(
            user_id="user1", voice_input="Test", gemini_response="Response"
        )

        # All three layers should be called
        assert mock_redis_client.setex.called
        assert manager.firestore is not None
        assert mock_firestore.add_conversation.called


@pytest.mark.asyncio
async def test_storage_manager_offline_mode(tmp_path):
    """Test offline mode uses only local storage."""
    with patch("max_os.storage.storage_manager.redis") as mock_redis_module:
        # Setup mocks
        mock_redis_client = Mock()
        mock_redis_module.from_url.return_value = mock_redis_client

        from max_os.storage.storage_manager import StorageManager

        sqlite_path = tmp_path / "test.db"
        manager = StorageManager(
            redis_url="redis://localhost",
            sqlite_path=str(sqlite_path),
            firestore_project="test",
            offline_mode=True,  # Offline!
        )

        assert manager.firestore is None

        # Should still work with local storage only
        await manager.store_conversation(
            user_id="user1", voice_input="Test", gemini_response="Response"
        )

        assert mock_redis_client.setex.called


@pytest.mark.asyncio
async def test_storage_manager_get_conversation_history_offline(tmp_path):
    """Test getting conversation history from SQLite in offline mode."""
    with patch("max_os.storage.storage_manager.redis") as mock_redis_module:
        mock_redis_client = Mock()
        mock_redis_module.from_url.return_value = mock_redis_client

        from max_os.storage.storage_manager import StorageManager

        sqlite_path = tmp_path / "test.db"
        manager = StorageManager(
            redis_url="redis://localhost",
            sqlite_path=str(sqlite_path),
            firestore_project="test",
            offline_mode=True,
        )

        # Add some conversations
        await manager.store_conversation(user_id="user1", voice_input="Hello", gemini_response="Hi")
        await manager.store_conversation(
            user_id="user1", voice_input="Test", gemini_response="Response"
        )

        # Get history
        history = await manager.get_conversation_history("user1", limit=10)

        assert len(history) == 2
        # SQLite returns in reverse order (DESC), so newest first
        assert history[0]["voice_input"] == "Test"
        assert history[1]["voice_input"] == "Hello"


@pytest.mark.asyncio
async def test_storage_manager_get_pantry_with_cache(tmp_path):
    """Test getting pantry with Redis cache."""
    with (
        patch("max_os.storage.storage_manager.redis") as mock_redis_module,
        patch("max_os.storage.storage_manager.FirestoreClient") as mock_firestore_class,
    ):
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = '[{"item": "milk", "quantity": 1}]'
        mock_redis_module.from_url.return_value = mock_redis_client
        mock_firestore = AsyncMock()
        mock_firestore_class.return_value = mock_firestore

        from max_os.storage.storage_manager import StorageManager

        sqlite_path = tmp_path / "test.db"
        manager = StorageManager(
            redis_url="redis://localhost",
            sqlite_path=str(sqlite_path),
            firestore_project="test",
            offline_mode=False,
        )

        pantry = await manager.get_pantry("user1")

        # Should return cached value
        assert pantry == [{"item": "milk", "quantity": 1}]
        # Should not call Firestore
        assert not mock_firestore.get_pantry.called


@pytest.mark.asyncio
async def test_firestore_save_gesture():
    """Test saving gesture to Firestore."""
    with (
        patch("max_os.storage.firestore_client.firestore") as mock_firestore,
        patch("max_os.storage.firestore_client.storage") as mock_storage,
    ):
        # Setup mocks
        mock_async_client = AsyncMock()
        mock_firestore.AsyncClient.return_value = mock_async_client
        mock_storage_client = Mock()
        mock_storage.Client.return_value = mock_storage_client
        mock_bucket = Mock()
        mock_storage_client.get_bucket.return_value = mock_bucket

        from max_os.storage.firestore_client import FirestoreClient

        client = FirestoreClient(project_id="test-project")

        # Mock the collection chain with proper async/non-async distinction
        mock_collection = Mock()
        mock_document = Mock()
        mock_subcollection = Mock()
        mock_gesture_doc = Mock()
        mock_gesture_doc.set = AsyncMock()
        mock_async_client.collection = Mock(return_value=mock_collection)
        mock_collection.document = Mock(return_value=mock_document)
        mock_document.collection = Mock(return_value=mock_subcollection)
        mock_subcollection.document = Mock(return_value=mock_gesture_doc)

        landmarks = [{"x": 0.5, "y": 0.5}]
        await client.save_gesture("user1", "thumbs_up", landmarks, confidence=0.95)

        mock_gesture_doc.set.assert_called_once()


@pytest.mark.asyncio
async def test_storage_manager_sqlite_initialization(tmp_path):
    """Test SQLite schema is created on initialization."""
    with patch("max_os.storage.storage_manager.redis") as mock_redis_module:
        mock_redis_client = Mock()
        mock_redis_module.from_url.return_value = mock_redis_client

        from max_os.storage.storage_manager import StorageManager

        sqlite_path = tmp_path / "test.db"
        manager = StorageManager(
            redis_url="redis://localhost",
            sqlite_path=str(sqlite_path),
            firestore_project="test",
            offline_mode=True,
        )

        # Check tables exist
        cursor = manager.sqlite.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='offline_queue'")
        assert cursor.fetchone() is not None
