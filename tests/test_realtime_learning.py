from datetime import UTC, datetime

import pytest

from max_os.learning.personality import Interaction
from max_os.learning.realtime_engine import RealTimeLearningEngine


class StubPersonality:
    def __init__(self):
        self.observed = []

    def observe(self, interaction: Interaction):
        self.observed.append(interaction)


@pytest.fixture()
def sample_interaction():
    return Interaction(
        timestamp=datetime.now(UTC),
        user_input="test command",
        agent="system",
        response_length=42,
        technical_complexity=0.5,
        success=True,
        context={"domain": "system"},
    )


@pytest.mark.asyncio
async def test_realtime_engine_processes_batches(sample_interaction):
    personality = StubPersonality()
    engine = RealTimeLearningEngine(
        personality, observation_interval=0.01, batch_size=2, max_queue=5
    )

    engine.observe_interaction(sample_interaction)
    engine.observe_interaction(sample_interaction)

    async def run_once():
        batch = engine._drain_batch()
        metrics = engine._process_batch(batch)
        return metrics

    metrics = await run_once()
    assert len(personality.observed) == 2
    assert metrics["batch_size"] == 2
    assert metrics["success_rate"] == 1.0


def test_queue_drops_old_entries(sample_interaction):
    personality = StubPersonality()
    engine = RealTimeLearningEngine(personality, observation_interval=1, batch_size=1, max_queue=3)

    for _ in range(5):
        engine.observe_interaction(sample_interaction)

    assert len(engine._queue) == 3
