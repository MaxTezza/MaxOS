from pathlib import Path

from max_os.agents.base import AgentResponse
from max_os.learning.personality import UserPersonalityModel
from max_os.learning.prompt_filter import PromptOptimizationFilter


def create_filter(tmp_path: Path) -> PromptOptimizationFilter:
    model = UserPersonalityModel(db_path=tmp_path / "personality.db")
    return PromptOptimizationFilter(model)


def test_optimize_response_terse_removes_fillers(tmp_path: Path):
    prompt_filter = create_filter(tmp_path)
    prompt_filter.upm.verbosity_preference = 0.1

    response = AgentResponse(
        agent="system",
        status="success",
        message="Successfully completed operation and actually retrieved information for test file",
        payload={"summary": "Verbose summary", "value": 42},
    )

    optimized = prompt_filter.optimize_response(response, context={})

    assert "Successfully" not in optimized.message
    assert "actually" not in optimized.message
    assert "summary" not in optimized.payload
    assert optimized.payload["value"] == 42


def test_optimize_response_verbose_adds_context(tmp_path: Path):
    prompt_filter = create_filter(tmp_path)
    prompt_filter.upm.verbosity_preference = 0.9

    response = AgentResponse(
        agent="filesystem",
        status="success",
        message="Found 3 file(s) matching criteria",
        payload={"search_path": "/tmp", "pattern": "*.txt"},
    )

    context = {"domain": "filesystem", "search_path": "/tmp"}
    optimized = prompt_filter.optimize_response(response, context=context)

    assert "(searched in /tmp)" in optimized.message


def test_add_predictive_suggestions_appends_to_message(tmp_path: Path):
    prompt_filter = create_filter(tmp_path)
    prompt_filter.upm.verbosity_preference = 0.6

    base_response = AgentResponse(
        agent="developer",
        status="success",
        message="Git status for repo",
        payload={},
    )

    predictions = [
        {"task": "run tests", "reason": "You usually do this after git status", "confidence": 0.8},
        {"task": "git push", "reason": "You often push after commits", "confidence": 0.9},
    ]

    enhanced = prompt_filter.add_predictive_suggestions(base_response, predictions)

    assert "You might want to:" in enhanced.message
    assert "run tests" in enhanced.message
    assert "git push" in enhanced.message


def test_estimate_technical_complexity_increases_for_technical_terms(tmp_path: Path):
    prompt_filter = create_filter(tmp_path)

    simple = prompt_filter.estimate_technical_complexity("Hello world", domain="general")
    technical = prompt_filter.estimate_technical_complexity(
        "Async daemon uses socket buffer and parsing with def func(): pass",
        domain="programming",
    )

    assert technical > simple
