from datetime import datetime, timedelta
from pathlib import Path

from max_os.learning.personality import Interaction, UserPersonalityModel


def create_model(tmp_path: Path) -> UserPersonalityModel:
    db_path = tmp_path / "personality.db"
    return UserPersonalityModel(db_path=db_path)


def test_observe_updates_verbosity_and_technical_level(tmp_path: Path):
    model = create_model(tmp_path)
    initial_verbosity = model.verbosity_preference
    initial_technical = model.technical_level

    interaction = Interaction(
        timestamp=datetime.now(),
        user_input="please explain how this works",
        agent="system",
        response_length=800,
        technical_complexity=0.9,
        success=True,
        context={},
        user_reaction="positive",
    )

    model.observe(interaction)

    assert model.verbosity_preference > initial_verbosity
    assert model.technical_level > initial_technical


def test_observe_json_flag_pushes_toward_terse(tmp_path: Path):
    model = create_model(tmp_path)
    model.verbosity_preference = 0.6

    interaction = Interaction(
        timestamp=datetime.now(),
        user_input="show system health --json",
        agent="system",
        response_length=100,
        technical_complexity=0.4,
        success=True,
        context={},
        user_reaction=None,
    )

    model.observe(interaction)

    # JSON flag should push preference downward or at least not increase it
    assert model.verbosity_preference <= 0.6


def test_expertise_updates_on_success_and_failure(tmp_path: Path):
    model = create_model(tmp_path)
    initial_programming = model.skill_levels["programming"]

    success_interaction = Interaction(
        timestamp=datetime.now(),
        user_input="run tests",
        agent="developer",
        response_length=200,
        technical_complexity=0.7,
        success=True,
        context={"domain": "programming"},
        user_reaction=None,
    )
    model.observe(success_interaction)
    after_success = model.skill_levels["programming"]
    assert after_success > initial_programming

    failure_interaction = Interaction(
        timestamp=datetime.now(),
        user_input="run tests",
        agent="developer",
        response_length=200,
        technical_complexity=0.7,
        success=False,
        context={"domain": "programming"},
        user_reaction=None,
    )
    model.observe(failure_interaction)
    after_failure = model.skill_levels["programming"]
    assert after_failure < after_success


def test_predict_next_need_uses_context_and_threshold(tmp_path: Path):
    model = create_model(tmp_path)
    model.confidence_threshold = 0.5

    # Seed a context-based prediction
    context = {"git_status": "modified"}
    predictions = model.predict_next_need(context)

    assert any(p["task"] == "commit changes" for p in predictions)
