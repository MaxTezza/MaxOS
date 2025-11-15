from max_os.core.orchestrator import AIOperatingSystem


def test_filesystem_routing():
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text("Please archive the Reports folder")
    assert response.agent == "filesystem"
    assert response.status == "planned"


def test_developer_routing():
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text("Create a FastAPI project and push to git")
    assert response.agent == "developer"
    assert "git_provider" in response.payload


def test_default_fallback():
    orchestrator = AIOperatingSystem()
    response = orchestrator.handle_text("What's the weather?")
    assert response.agent in {"system", "orchestrator"}
