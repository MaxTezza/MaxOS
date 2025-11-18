import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta
import json
import os

from max_os.learning.context_engine import ContextAwarenessEngine, FileChangeEventHandler

@pytest.fixture
def mock_paths(tmp_path):
    # Mock Path.home() to return a temporary directory
    with patch('pathlib.Path.home', return_value=tmp_path) as mock_home:
        yield tmp_path

@pytest.fixture
def context_engine(mock_paths):
    # mock_paths is now the tmp_path fixture
    temp_home = mock_paths
    
    # Ensure cache directory exists for testing within the temporary home
    cache_dir = temp_home / ".maxos/cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create mock repo and docs directories within the temporary home
    repo1_path = temp_home / "repo1"
    repo1_path.mkdir()
    (repo1_path / ".git").mkdir()

    docs_path = temp_home / "docs"
    docs_path.mkdir()

    return ContextAwarenessEngine(repo_paths=[repo1_path], tracked_dirs=[docs_path])

@pytest.mark.asyncio
async def test_gather_system_metrics(context_engine):
    with patch('psutil.cpu_percent', return_value=10.0), \
         patch('psutil.cpu_count', return_value=4), \
         patch('psutil.virtual_memory') as mock_vm, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.boot_time', return_value=datetime.now().timestamp() - 3600), \
         patch('os.getloadavg', return_value=(0.5, 0.4, 0.3)):
        
        mock_vm.return_value = MagicMock(total=16*1024**3, available=8*1024**3, used=8*1024**3, percent=50.0)
        mock_disk.return_value = MagicMock(total=100*1024**3, used=50*1024**3, free=50*1024**3, percent=50.0)

        metrics = await context_engine._gather_system_metrics()
        assert metrics['cpu']['percent'] == 10.0
        assert metrics['memory']['percent'] == 50.0
        assert metrics['disk']['percent'] == 50.0
        assert 'uptime_seconds' in metrics

@pytest.mark.asyncio
async def test_gather_processes(context_engine):
    mock_process = MagicMock()
    mock_process.info = {'pid': 1, 'name': 'test_proc', 'username': 'user', 'cpu_percent': 5.0, 'memory_percent': 2.0}
    with patch('psutil.process_iter', return_value=[mock_process]):
        processes = await context_engine._gather_processes()
        assert processes['total'] == 1
        assert processes['top_processes'][0]['name'] == 'test_proc'

@pytest.mark.asyncio
async def test_git_status(context_engine):
    # Use one of the pre-created repo paths from the fixture
    mock_repo_path = context_engine.repo_paths[0]

    mock_subprocess_run_result = MagicMock()
    mock_subprocess_run_result.stdout = "## master...origin/master [ahead 2]\n M file1.txt\n?? untracked.txt"
    mock_subprocess_run_result.stderr = ""
    mock_subprocess_run_result.returncode = 0
    with patch('subprocess.run', return_value=mock_subprocess_run_result):
        status = context_engine._git_status(mock_repo_path)
        assert status['branch'] == "master...origin/master [ahead 2]"
        assert "file1.txt" in status['modified']
        assert "untracked.txt" in status['untracked']
        assert not status['clean']

@pytest.mark.asyncio
async def test_discover_repos_from_cache(context_engine, mock_paths):
    cache_path = context_engine._get_repo_cache_path()
    cached_data = {
        "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
        "repos": [str(mock_paths / "cached_repo1"), str(mock_paths / "cached_repo2")]
    }
    with open(cache_path, "w") as f:
        json.dump(cached_data, f)
    
    repos = context_engine._discover_repos()
    assert len(repos) == 2
    assert Path(str(mock_paths / "cached_repo1")) in repos

@pytest.mark.asyncio
async def test_discover_repos_full_scan(context_engine):
    cache_path = context_engine._get_repo_cache_path()
    if cache_path.exists():
        cache_path.unlink() # Ensure no cache

    with patch.object(context_engine, '_scan_for_repos', return_value=[Path("/mock/home/scanned_repo")]) as mock_scan:
        repos = context_engine._discover_repos()
        mock_scan.assert_called_once()
        assert len(repos) == 1
        assert Path("/mock/home/scanned_repo") in repos
        assert cache_path.exists() # Should have saved to cache

def test_file_change_event_handler_invalidates_cache(context_engine, mock_paths):
    # Create a mock .git directory within the temporary home
    mock_git_dir = mock_paths / "repo_to_watch/.git"
    mock_git_dir.mkdir(parents=True, exist_ok=True)
    
    mock_event = MagicMock(src_path=str(mock_git_dir / "config"), is_directory=False)
    handler = FileChangeEventHandler(context_engine)
    
    with patch.object(context_engine, 'invalidate_repo_cache') as mock_invalidate:
        handler.on_any_event(mock_event)
        mock_invalidate.assert_called_once()

def test_file_change_event_handler_stores_events(context_engine, mock_paths):
    mock_docs_dir = mock_paths / "docs"
    mock_file_path = mock_docs_dir / "file.txt"
    mock_file_path.touch() # Create the file for the event
    
    mock_event = MagicMock(src_path=str(mock_file_path), is_directory=False, event_type="created")
    handler = FileChangeEventHandler(context_engine)
    
    handler.on_any_event(mock_event)
    events = handler.get_events()
    assert len(events) == 1
    assert events[0]['src_path'] == str(mock_file_path)
    assert events[0]['event_type'] == "created"
