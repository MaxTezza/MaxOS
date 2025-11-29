import asyncio
from collections import Counter, deque
from statistics import mean

import structlog
from sklearn.ensemble import IsolationForest

from max_os.agents.base import BaseAgent  # Import BaseAgent for type hinting
from max_os.learning.personality import Interaction, UserPersonalityModel


class RealTimeLearningEngine:
    """
    Processes user interactions in real-time to update the UserPersonalityModel.
    """

    def __init__(
        self,
        personality_model: UserPersonalityModel,
        agent_evolver: BaseAgent | None = None,
        observation_interval: float = 5.0,
        batch_size: int = 10,
        max_queue: int = 100,
    ):
        self.personality_model = personality_model
        self.agent_evolver = agent_evolver
        self.logger = structlog.get_logger("max_os.learning.realtime")
        self._running = False
        self._queue: deque[Interaction] = deque()
        self.max_queue = max_queue  # Max interactions to hold in memory
        self.batch_size = batch_size  # How many interactions to process at once
        self.observation_interval = observation_interval  # seconds between batch processing
        self._recent_metrics: deque[dict[str, float]] = deque(maxlen=5) # Store last 5 batch metrics
        self.anomaly_threshold = 0.5 # If success rate drops below this, log a warning
        self.anomaly_detector = IsolationForest(random_state=42)
        self.anomaly_detector_trained = False

    def observe_interaction(self, interaction: Interaction) -> None:
        """Adds an interaction to the observation queue, dropping the oldest if full."""
        if len(self._queue) >= self.max_queue:
            dropped = self._queue.popleft()
            self.logger.debug(
                "Dropped oldest interaction due to queue limits",
                extra={"dropped_agent": dropped.agent, "timestamp": dropped.timestamp.isoformat()},
            )
        self._queue.append(interaction)

    def get_recent_metrics(self) -> list[dict[str, float]]:
        """Expose recent batch analytics for debugging or UI."""
        return list(self._recent_metrics)

    async def run(self) -> None:
        """Main loop that periodically processes queued interactions in batches."""
        if self._running:
            return
        self._running = True
        try:
            while True:
                batch = self._drain_batch()
                if batch:
                    metrics = self._process_batch(batch)
                    self._recent_metrics.append(metrics)
                    self._check_for_anomalies(metrics)
                await asyncio.sleep(self.observation_interval)
        finally:
            self._running = False

    def _drain_batch(self) -> list[Interaction]:
        batch: list[Interaction] = []
        while self._queue and len(batch) < self.batch_size:
            batch.append(self._queue.popleft())
        return batch

    def _process_batch(self, batch: list[Interaction]) -> dict[str, float]:
        """Feed interactions into the personality model and compute simple metrics."""
        for interaction in batch:
            self.personality_model.observe(interaction)

        success_rate = sum(1 for i in batch if i.success) / len(batch)
        avg_length = mean(i.response_length for i in batch)
        avg_complexity = mean(i.technical_complexity for i in batch)

        domain_counts = Counter(
            interaction.context.get("domain", "unknown") for interaction in batch
        )
        top_domain, top_domain_count = domain_counts.most_common(1)[0]

        metrics = {
            "batch_size": len(batch),
            "success_rate": success_rate,
            "avg_response_length": avg_length,
            "avg_technical_complexity": avg_complexity,
            "top_domain": top_domain,
            "top_domain_ratio": top_domain_count / len(batch),
        }
        self.logger.debug("Processed learning batch", extra=metrics)

        # Prepare data for anomaly detection
        metric_values = [
            metrics["success_rate"],
            metrics["avg_response_length"],
            metrics["avg_technical_complexity"],
            metrics["top_domain_ratio"],
        ]
        # IsolationForest expects a 2D array
        metric_values_2d = [metric_values]

        # Train/update anomaly detector
        if not self.anomaly_detector_trained:
            # Initial training with a small, arbitrary dataset if no data yet
            # In a real scenario, you'd accumulate more data before initial fit
            if len(self._recent_metrics) >= 2: # Need at least 2 samples to fit
                training_data = [
                    [m["success_rate"], m["avg_response_length"], m["avg_technical_complexity"], m["top_domain_ratio"]]
                    for m in self._recent_metrics
                ]
                self.anomaly_detector.fit(training_data)
                self.anomaly_detector_trained = True
        else:
            # Partial fit or re-fit with new data (IsolationForest doesn't have partial_fit)
            # For simplicity, we'll refit with recent metrics + current batch
            all_recent_data = [
                [m["success_rate"], m["avg_response_length"], m["avg_technical_complexity"], m["top_domain_ratio"]]
                for m in self._recent_metrics
            ] + metric_values_2d
            if len(all_recent_data) > 1:
                self.anomaly_detector.fit(all_recent_data)

        return metrics

    def _check_for_anomalies(self, metrics: dict[str, float]) -> None:
        """Log warnings when a batch looks problematic (low success, single-domain spam)."""
        # Existing heuristic-based anomaly detection
        if metrics["success_rate"] < self.anomaly_threshold:
            self.logger.warning(
                "Low success rate detected in learning batch (heuristic)",
                extra=metrics,
            )
        if metrics["top_domain_ratio"] > 0.9 and metrics["batch_size"] >= self.batch_size:
            self.logger.info(
                "Detected sustained focus on single domain (heuristic)",
                extra=metrics,
            )
        
        # ML-based anomaly detection
        if self.anomaly_detector_trained:
            metric_values = [
                metrics["success_rate"],
                metrics["avg_response_length"],
                metrics["avg_technical_complexity"],
                metrics["top_domain_ratio"],
            ]
            score = self.anomaly_detector.decision_function([metric_values])
            if score < 0: # Negative score indicates an anomaly
                self.logger.warning(
                    "Anomaly detected in learning batch (IsolationForest)",
                    extra={**metrics, "anomaly_score": score[0]},
                )
                if self.agent_evolver:
                    # Trigger AgentEvolver for anomaly investigation/policy update
                    # For now, a simple log, but this would be a call to agent_evolver.handle_anomaly()
                    self.logger.info(
                        "Triggering AgentEvolver due to anomaly detection",
                        extra={**metrics, "anomaly_score": score[0]},
                    )
                    # In a real scenario, you'd create an AgentRequest for the AgentEvolver
                    # await self.agent_evolver.handle_anomaly(metrics) # Assuming such a method exists
