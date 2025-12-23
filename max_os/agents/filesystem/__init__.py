"""Filesystem agent: responsible for file CRUD, search, organization."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from max_os.agents.base import AgentRequest, AgentResponse


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
        return AgentResponse(
            agent=self.name,
            status="not_implemented",
            message="Copy operation requires explicit source and destination paths",
            payload={"operation": "copy", "requires": ["source_path", "dest_path"]},
        )

    def _handle_move(self, request: AgentRequest) -> AgentResponse:
        """Move files or directories."""
        return AgentResponse(
            agent=self.name,
            status="not_implemented",
            message="Move operation requires explicit source and destination paths",
            payload={"operation": "move", "requires": ["source_path", "dest_path"]},
        )

    def _handle_create_dir(self, request: AgentRequest) -> AgentResponse:
        """Create a new directory."""
        return AgentResponse(
            agent=self.name,
            status="not_implemented",
            message="Directory creation requires explicit path and confirmation",
            payload={"operation": "mkdir", "requires": ["path", "confirmation"]},
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
