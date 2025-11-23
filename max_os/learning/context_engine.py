"""Context awareness engine that gathers real-time signals about the host."""
from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
import structlog
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = structlog.get_logger("max_os.context_engine")


@dataclass
class ContextSignals:
    """Structured representation of gathered signals."""

    system: dict[str, Any] = field(default_factory=dict)
    processes: dict[str, Any] = field(default_factory=dict)
    git: dict[str, Any] = field(default_factory=dict)
    filesystem: dict[str, Any] = field(default_factory=dict)
    time: dict[str, Any] = field(default_factory=dict)
    network: dict[str, Any] = field(default_factory=dict)
    applications: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "processes": self.processes,
            "git": self.git,
            "filesystem": self.filesystem,
            "time": self.time,
            "network": self.network,
            "applications": self.applications,
        }


class FileChangeEventHandler(FileSystemEventHandler):
    def __init__(self, context_engine: ContextAwarenessEngine, max_events=100):
        super().__init__()
        self.context_engine = context_engine
        self.events = []
        self.lock = threading.Lock()
        self.max_events = max_events

    def on_any_event(self, event):
        with self.lock:
            self.events.append({
                "event_type": event.event_type,
                "src_path": event.src_path,
                "is_directory": event.is_directory,
                "timestamp": datetime.now(UTC).isoformat(),
            })
            if len(self.events) > self.max_events:
                self.events.pop(0)
            
            # Invalidate repo cache if a change is detected in a .git directory
            if ".git" in event.src_path:
                self.context_engine.invalidate_repo_cache()

    def get_events(self):
        with self.lock:
            events = list(self.events)
            self.events.clear()
            return events

class ContextAwarenessEngine:
    """Collects signals about the local environment for predictive agents."""

    def __init__(
        self,
        repo_paths: list[Path] | None = None,
        downloads_dir: Path | None = None,
        tracked_dirs: list[Path] | None = None,
    ) -> None:
        self.logger = structlog.get_logger("max_os.context_engine")
        self.repo_cache_ttl = timedelta(
            seconds=int(os.environ.get("MAXOS_REPO_CACHE_TTL", "3600"))
        )
        self.max_repo_results = int(os.environ.get("MAXOS_REPO_LIMIT", "25"))
        self.max_repo_scan_depth = int(os.environ.get("MAXOS_REPO_SCAN_DEPTH", "2"))
        self.repo_paths = repo_paths or self._discover_repos()
        self.downloads_dir = downloads_dir or Path.home() / "Downloads"
        self.tracked_dirs = tracked_dirs or self._default_tracked_dirs()
        self.fs_event_handler = FileChangeEventHandler(self)
        self._start_filesystem_observer()

    def _start_filesystem_observer(self):
        try:
            observer = Observer()
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("Failed to initialize filesystem observer", exc_info=exc)
            self.observer = None
            return

        scheduled = False
        for path in self.tracked_dirs:
            try:
                if path.exists():
                    observer.schedule(self.fs_event_handler, str(path), recursive=True)
                    scheduled = True
            except Exception as exc:  # noqa: BLE001
                self.logger.debug("Unable to watch %s", path, exc_info=exc)

        if scheduled:
            observer.start()
            self.observer = observer
        else:
            self.logger.debug("No directories scheduled for filesystem monitoring.")
            self.observer = None

    def shutdown(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def invalidate_repo_cache(self):
        cache_path = self._get_repo_cache_path()
        if cache_path.exists():
            cache_path.unlink()
            self.logger.info("Git repo cache invalidated.")



    async def gather_all_signals(self, timeout: float | None = None) -> dict[str, Any]:
        """Collect every available signal about the current state."""
        async def _collect():
            return await asyncio.gather(
                self._gather_system_metrics(),
                self._gather_processes(),
                self._gather_git_signals(),
                self._gather_filesystem_signals(),
                self._gather_time_signals(),
                self._gather_network_signals(),
                self._gather_application_signals(),
                return_exceptions=True,
            )

        if timeout:
            results = await asyncio.wait_for(_collect(), timeout=timeout)
        else:
            results = await _collect()

        signals = ContextSignals()
        (
            signals.system,
            signals.processes,
            signals.git,
            signals.filesystem,
            signals.time,
            signals.network,
            signals.applications,
        ) = [self._unwrap_result(result) for result in results]

        return signals.to_dict()

    def _unwrap_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, Exception):
            logger.warning("Context signal collection failed", exc_info=result)
            return {"error": str(result)}
        return result

    async def _gather_system_metrics(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect_system_metrics)

    def _collect_system_metrics(self) -> dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "load_average": self._safe_load_average(),
            },
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
            },
            "uptime_seconds": max(0, int(datetime.now().timestamp() - psutil.boot_time())),
        }

    async def _gather_processes(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect_processes)

    def _collect_processes(self) -> dict[str, Any]:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                processes.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"],
                        "user": info["username"],
                        "cpu_percent": round(info["cpu_percent"], 2),
                        "memory_percent": round(info["memory_percent"], 2),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda item: (item["cpu_percent"], item["memory_percent"]), reverse=True)
        top_processes = processes[:15]

        return {
            "total": len(processes),
            "top_processes": top_processes,
        }

    async def _gather_git_signals(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect_git_signals)

    def _collect_git_signals(self) -> dict[str, Any]:
        repo_statuses = []
        for repo in self.repo_paths:
            if not repo.exists() or not (repo / ".git").exists():
                continue

            try:
                status = self._git_status(repo)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to read git status for %s", repo, exc_info=exc)
                status = {"path": str(repo), "error": str(exc)}
            repo_statuses.append(status)

        dirty = [repo for repo in repo_statuses if not repo.get("clean", True)]
        return {
            "repos": repo_statuses,
            "dirty_count": len(dirty),
        }

    def _git_status(self, repo: Path) -> dict[str, Any]:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--branch"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip().splitlines()
        branch = output[0].replace("## ", "") if output else "unknown"
        file_lines = output[1:] if len(output) > 1 else []

        staged, modified, untracked = [], [], []
        for line in file_lines:
            if not line:
                continue
            status_index = line[0]
            status_worktree = line[1]
            filepath = line[3:]
            
            if status_index == "?":
                untracked.append(filepath)
            else:
                if status_index in {"M", "A", "D", "R", "C"}: # Staged changes
                    staged.append(filepath)
                if status_worktree in {"M", "D"}: # Modified or deleted in working tree
                    modified.append(filepath)

        return {
            "path": str(repo),
            "branch": branch,
            "staged": staged,
            "modified": modified,
            "untracked": untracked,
            "clean": len(staged) == 0 and len(modified) == 0 and len(untracked) == 0,
        }

    async def _gather_filesystem_signals(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect_filesystem_signals)

    def _collect_filesystem_signals(self) -> dict[str, Any]:
        downloads = self._recent_files(self.downloads_dir, limit=5)
        tracked = {
            str(directory): self._recent_files(directory, limit=3)
            for directory in self.tracked_dirs
            if directory.exists()
        }
        recent_events = self.fs_event_handler.get_events() if self.observer else []

        return {
            "downloads": downloads,
            "tracked_dirs": tracked,
            "recent_events": recent_events,
        }

    async def _gather_time_signals(self) -> dict[str, Any]:
        now = datetime.now()
        return {
            "time_of_day": now.strftime("%H:%M"),
            "day_of_week": now.strftime("%A"),
            "timestamp": now.isoformat(),
        }

    async def _gather_network_signals(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect_network_signals)

    def _collect_network_signals(self) -> dict[str, Any]:
        net_io = psutil.net_io_counters(pernic=True)
        interfaces = {}
        for name, stats in net_io.items():
            interfaces[name] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
            }
        connections = []
        try:
            for conn in psutil.net_connections(kind="inet"):
                connections.append(
                    {
                        "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        "raddr": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        "status": conn.status,
                        "pid": conn.pid,
                    }
                )
        except psutil.AccessDenied:
            logger.debug("Access denied while reading network connections")

        return {
            "interfaces": interfaces,
            "connection_count": len(connections),
        }

    async def _gather_application_signals(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._collect_application_signals)

    def _collect_application_signals(self) -> dict[str, Any]:
        active_window = self._get_active_window()
        clipboard = self._get_clipboard_contents()

        return {
            "active_window": active_window,
            "clipboard_preview": clipboard[:1000] if clipboard else None,
        }

    def _recent_files(self, directory: Path, limit: int = 5) -> list[dict[str, Any]]:
        if not directory.exists():
            return []

        entries = []
        try:
            for path in directory.iterdir():
                if len(entries) >= 200:
                    break
                if path.is_file():
                    stat = path.stat()
                    entries.append(
                        {
                            "path": str(path),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "size_kb": round(stat.st_size / 1024, 2),
                        }
                    )
        except PermissionError:
            return []

        entries.sort(key=lambda item: item["modified"], reverse=True)
        return entries[:limit]

    def _safe_load_average(self) -> dict[str, float]:
        try:
            load1, load5, load15 = os.getloadavg()
            return {"1min": load1, "5min": load5, "15min": load15}
        except (AttributeError, OSError):
            return {"1min": 0.0, "5min": 0.0, "15min": 0.0}

    def _get_repo_cache_path(self) -> Path:
        cache_dir = Path.home() / ".maxos" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "repos.json"

    def _load_repos_from_cache(self) -> list[Path] | None:
        cache_path = self._get_repo_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path) as f:
                    cache_data = json.load(f)
                    timestamp = datetime.fromisoformat(cache_data["timestamp"])
                    if datetime.now() - timestamp < self.repo_cache_ttl:
                        return [Path(p) for p in cache_data["repos"]]
            except (json.JSONDecodeError, KeyError, ValueError):
                logger.warning("Failed to load repo cache, performing full scan.")
        return None

    def _save_repos_to_cache(self, repos: list[Path]) -> None:
        cache_path = self._get_repo_cache_path()
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "repos": [str(p) for p in repos],
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

    def _scan_for_repos(self) -> list[Path]:
        # Allow overrides through env var e.g. "/home/user/src:/srv/repos"
        env_paths = os.environ.get("MAXOS_REPO_PATHS")
        candidate_roots = [Path.cwd()]
        if env_paths:
            candidate_roots.extend(Path(path).expanduser() for path in env_paths.split(os.pathsep))
        github_dir = Path.home() / "GitHub"
        if github_dir.exists():
            candidate_roots.append(github_dir)
        projects_dir = Path.home() / "Projects"
        if projects_dir.exists():
            candidate_roots.append(projects_dir)

        skip_dirs = {".git", ".hg", ".svn", ".venv", "node_modules", "__pycache__"}
        queue = deque()
        seen: set[Path] = set()

        for root in candidate_roots:
            root = root.expanduser()
            try:
                resolved = root.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            queue.append((resolved, 0))

        repos: list[Path] = []
        while queue and len(repos) < self.max_repo_results:
            current, depth = queue.popleft()
            if not current.exists() or not current.is_dir():
                continue

            if (current / ".git").exists():
                repos.append(current)
                continue

            if depth >= self.max_repo_scan_depth:
                continue

            try:
                for entry in current.iterdir():
                    if not entry.is_dir():
                        continue
                    if entry.name in skip_dirs or entry.name.startswith("."):
                        continue
                    try:
                        resolved_child = entry.resolve()
                    except OSError:
                        continue
                    if resolved_child in seen:
                        continue
                    seen.add(resolved_child)
                    queue.append((resolved_child, depth + 1))
            except PermissionError:
                continue

        return repos

    def _discover_repos(self) -> list[Path]:
        cached_repos = self._load_repos_from_cache()
        if cached_repos:
            logger.debug("Loaded repos from cache.")
            return cached_repos

        logger.debug("Repo cache invalid or not found, performing full scan.")
        repos = self._scan_for_repos()
        self._save_repos_to_cache(repos)
        return repos

    def _default_tracked_dirs(self) -> list[Path]:
        candidates = [
            Path.cwd(),
            Path.home() / "Documents",
            Path.home() / "Downloads",
            Path.home() / "Desktop",
        ]
        existing = [path for path in candidates if path.exists()]
        return existing or [Path.cwd()]

    def _get_active_window(self) -> str | None:
        system = platform.system().lower()
        try:
            if system == "darwin":
                return self._run_command(["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'])
            if system == "linux":
                if shutil.which("xdotool"):
                    return self._run_command(["xdotool", "getactivewindow", "getwindowname"])
                if shutil.which("wmctrl"):
                    output = self._run_command(["wmctrl", "-lp"])
                    return output.splitlines()[0] if output else None
                wayland_window = self._get_wayland_active_window()
                if wayland_window:
                    return wayland_window
            if system == "windows":
                return None  # Placeholder until win32 APIs are wired up
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to get active window", exc_info=exc)
        return None

    def _get_wayland_active_window(self) -> str | None:
        """Attempt to read focused window metadata on Wayland compositors."""
        if os.environ.get("XDG_SESSION_TYPE", "").lower() != "wayland":
            return None

        if shutil.which("swaymsg"):
            output = self._run_command(["swaymsg", "-t", "get_tree"])
            if output:
                try:
                    data = json.loads(output)
                    return self._find_focused_sway_node(data)
                except json.JSONDecodeError:
                    return None

        if shutil.which("hyprctl"):
            output = self._run_command(["hyprctl", "activewindow", "-j"])
            if output:
                try:
                    data = json.loads(output)
                    return data.get("title") or data.get("class")
                except json.JSONDecodeError:
                    return None

        if shutil.which("grimshot"):  # Placeholder command available in wlroots setups
            return "wayland-session"  # Known but unspecified

        return None

    def _find_focused_sway_node(self, node: dict[str, Any]) -> str | None:
        if node.get("focused"):
            return node.get("name")
        for child_key in ("nodes", "floating_nodes"):
            for child in node.get(child_key, []):
                result = self._find_focused_sway_node(child)
                if result:
                    return result
        return None

    def _get_clipboard_contents(self) -> str | None:
        system = platform.system().lower()
        commands = []
        if system == "darwin":
            commands.append(["pbpaste"])
        elif system == "linux":
            # Check for Wayland
            if os.environ.get("XDG_SESSION_TYPE") == "wayland":
                # Acknowledge Wayland limitation (can be tricky with subprocess)
                return "Clipboard access not reliably available on Wayland."
            
            if shutil.which("xclip"):
                commands.append(["xclip", "-selection", "clipboard", "-o"])
            if shutil.which("wl-paste"):
                commands.append(["wl-paste"])
            if shutil.which("xsel"):
                commands.append(["xsel", "--clipboard", "--output"])

        for command in commands:
            try:
                output = self._run_command(command)
                if output:
                    return output.strip()
            except Exception as exc:  # noqa: BLE001
                self.logger.debug("Clipboard command failed: %s", command, exc_info=exc)
                continue
        return None

    def _run_command(self, command: list[str]) -> str | None:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
