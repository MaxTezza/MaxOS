"""Developer agent for scaffolding code bases and automating workflows."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict

from max_os.agents.base import AgentRequest, AgentResponse


class DeveloperAgent:
    name = "developer"
    description = "Bootstrap projects, run tests, and coordinate CI/CD"
    capabilities = ["scaffold", "ci", "code_review", "git"]
    KEYWORDS = ("project", "repo", "code", "test", "deploy", "ci", "git", "commit", "branch")

    def __init__(self, config: Dict[str, object] | None = None) -> None:
        self.config = config or {}

    def can_handle(self, request: AgentRequest) -> bool:
        return request.intent.startswith("dev.") or any(
            keyword in request.text.lower() for keyword in self.KEYWORDS
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        text_lower = request.text.lower()

        # Route to specific handlers
        if any(word in text_lower for word in ["git status", "status", "repo status"]):
            return self._handle_git_status(request)
        elif any(word in text_lower for word in ["git log", "commits", "history"]):
            return self._handle_git_log(request)
        elif any(word in text_lower for word in ["branch", "branches"]):
            return self._handle_git_branches(request)
        elif any(word in text_lower for word in ["test", "pytest", "unittest"]):
            return self._handle_tests(request)
        elif any(word in text_lower for word in ["scaffold", "create project", "new project"]):
            return self._handle_scaffold(request)
        else:
            # Default to git status
            return self._handle_git_status(request)

    def _find_git_root(self, start_path: Path = None) -> Path | None:
        """Find the git repository root."""
        if start_path is None:
            start_path = Path.cwd()

        current = start_path.resolve()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None

    def _handle_git_status(self, request: AgentRequest) -> AgentResponse:
        """Get git repository status."""
        git_root = self._find_git_root()

        if not git_root:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Not in a git repository",
                payload={"cwd": str(Path.cwd())},
            )

        try:
            # Get status
            result = subprocess.run(
                ["git", "status", "--porcelain", "--branch"],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            lines = result.stdout.strip().split('\n')
            branch_line = lines[0] if lines else ""
            file_lines = lines[1:] if len(lines) > 1 else []

            # Parse files
            modified = []
            untracked = []
            staged = []

            for line in file_lines:
                if not line:
                    continue
                status = line[:2]
                filepath = line[3:]

                if status == "??":
                    untracked.append(filepath)
                elif status[0] in ["M", "A", "D", "R"]:
                    staged.append(filepath)
                elif status[1] in ["M", "D"]:
                    modified.append(filepath)

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Git status for {git_root.name}",
                payload={
                    "repo_path": str(git_root),
                    "branch": branch_line.replace("## ", ""),
                    "staged": staged,
                    "modified": modified,
                    "untracked": untracked,
                    "clean": len(staged) == 0 and len(modified) == 0 and len(untracked) == 0,
                },
            )
        except subprocess.TimeoutExpired:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Git command timed out",
                payload={"repo_path": str(git_root)},
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to get git status: {str(e)}",
                payload={"error": str(e), "repo_path": str(git_root)},
            )

    def _handle_git_log(self, request: AgentRequest) -> AgentResponse:
        """Get recent git commit history."""
        git_root = self._find_git_root()

        if not git_root:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Not in a git repository",
                payload={"cwd": str(Path.cwd())},
            )

        try:
            # Get last 10 commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-10", "--format=%h|%an|%ar|%s"],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    })

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Retrieved {len(commits)} recent commits",
                payload={
                    "repo_path": str(git_root),
                    "count": len(commits),
                    "commits": commits,
                },
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to get git log: {str(e)}",
                payload={"error": str(e), "repo_path": str(git_root)},
            )

    def _handle_git_branches(self, request: AgentRequest) -> AgentResponse:
        """List git branches."""
        git_root = self._find_git_root()

        if not git_root:
            return AgentResponse(
                agent=self.name,
                status="error",
                message="Not in a git repository",
                payload={"cwd": str(Path.cwd())},
            )

        try:
            # Get branches
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=git_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            branches = []
            current = None
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                is_current = line.startswith('*')
                branch_name = line[2:].strip()

                if is_current:
                    current = branch_name

                branches.append({
                    "name": branch_name,
                    "current": is_current,
                })

            return AgentResponse(
                agent=self.name,
                status="success",
                message=f"Found {len(branches)} branch(es)",
                payload={
                    "repo_path": str(git_root),
                    "current_branch": current,
                    "count": len(branches),
                    "branches": branches,
                },
            )
        except Exception as e:
            return AgentResponse(
                agent=self.name,
                status="error",
                message=f"Failed to list branches: {str(e)}",
                payload={"error": str(e), "repo_path": str(git_root)},
            )

    def _handle_tests(self, request: AgentRequest) -> AgentResponse:
        """Run tests (stub for now)."""
        return AgentResponse(
            agent=self.name,
            status="not_implemented",
            message="Test execution requires specifying test framework and path",
            payload={
                "operation": "run_tests",
                "supported_frameworks": ["pytest", "unittest", "nose"],
            },
        )

    def _handle_scaffold(self, request: AgentRequest) -> AgentResponse:
        """Scaffold new project (stub for now)."""
        return AgentResponse(
            agent=self.name,
            status="not_implemented",
            message="Project scaffolding requires project type and destination path",
            payload={
                "operation": "scaffold",
                "supported_stacks": ["python", "fastapi", "react", "nextjs"],
            },
        )
