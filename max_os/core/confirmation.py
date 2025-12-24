"""Confirmation handler for filesystem operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OperationPreview:
    """Preview of a filesystem operation."""

    operation: str  # 'copy', 'move', 'delete', 'mkdir'
    source: str | None
    destination: str | None
    file_count: int
    total_size_bytes: int
    files: list[dict[str, Any]]
    metadata: dict[str, Any] | None = None

    def format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable size."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def format_preview(self) -> str:
        """Generate human-readable preview text."""
        lines = [
            f"Operation: {self.operation.upper()}",
        ]

        if self.source:
            lines.append(
                f"Source: {self.source} ({self.file_count} files, {self.format_size(self.total_size_bytes)})"
            )

        if self.destination:
            lines.append(f"Destination: {self.destination}")

        if self.file_count > 0:
            lines.append("Files affected:")
            for file_info in self.files[:10]:  # Show max 10 files
                size_str = self.format_size(file_info.get("size_bytes", 0))
                lines.append(f"  - {file_info.get('name', 'unknown')} ({size_str})")

            if self.file_count > 10:
                lines.append(f"  ... ({self.file_count - 10} more files)")

        return "\n".join(lines)


class ConfirmationHandler:
    """Handler for operation confirmations."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize confirmation handler.

        Args:
            config: Configuration dict with settings like:
                - enabled: Whether confirmation is enabled (default: True)
                - require_for_operations: List of operations requiring confirmation
                - auto_approve_under_mb: Auto-approve operations under this size
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.require_for = set(
            self.config.get("require_for_operations", ["copy", "move", "delete"])
        )
        self.auto_approve_threshold_bytes = (
            self.config.get("auto_approve_under_mb", 10) * 1024 * 1024
        )

    def should_confirm(self, operation: str, size_bytes: int = 0) -> bool:
        """Check if operation requires confirmation.

        Args:
            operation: Operation type ('copy', 'move', 'delete', 'mkdir')
            size_bytes: Total size of operation in bytes

        Returns:
            True if confirmation is required
        """
        if not self.enabled:
            return False

        if operation not in self.require_for:
            return False

        # Auto-approve small operations
        if size_bytes < self.auto_approve_threshold_bytes:
            return False

        return True

    def generate_preview(
        self,
        operation: str,
        source: Path | None = None,
        destination: Path | None = None,
        files: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OperationPreview:
        """Generate operation preview.

        Args:
            operation: Operation type
            source: Source path
            destination: Destination path
            files: List of file info dicts with 'name', 'size_bytes', 'path'
            metadata: Additional metadata

        Returns:
            OperationPreview object
        """
        files = files or []
        total_size = sum(f.get("size_bytes", 0) for f in files)

        return OperationPreview(
            operation=operation,
            source=str(source) if source else None,
            destination=str(destination) if destination else None,
            file_count=len(files),
            total_size_bytes=total_size,
            files=files,
            metadata=metadata,
        )

    def request_confirmation(
        self,
        preview: OperationPreview,
        mode: str = "cli",
    ) -> tuple[bool, OperationPreview]:
        """Request user confirmation for an operation.

        Args:
            preview: Operation preview
            mode: 'cli' for interactive prompt, 'api' to return preview without prompting

        Returns:
            Tuple of (approved: bool, preview: OperationPreview)
        """
        # Check if confirmation is needed
        if not self.should_confirm(preview.operation, preview.total_size_bytes):
            return True, preview

        if mode == "api":
            # API mode: return preview without prompting
            return False, preview

        # CLI mode: show preview and prompt
        print("\n" + "=" * 60)
        print(preview.format_preview())
        print("=" * 60)

        try:
            response = input("\nProceed? [y/N]: ").strip().lower()
            approved = response in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled.")
            approved = False

        return approved, preview
