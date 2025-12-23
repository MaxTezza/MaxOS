from unittest.mock import patch

import fakeredis
import pytest

from max_os.core.orchestrator import AIOperatingSystem


@pytest.mark.asyncio
@patch("redis.from_url", return_value=fakeredis.FakeRedis())
async def test_filesystem_routing(mock_redis):
    orchestrator = AIOperatingSystem()
    response = await orchestrator.handle_text("Please archive the Reports folder")
    assert response.agent == "filesystem"
    # Agent should handle the request (not be unhandled)
    assert response.status in {"success", "error", "not_implemented"}
    # Intent should be routed to a filesystem-related action
    assert response.payload.get("intent", "").startswith("file.")


@pytest.mark.asyncio
@patch("redis.from_url", return_value=fakeredis.FakeRedis())
async def test_developer_routing(mock_redis):
    orchestrator = AIOperatingSystem()
    response = await orchestrator.handle_text("Create a FastAPI project and push to git")
    assert response.agent == "developer"
    # Developer agent defaults to git status for generic dev requests
    assert response.status in {"success", "error"}
    assert "repo_path" in response.payload
    assert "branch" in response.payload


@pytest.mark.asyncio
@patch("redis.from_url", return_value=fakeredis.FakeRedis())
async def test_default_fallback(mock_redis):
    orchestrator = AIOperatingSystem()
    response = await orchestrator.handle_text("What's the weather?")
    assert response.agent in {"system", "orchestrator"}
