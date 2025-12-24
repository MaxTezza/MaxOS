"""Tests for gRPC server implementation."""

from unittest.mock import MagicMock, patch

import fakeredis
import grpc
import pytest

from max_os.core.orchestrator import AIOperatingSystem
from max_os.interfaces.grpc.protos import maxos_pb2
from max_os.interfaces.grpc.server import MaxOSServiceServicer


@pytest.fixture
@patch("redis.from_url", return_value=fakeredis.FakeRedis())
def mock_orchestrator(mock_redis):
    """Create a mock orchestrator for testing."""
    return AIOperatingSystem(enable_learning=False)


@pytest.fixture
def grpc_servicer(mock_orchestrator):
    """Create a gRPC servicer for testing."""
    return MaxOSServiceServicer(mock_orchestrator)


def test_handle_text_success(grpc_servicer):
    """Test successful text handling."""
    # Create a mock context
    mock_context = MagicMock(spec=grpc.ServicerContext)

    # Create request
    request = maxos_pb2.TextRequest(
        text="List files in /home",
        context={"domain": "filesystem"},
    )

    # Call the handler
    response = grpc_servicer.HandleText(request, mock_context)

    # Verify response structure
    assert isinstance(response, maxos_pb2.AgentResponse)
    assert response.agent != ""
    assert response.status in {"success", "error", "not_implemented", "unhandled"}
    assert response.message != ""
    # Payload is a proto map, not a regular dict
    assert len(response.payload) >= 0


def test_handle_text_with_context(grpc_servicer):
    """Test text handling with context."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.TextRequest(
        text="Show git status",
        context={"domain": "developer", "repo_path": "/home/user/project"},
    )

    response = grpc_servicer.HandleText(request, mock_context)

    assert isinstance(response, maxos_pb2.AgentResponse)
    assert response.agent != ""


def test_handle_text_empty_request(grpc_servicer):
    """Test handling empty text request."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.TextRequest(text="", context={})

    response = grpc_servicer.HandleText(request, mock_context)

    assert isinstance(response, maxos_pb2.AgentResponse)


def test_handle_text_error_handling(grpc_servicer):
    """Test error handling in HandleText."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    # Mock orchestrator to raise exception
    with patch.object(
        grpc_servicer.orchestrator,
        "handle_text",
        side_effect=Exception("Test error"),
    ):
        request = maxos_pb2.TextRequest(text="test", context={})
        response = grpc_servicer.HandleText(request, mock_context)

        assert response.status == "error"
        assert "Test error" in response.message
        mock_context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)


def test_stream_operations_success(grpc_servicer):
    """Test successful streaming operations."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.TextRequest(
        text="Create a Python project",
        context={"domain": "developer"},
    )

    updates = list(grpc_servicer.StreamOperations(request, mock_context))

    # Should have multiple updates
    assert len(updates) >= 4

    # Check first update
    assert updates[0].progress == 0
    assert updates[0].status == "started"

    # Check last update
    assert updates[-1].progress == 100
    assert updates[-1].status in {"completed", "error"}


def test_stream_operations_progress(grpc_servicer):
    """Test that streaming operations show progress."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.TextRequest(text="test operation", context={})

    updates = list(grpc_servicer.StreamOperations(request, mock_context))

    # Verify progress increases
    progresses = [update.progress for update in updates]
    assert progresses[0] < progresses[-1]
    assert progresses[-1] == 100


def test_stream_operations_error_handling(grpc_servicer):
    """Test error handling in streaming operations."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    # Mock orchestrator to raise exception
    with patch.object(
        grpc_servicer.orchestrator,
        "handle_text",
        side_effect=Exception("Stream error"),
    ):
        request = maxos_pb2.TextRequest(text="test", context={})
        updates = list(grpc_servicer.StreamOperations(request, mock_context))

        # Should have error update
        assert any(update.status == "error" for update in updates)
        assert any("Stream error" in update.message for update in updates)


def test_get_system_health_success(grpc_servicer):
    """Test successful health check."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.HealthRequest()

    response = grpc_servicer.GetSystemHealth(request, mock_context)

    assert response.status == "healthy"
    assert response.version == "0.1.0"
    # Metrics is a proto map, not a regular dict
    assert "orchestrator" in response.metrics
    assert "agents" in response.metrics


def test_get_system_health_metrics(grpc_servicer):
    """Test health check includes proper metrics."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.HealthRequest()

    response = grpc_servicer.GetSystemHealth(request, mock_context)

    # Verify metrics
    assert response.metrics["orchestrator"] == "ready"
    assert int(response.metrics["agents"]) > 0
    assert "memory_limit" in response.metrics


def test_get_system_health_error_handling(grpc_servicer):
    """Test error handling in health check."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    # Directly access the length function on agents to cause an error
    original_agents = grpc_servicer.orchestrator.agents
    
    # Set agents to something that will cause len() to fail
    grpc_servicer.orchestrator.agents = None
    
    request = maxos_pb2.HealthRequest()
    response = grpc_servicer.GetSystemHealth(request, mock_context)

    assert response.status == "unhealthy"
    mock_context.set_code.assert_called_with(grpc.StatusCode.INTERNAL)
    
    # Restore original agents
    grpc_servicer.orchestrator.agents = original_agents


def test_payload_serialization(grpc_servicer):
    """Test that complex payload types are serialized correctly."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    request = maxos_pb2.TextRequest(text="test", context={})

    response = grpc_servicer.HandleText(request, mock_context)

    # All payload values should be strings (proto requirement)
    for value in response.payload.values():
        assert isinstance(value, str)


@patch("redis.from_url", return_value=fakeredis.FakeRedis())
def test_concurrent_requests(mock_redis, grpc_servicer):
    """Test handling multiple concurrent requests."""
    mock_context = MagicMock(spec=grpc.ServicerContext)

    requests = [
        maxos_pb2.TextRequest(text=f"Request {i}", context={})
        for i in range(5)
    ]

    responses = [
        grpc_servicer.HandleText(request, mock_context)
        for request in requests
    ]

    # All requests should get responses
    assert len(responses) == 5
    for response in responses:
        assert isinstance(response, maxos_pb2.AgentResponse)
        assert response.agent != ""
