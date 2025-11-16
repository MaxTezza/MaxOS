from max_os.core.orchestrator import AIOperatingSystem


def test_filesystem_routing():
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text("Please archive the Reports folder")
    assert response.agent == "filesystem"
    # Agent should handle the request (not be unhandled)
    assert response.status in {"success", "error", "not_implemented"}
    # Intent should be routed to a filesystem-related action
    assert response.payload.get("intent", "").startswith("file.")


def test_developer_routing():
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text("Create a FastAPI project and push to git")
    assert response.agent == "developer"
    # Developer agent defaults to git status for generic dev requests
    assert response.status in {"success", "error"}
    assert "repo_path" in response.payload
    assert "branch" in response.payload


def test_default_fallback():
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text("What's the weather?")
    assert response.agent in {"system", "orchestrator"}
