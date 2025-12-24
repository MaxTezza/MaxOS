"""Tests for confirmation handler."""

from max_os.core.confirmation import ConfirmationHandler, OperationPreview


def test_operation_preview_formatting():
    """Test preview formatting."""
    files = [
        {"name": "file1.txt", "size_bytes": 1024},
        {"name": "file2.txt", "size_bytes": 2048},
    ]

    preview = OperationPreview(
        operation="copy",
        source="/home/user/source",
        destination="/home/user/dest",
        file_count=2,
        total_size_bytes=3072,
        files=files,
    )

    formatted = preview.format_preview()
    assert "Operation: COPY" in formatted
    assert "Source: /home/user/source" in formatted
    assert "Destination: /home/user/dest" in formatted
    assert "file1.txt" in formatted
    assert "file2.txt" in formatted


def test_format_size():
    """Test size formatting."""
    preview = OperationPreview(
        operation="copy",
        source=None,
        destination=None,
        file_count=0,
        total_size_bytes=0,
        files=[],
    )

    assert preview.format_size(512) == "512 B"
    assert preview.format_size(1024) == "1.0 KB"
    assert preview.format_size(1024 * 1024) == "1.0 MB"
    assert preview.format_size(1024 * 1024 * 1024) == "1.0 GB"


def test_confirmation_handler_defaults():
    """Test confirmation handler with default config."""
    handler = ConfirmationHandler()

    assert handler.enabled is True
    assert "copy" in handler.require_for
    assert "move" in handler.require_for
    assert "delete" in handler.require_for


def test_confirmation_handler_custom_config():
    """Test confirmation handler with custom config."""
    config = {
        "enabled": False,
        "require_for_operations": ["delete"],
        "auto_approve_under_mb": 5,
    }

    handler = ConfirmationHandler(config)

    assert handler.enabled is False
    assert "delete" in handler.require_for
    assert "copy" not in handler.require_for
    assert handler.auto_approve_threshold_bytes == 5 * 1024 * 1024


def test_should_confirm():
    """Test confirmation requirement logic."""
    handler = ConfirmationHandler(
        {
            "enabled": True,
            "require_for_operations": ["copy", "delete"],
            "auto_approve_under_mb": 10,
        }
    )

    # Should confirm large copy
    assert handler.should_confirm("copy", 20 * 1024 * 1024) is True

    # Should not confirm small copy (auto-approved)
    assert handler.should_confirm("copy", 5 * 1024 * 1024) is False

    # Should not confirm mkdir (not in require list)
    assert handler.should_confirm("mkdir", 0) is False

    # Should confirm large delete
    assert handler.should_confirm("delete", 20 * 1024 * 1024) is True


def test_generate_preview():
    """Test preview generation."""
    handler = ConfirmationHandler()

    files = [
        {"name": "test.txt", "size_bytes": 1000},
        {"name": "test2.txt", "size_bytes": 2000},
    ]

    preview = handler.generate_preview(
        operation="copy",
        source="/home/user/source",
        destination="/home/user/dest",
        files=files,
    )

    assert preview.operation == "copy"
    assert preview.source == "/home/user/source"
    assert preview.destination == "/home/user/dest"
    assert preview.file_count == 2
    assert preview.total_size_bytes == 3000
    assert len(preview.files) == 2


def test_request_confirmation_api_mode():
    """Test confirmation in API mode (returns preview without prompting)."""
    handler = ConfirmationHandler()

    files = [{"name": "large.txt", "size_bytes": 20 * 1024 * 1024}]
    preview = handler.generate_preview(
        operation="copy",
        files=files,
    )

    # API mode should return False (not approved) with preview
    approved, returned_preview = handler.request_confirmation(preview, mode="api")

    assert approved is False
    assert returned_preview == preview


def test_request_confirmation_auto_approved():
    """Test auto-approval for small operations."""
    handler = ConfirmationHandler(
        {
            "enabled": True,
            "require_for_operations": ["copy"],
            "auto_approve_under_mb": 10,
        }
    )

    files = [{"name": "small.txt", "size_bytes": 1024}]
    preview = handler.generate_preview(
        operation="copy",
        files=files,
    )

    # Should be auto-approved due to small size
    approved, returned_preview = handler.request_confirmation(preview, mode="cli")

    assert approved is True
    assert returned_preview == preview


def test_request_confirmation_disabled():
    """Test confirmation when disabled."""
    handler = ConfirmationHandler({"enabled": False})

    files = [{"name": "large.txt", "size_bytes": 100 * 1024 * 1024}]
    preview = handler.generate_preview(
        operation="copy",
        files=files,
    )

    # Should be auto-approved when confirmation is disabled
    approved, returned_preview = handler.request_confirmation(preview, mode="cli")

    assert approved is True
    assert returned_preview == preview
