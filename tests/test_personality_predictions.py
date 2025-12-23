import pytest

from max_os.learning.personality import UserPersonalityModel


@pytest.fixture()
def personality(tmp_path):
    db = tmp_path / "personality.db"
    model = UserPersonalityModel(db_path=db)
    # Ensure clean slate for deterministic predictions
    model.temporal_patterns = {}
    model.sequential_patterns = []
    model.confidence_threshold = 0.6
    return model


def test_predicts_commit_and_push_from_git_signals(personality):
    context = {
        "signals": {
            "git": {
                "dirty_count": 2,
                "repos": [
                    {
                        "path": "/home/user/repo1",
                        "staged": ["file1.py"],
                        "modified": [],
                        "untracked": [],
                    },
                    {
                        "path": "/home/user/repo2",
                        "staged": [],
                        "modified": ["main.py"],
                        "untracked": [],
                    },
                ],
            }
        }
    }

    tasks = {prediction["task"] for prediction in personality.predict_next_need(context)}
    assert "commit changes" in tasks
    assert "push commits" in tasks


def test_predicts_system_health_on_high_cpu(personality):
    context = {
        "signals": {
            "system": {
                "cpu": {"percent": 92},
                "memory": {"percent": 70},
            }
        }
    }

    predictions = personality.predict_next_need(context)
    assert any(p["task"] == "show system health" for p in predictions)
