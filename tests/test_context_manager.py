"""Tests for context manager."""

import pytest

from max_os.core.context_manager import ContextManager, UserContext


@pytest.fixture
def temp_context_dir(tmp_path):
    """Create temporary context directory."""
    return tmp_path / "context"


def test_user_context_creation():
    """Test UserContext creation."""
    ctx = UserContext(user_id="test_user")

    assert ctx.user_id == "test_user"
    assert ctx.conversation_history == []
    assert ctx.user_profile == {}
    assert ctx.pantry_items == []
    assert ctx.music_history == []


def test_user_context_to_dict():
    """Test UserContext serialization."""
    ctx = UserContext(
        user_id="test_user",
        pantry_items=["milk", "eggs"],
        music_history=["song1", "song2"],
    )

    data = ctx.to_dict()

    assert data["user_id"] == "test_user"
    assert data["pantry_items"] == ["milk", "eggs"]
    assert data["music_history"] == ["song1", "song2"]


def test_user_context_from_dict():
    """Test UserContext deserialization."""
    data = {
        "user_id": "test_user",
        "conversation_history": [],
        "user_profile": {"name": "Test"},
        "pantry_items": ["milk"],
        "music_history": [],
        "routines": {},
        "preferences": {},
        "last_updated": "2024-01-01T00:00:00",
    }

    ctx = UserContext.from_dict(data)

    assert ctx.user_id == "test_user"
    assert ctx.user_profile == {"name": "Test"}
    assert ctx.pantry_items == ["milk"]


def test_context_manager_init(temp_context_dir):
    """Test ContextManager initialization."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    assert manager.user_id == "test_user"
    assert manager.storage_path == temp_context_dir
    assert manager.context.user_id == "test_user"
    assert temp_context_dir.exists()


def test_add_conversation(temp_context_dir):
    """Test adding conversation messages."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    manager.add_conversation("user", "Hello")
    assert len(manager.context.conversation_history) == 1
    assert manager.context.conversation_history[0]["role"] == "user"
    assert manager.context.conversation_history[0]["content"] == "Hello"

    manager.add_conversation("assistant", "Hi there!")
    assert len(manager.context.conversation_history) == 2


def test_conversation_history_limit(temp_context_dir):
    """Test conversation history trimming."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir, max_history=5)

    # Add more messages than the limit
    for i in range(10):
        manager.add_conversation("user", f"Message {i}")

    # Should only keep last 5
    assert len(manager.context.conversation_history) == 5
    assert manager.context.conversation_history[0]["content"] == "Message 5"


def test_get_conversation_history(temp_context_dir):
    """Test getting conversation history."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    manager.add_conversation("user", "Hello")
    manager.add_conversation("assistant", "Hi")
    manager.add_conversation("user", "How are you?")

    # Get all history
    history = manager.get_conversation_history()
    assert len(history) == 3

    # Get limited history
    history = manager.get_conversation_history(limit=2)
    assert len(history) == 2
    assert history[0]["content"] == "Hi"


def test_clear_conversation_history(temp_context_dir):
    """Test clearing conversation history."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    manager.add_conversation("user", "Hello")
    assert len(manager.context.conversation_history) == 1

    manager.clear_conversation_history()
    assert len(manager.context.conversation_history) == 0


def test_update_user_profile(temp_context_dir):
    """Test updating user profile."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    manager.update_user_profile({"name": "Test User", "age": 30})
    assert manager.context.user_profile["name"] == "Test User"
    assert manager.context.user_profile["age"] == 30

    # Update should merge
    manager.update_user_profile({"age": 31, "city": "New York"})
    assert manager.context.user_profile["age"] == 31
    assert manager.context.user_profile["city"] == "New York"
    assert manager.context.user_profile["name"] == "Test User"


def test_pantry_operations(temp_context_dir):
    """Test pantry item operations."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    # Add items
    manager.add_pantry_item("milk")
    manager.add_pantry_item("eggs")
    assert len(manager.get_pantry_items()) == 2

    # Don't add duplicates
    manager.add_pantry_item("milk")
    assert len(manager.get_pantry_items()) == 2

    # Remove item
    manager.remove_pantry_item("milk")
    assert len(manager.get_pantry_items()) == 1
    assert "eggs" in manager.get_pantry_items()

    # Update all items
    manager.update_pantry(["bread", "butter", "cheese"])
    assert len(manager.get_pantry_items()) == 3


def test_music_history(temp_context_dir):
    """Test music history operations."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    # Add tracks
    for i in range(150):
        manager.add_music_history(f"Track {i}")

    # Should keep only last 100
    assert len(manager.context.music_history) == 100
    assert manager.context.music_history[0] == "Track 50"

    # Get recent tracks
    recent = manager.get_music_history(limit=5)
    assert len(recent) == 5
    assert recent[-1] == "Track 149"


def test_routines_and_preferences(temp_context_dir):
    """Test routines and preferences."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    # Routines
    manager.update_routines({"morning": "coffee at 7am", "evening": "workout at 6pm"})
    routines = manager.get_routines()
    assert routines["morning"] == "coffee at 7am"

    # Preferences
    manager.update_preferences({"theme": "dark", "language": "en"})
    prefs = manager.get_preferences()
    assert prefs["theme"] == "dark"


def test_context_persistence(temp_context_dir):
    """Test context persistence to disk."""
    # Create manager and add data
    manager1 = ContextManager(user_id="test_user", storage_path=temp_context_dir)
    manager1.add_pantry_item("milk")
    manager1.update_user_profile({"name": "Test"})
    manager1.add_conversation("user", "Hello")

    # Create new manager with same user - should load saved context
    manager2 = ContextManager(user_id="test_user", storage_path=temp_context_dir)
    assert "milk" in manager2.get_pantry_items()
    assert manager2.context.user_profile["name"] == "Test"
    assert len(manager2.get_conversation_history()) == 1


def test_build_context_summary(temp_context_dir):
    """Test building context summary."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    manager.update_user_profile({"name": "Test User"})
    manager.update_pantry(["milk", "eggs", "bread"])
    manager.add_music_history("Song 1")
    manager.add_music_history("Song 2")
    manager.update_routines({"morning": "coffee"})
    manager.update_preferences({"theme": "dark"})

    summary = manager.build_context_summary()

    assert "User Profile" in summary
    assert "Pantry Items" in summary
    assert "milk" in summary
    assert "Recent Music" in summary
    assert "Routines" in summary
    assert "Preferences" in summary


def test_build_context_summary_empty(temp_context_dir):
    """Test building context summary with no data."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)

    summary = manager.build_context_summary()
    assert summary == "No context available"


def test_get_full_context(temp_context_dir):
    """Test getting full context object."""
    manager = ContextManager(user_id="test_user", storage_path=temp_context_dir)
    manager.add_pantry_item("milk")

    ctx = manager.get_full_context()
    assert isinstance(ctx, UserContext)
    assert ctx.user_id == "test_user"
    assert "milk" in ctx.pantry_items
