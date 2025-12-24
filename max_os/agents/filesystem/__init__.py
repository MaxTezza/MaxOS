"""Filesystem agent: responsible for file CRUD, search, organization."""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

from max_os.agents.base import AgentRequest, AgentResponse
from max_os.core.confirmation import ConfirmationHandler
from max_os.core.rollback import RollbackManager
from max_os.core.transactions import TransactionLogger


class FileSystemAgent:
    name = "filesystem"
    description = "Manage files, directories, backups, and package installs"
    capabilities = ["search", "organize", "archive", "package_install"]
    KEYWORDS: Iterable[str] = (
        "file",
        "folder",
        "directory",
        "archive",
        "backup",
        "move",
        "copy",
        "install",
        "list",
        "ls",
        "cd",
        "pwd",
        "mkdir",
        "rm",
        "touch",
    )

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or {}
        whitelist = self.config.get("root_whitelist", ["/home"])
        self.allowed_roots = [Path(path).resolve() for path in whitelist]

        # Initialize confirmation and rollback systems
        confirmation_config = self.config.get("confirmation", {})
        self.confirmation_handler = ConfirmationHandler(confirmation_config)

        rollback_config = self.config.get("rollback", {})
        self.rollback_manager = RollbackManager(
            retention_days=rollback_config.get("trash_retention_days", 30),
            max_trash_size_gb=rollback_config.get("max_trash_size_gb", 50),
        )

        self.transaction_logger = TransactionLogger(
            db_path=self.config.get("transactions", {}).get("db_path")
        )

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("file.")

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text_lower = request.text.lower()

        # Route to specific handlers based on keywords
        if any(word in text_lower for word in ["search", "find", "scan"]):
            return self._handle_search(request)
        elif any(word in text_lower for word in ["list", "show", "ls"]):
            return self._handle_list(request)
        elif "copy" in text_lower:
            return self._handle_copy(request)
        elif "move" in text_lower:
            return self._handle_move(request)
        elif any(word in text_lower for word in ["delete", "remove", "rm"]):
            return self._handle_delete(request)
        elif any(word in text_lower for word in ["create", "mkdir"]):
            return self._handle_create_dir(request)
        elif any(word in text_lower for word in ["info", "stat", "size"]):
            return self._handle_info(request)
        else:
            # Default fallback
            return self._handle_list(request)

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed roots."""
        try:
            resolved = path.resolve()
            return any(resolved.is_relative_to(root) for root in self.allowed_roots)
        except (ValueError, OSError):
            return False

    def _extract_path_from_text(self, text: str) -> Path:
        """Extract path from natural language text, defaulting to home."""
        text_lower = text.lower()

        # Common patterns - always safe as they're under home
        if "downloads" in text_lower:
            candidate = Path.home() / "Downloads"
        elif "documents" in text_lower:
            candidate = Path.home() / "Documents"
        elif "desktop" in text_lower:
            candidate = Path.home() / "Desktop"
        elif "home" in text_lower or "~" in text:
            candidate = Path.home()
        else:
            # Try to extract explicit paths
            candidate = None
            for word in text.split():
                if "/" in word:
                    try:
                        potential_path = Path(word.strip("'\""))
                        # Validate before checking existence
                        if self._is_path_allowed(potential_path) and potential_path.exists():
                            candidate = potential_path
                            break
                    except (ValueError, OSError):
                        pass

        # Default to home if no candidate found or candidate invalid
        if candidate is None:
            return Path.home()

        # Final safety check before returning
        if not self._is_path_allowed(candidate):
            return Path.home()

        return candidate

    def _handle_search(self, request: AgentRequest) -> AgentResponse:
        """Search for files matching patterns."""
        base_path = self._extract_path_from_text(request.text)

        if not self._is_path_allowed(base_path):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {base_path} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        # Extract search pattern from text
        pattern = "*"
        text_lower = request.text.lower()

        # Look for file extensions
        extensions = [".psd", ".jpg", ".png", ".txt", ".pdf", ".py", ".js", ".md"]
        for ext in extensions:
            if ext in text_lower:
                pattern = f"*{ext}"
                break

        # Look for size constraints
        min_size = 0
        if "larger than" in text_lower or "bigger than" in text_lower:
            words = request.text.split()
            for i, word in enumerate(words):
                if word.lower() in ["larger", "bigger"] and i + 2 < len(words):
                    try:
                        size_str = words[i + 2]
                        if "mb" in size_str.lower():
                            min_size = int(size_str.lower().replace("mb", "")) * 1024 * 1024
                        elif "gb" in size_str.lower():
                            min_size = int(size_str.lower().replace("gb", "")) * 1024 * 1024 * 1024
                    except (ValueError, IndexError):
                        pass

        # Perform search
        results = []
        try:
            for item in base_path.rglob(pattern):
                if item.is_file():
                    stat = item.stat()
                    if stat.st_size >= min_size:
                        results.append(
                            {
                                "path": str(item),
                                "size_bytes": stat.st_size,
                                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                                "modified": stat.st_mtime,
                            }
                        )
        except PermissionError as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Permission denied accessing {base_path}",
                payload={"error": str(e)},
            )

        return AgentResponse(
            agent=self.name,
            status="success",
            message=f"Found {len(results)} file(s) matching criteria",
            payload={
                "search_path": str(base_path),
                "pattern": pattern,
                "min_size_bytes": min_size,
                "count": len(results),
                "files": results[:50],  # Limit to 50 results
            },
        )

    def _handle_list(self, request: AgentRequest) -> AgentResponse:
        """List directory contents."""
        target_path = self._extract_path_from_text(request.text)

        if not self._is_path_allowed(target_path):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not target_path.exists():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} does not exist",
                payload={"path": str(target_path)},
            )

        if not target_path.is_dir():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} is not a directory",
                payload={"path": str(target_path)},
            )

        # List contents
        items = []
        try:
            for item in sorted(target_path.iterdir()):
                stat = item.stat()
                items.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size_bytes": stat.st_size if item.is_file() else None,
                        "modified": stat.st_mtime,
                    }
                )
        except PermissionError as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Permission denied accessing {target_path}",
                payload={"error": str(e)},
            )

        return AgentResponse(
            agent=self.name,
            status="success",
            message=f"Listed {len(items)} items in {target_path}",
            payload={
                "path": str(target_path),
                "count": len(items),
                "items": items,
            },
        )

    def _handle_copy(self, request: AgentRequest) -> AgentResponse:
        """Copy files or directories."""
        # Extract source and destination from request text
        # For now, return not_implemented with instructions
        # A full implementation would need explicit source/dest paths from request.context

        source_path = request.context.get("source_path")
        dest_path = request.context.get("dest_path")

        if not source_path or not dest_path:
            return AgentResponse(
                agent=self.name,
                status="not_implemented",
                message="Copy operation requires explicit source and destination paths in context",
                payload={
                    "operation": "copy",
                    "requires": {
                        "source_path": "Path to source file or directory",
                        "dest_path": "Path to destination",
                    },
                },
            )

        source = Path(source_path).expanduser()
        dest = Path(dest_path).expanduser()

        # Validate paths
        if not self._is_path_allowed(source):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Source path {source} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not self._is_path_allowed(dest):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Destination path {dest} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not source.exists():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Source path {source} does not exist",
                payload={"source_path": str(source)},
            )

        # Gather files to copy
        files_to_copy = []
        if source.is_file():
            files_to_copy.append(
                {
                    "name": source.name,
                    "path": str(source),
                    "size_bytes": source.stat().st_size,
                }
            )
        else:
            # Directory - recursively gather files
            for item in source.rglob("*"):
                if item.is_file():
                    files_to_copy.append(
                        {
                            "name": str(item.relative_to(source)),
                            "path": str(item),
                            "size_bytes": item.stat().st_size,
                        }
                    )

        # Generate preview
        preview = self.confirmation_handler.generate_preview(
            operation="copy",
            source=source,
            destination=dest,
            files=files_to_copy,
        )

        # Request confirmation
        mode = request.context.get("confirmation_mode", "cli")
        approved, preview = self.confirmation_handler.request_confirmation(preview, mode=mode)

        if not approved:
            return AgentResponse(
                agent=self.name,
                status="cancelled",
                message="Copy operation cancelled by user",
                payload={"preview": preview.__dict__},
            )

        # Create transaction
        transaction_id = self.transaction_logger.log_transaction(
            operation="copy",
            status="pending",
            user_approved=approved,
            metadata={
                "source": str(source),
                "destination": str(dest),
                "file_count": len(files_to_copy),
                "total_size_bytes": preview.total_size_bytes,
            },
        )

        # Perform copy
        copied_files = []
        try:
            if source.is_file():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(dest))
                checksum = self.rollback_manager.calculate_checksum(dest)
                copied_files.append(
                    {
                        "source": str(source),
                        "destination": str(dest),
                        "checksum": checksum,
                    }
                )
            else:
                shutil.copytree(str(source), str(dest), dirs_exist_ok=True)
                # Calculate checksums for copied files
                for item in dest.rglob("*"):
                    if item.is_file():
                        checksum = self.rollback_manager.calculate_checksum(item)
                        copied_files.append(
                            {
                                "source": str(source / item.relative_to(dest)),
                                "destination": str(item),
                                "checksum": checksum,
                            }
                        )

            # Update transaction
            self.transaction_logger.update_transaction(
                transaction_id,
                status="completed",
                metadata={
                    "source": str(source),
                    "destination": str(dest),
                    "file_count": len(copied_files),
                    "total_size_bytes": preview.total_size_bytes,
                    "copied_files": copied_files,
                },
            )

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Copied {len(copied_files)} file(s) from {source} to {dest}",
                payload={
                    "transaction_id": transaction_id,
                    "source": str(source),
                    "destination": str(dest),
                    "file_count": len(copied_files),
                    "total_size_bytes": preview.total_size_bytes,
                },
            )
        except Exception as e:
            self.transaction_logger.update_transaction(transaction_id, status="failed")
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to copy: {e}",
                payload={"transaction_id": transaction_id, "error": str(e)},
            )

    def _handle_move(self, request: AgentRequest) -> AgentResponse:
        """Move files or directories."""
        # Extract source and destination from request context
        source_path = request.context.get("source_path")
        dest_path = request.context.get("dest_path")

        if not source_path or not dest_path:
            return AgentResponse(
                agent=self.name,
                status="not_implemented",
                message="Move operation requires explicit source and destination paths in context",
                payload={
                    "operation": "move",
                    "requires": {
                        "source_path": "Path to source file or directory",
                        "dest_path": "Path to destination",
                    },
                },
            )

        source = Path(source_path).expanduser()
        dest = Path(dest_path).expanduser()

        # Validate paths
        if not self._is_path_allowed(source):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Source path {source} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not self._is_path_allowed(dest):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Destination path {dest} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not source.exists():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Source path {source} does not exist",
                payload={"source_path": str(source)},
            )

        # Gather files to move
        files_to_move = []
        if source.is_file():
            files_to_move.append(
                {
                    "name": source.name,
                    "path": str(source),
                    "size_bytes": source.stat().st_size,
                }
            )
        else:
            for item in source.rglob("*"):
                if item.is_file():
                    files_to_move.append(
                        {
                            "name": str(item.relative_to(source)),
                            "path": str(item),
                            "size_bytes": item.stat().st_size,
                        }
                    )

        # Generate preview
        preview = self.confirmation_handler.generate_preview(
            operation="move",
            source=source,
            destination=dest,
            files=files_to_move,
        )

        # Request confirmation
        mode = request.context.get("confirmation_mode", "cli")
        approved, preview = self.confirmation_handler.request_confirmation(preview, mode=mode)

        if not approved:
            return AgentResponse(
                agent=self.name,
                status="cancelled",
                message="Move operation cancelled by user",
                payload={"preview": preview.__dict__},
            )

        # Create transaction with rollback info
        moved_files = []
        for file_info in files_to_move:
            moved_files.append(
                {
                    "original_path": file_info["path"],
                    "destination": (
                        str(dest / Path(file_info["path"]).relative_to(source))
                        if source.is_dir()
                        else str(dest)
                    ),
                }
            )

        transaction_id = self.transaction_logger.log_transaction(
            operation="move",
            status="pending",
            user_approved=approved,
            metadata={
                "source": str(source),
                "destination": str(dest),
                "file_count": len(files_to_move),
                "total_size_bytes": preview.total_size_bytes,
            },
            rollback_info={
                "moved_files": moved_files,
            },
        )

        # Perform move
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest))

            # Update transaction
            self.transaction_logger.update_transaction(transaction_id, status="completed")

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Moved {len(files_to_move)} file(s) from {source} to {dest}",
                payload={
                    "transaction_id": transaction_id,
                    "source": str(source),
                    "destination": str(dest),
                    "file_count": len(files_to_move),
                    "total_size_bytes": preview.total_size_bytes,
                },
            )
        except Exception as e:
            self.transaction_logger.update_transaction(transaction_id, status="failed")
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to move: {e}",
                payload={"transaction_id": transaction_id, "error": str(e)},
            )

    def _handle_create_dir(self, request: AgentRequest) -> AgentResponse:
        """Create a new directory."""
        # Extract path from request context
        dir_path = request.context.get("path")

        if not dir_path:
            return AgentResponse(
                agent=self.name,
                status="not_implemented",
                message="Directory creation requires explicit path in context",
                payload={
                    "operation": "mkdir",
                    "requires": {"path": "Path to directory to create"},
                },
            )

        target_path = Path(dir_path).expanduser()

        # Validate path
        if not self._is_path_allowed(target_path):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if target_path.exists():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} already exists",
                payload={"path": str(target_path)},
            )

        # Generate preview
        preview = self.confirmation_handler.generate_preview(
            operation="mkdir",
            destination=target_path,
            files=[],
            metadata={"path": str(target_path)},
        )

        # Request confirmation
        mode = request.context.get("confirmation_mode", "cli")
        approved, preview = self.confirmation_handler.request_confirmation(preview, mode=mode)

        if not approved:
            return AgentResponse(
                agent=self.name,
                status="cancelled",
                message="Directory creation cancelled by user",
                payload={"preview": preview.__dict__},
            )

        # Create transaction
        transaction_id = self.transaction_logger.log_transaction(
            operation="mkdir",
            status="pending",
            user_approved=approved,
            metadata={"path": str(target_path)},
        )

        # Create directory
        try:
            target_path.mkdir(parents=True, exist_ok=False)

            # Update transaction
            self.transaction_logger.update_transaction(transaction_id, status="completed")

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Created directory {target_path}",
                payload={
                    "transaction_id": transaction_id,
                    "path": str(target_path),
                },
            )
        except Exception as e:
            self.transaction_logger.update_transaction(transaction_id, status="failed")
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to create directory: {e}",
                payload={"transaction_id": transaction_id, "error": str(e)},
            )

    def _handle_delete(self, request: AgentRequest) -> AgentResponse:
        """Delete files or directories (moves to trash)."""
        # Extract path from request context
        target_path_str = request.context.get("path")

        if not target_path_str:
            return AgentResponse(
                agent=self.name,
                status="not_implemented",
                message="Delete operation requires explicit path in context",
                payload={
                    "operation": "delete",
                    "requires": {"path": "Path to file or directory to delete"},
                },
            )

        target_path = Path(target_path_str).expanduser()

        # Validate path
        if not self._is_path_allowed(target_path):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not target_path.exists():
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} does not exist",
                payload={"path": str(target_path)},
            )

        # Gather files to delete
        files_to_delete = []
        if target_path.is_file():
            files_to_delete.append(
                {
                    "name": target_path.name,
                    "path": str(target_path),
                    "size_bytes": target_path.stat().st_size,
                }
            )
        else:
            for item in target_path.rglob("*"):
                if item.is_file():
                    files_to_delete.append(
                        {
                            "name": str(item.relative_to(target_path)),
                            "path": str(item),
                            "size_bytes": item.stat().st_size,
                        }
                    )

        # Generate preview
        preview = self.confirmation_handler.generate_preview(
            operation="delete",
            source=target_path,
            files=files_to_delete,
            metadata={"will_move_to_trash": True},
        )

        # Request confirmation
        mode = request.context.get("confirmation_mode", "cli")
        approved, preview = self.confirmation_handler.request_confirmation(preview, mode=mode)

        if not approved:
            return AgentResponse(
                agent=self.name,
                status="cancelled",
                message="Delete operation cancelled by user",
                payload={"preview": preview.__dict__},
            )

        # Create transaction
        transaction_id = self.transaction_logger.log_transaction(
            operation="delete",
            status="pending",
            user_approved=approved,
            metadata={
                "path": str(target_path),
                "file_count": len(files_to_delete),
                "total_size_bytes": preview.total_size_bytes,
            },
        )

        # Move to trash
        try:
            trash_path = self.rollback_manager.move_to_trash(
                target_path, transaction_id, original_path=target_path
            )

            # Update transaction
            self.transaction_logger.update_transaction(
                transaction_id,
                status="completed",
                rollback_info={
                    "trash_path": str(trash_path),
                    "original_path": str(target_path),
                },
            )

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Deleted {len(files_to_delete)} file(s), moved to trash (transaction {transaction_id})",
                payload={
                    "transaction_id": transaction_id,
                    "path": str(target_path),
                    "file_count": len(files_to_delete),
                    "total_size_bytes": preview.total_size_bytes,
                    "trash_path": str(trash_path),
                    "recoverable": True,
                },
            )
        except Exception as e:
            self.transaction_logger.update_transaction(transaction_id, status="failed")
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to delete: {e}",
                payload={"transaction_id": transaction_id, "error": str(e)},
            )

    def _handle_info(self, request: AgentRequest) -> AgentResponse:
        """Get file/directory information."""
        target_path = self._extract_path_from_text(request.text)

        if not self._is_path_allowed(target_path):
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} is outside allowed roots",
                payload={"allowed_roots": [str(r) for r in self.allowed_roots]},
            )

        if not target_path.exists():
            # Check if file might be in trash
            trash_files = self.rollback_manager.list_trash()
            matching_trash = [f for f in trash_files if f["original_path"] == str(target_path)]

            if matching_trash:
                return AgentResponse(
                    agent=self.name,
                    status="not_found",
                    message=f"Path {target_path} does not exist, but found in trash",
                    payload={
                        "path": str(target_path),
                        "in_trash": True,
                        "trash_entries": matching_trash,
                        "recovery_hint": "Use --restore <transaction_id> to recover",
                    },
                )

            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Path {target_path} does not exist",
                payload={"path": str(target_path)},
            )

        stat = target_path.stat()
        info = {
            "path": str(target_path),
            "name": target_path.name,
            "type": "directory" if target_path.is_dir() else "file",
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "permissions": oct(stat.st_mode)[-3:],
        }

        return AgentResponse(
            agent=self.name,
            status="success",
            message=f"Retrieved info for {target_path.name}",
            payload=info,
        )
