"""User personality model that learns preferences and communication style."""
from __future__ import annotations

import json
import sqlite3  # Added for database operations
from dataclasses import dataclass  # Import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog


@dataclass
class Interaction:
    timestamp: datetime
    user_input: str
    agent: str
    response_length: int
    technical_complexity: float
    success: bool
    context: dict[str, Any]
    user_reaction: str | None = None  # e.g., "positive", "negative", "neutral"


class UserPersonalityModel:
    """
    Models the user's personality, preferences, and predicts next needs.
    """

    def __init__(self, db_path: Path | None = None):
        self.interaction_history: list[Interaction] = []
        self.verbosity_preference: float = 0.5  # 0.0 (terse) to 1.0 (verbose)
        self.technical_level: float = 0.5  # 0.0 (novice) to 1.0 (expert)
        self.logger = structlog.get_logger("max_os.learning.personality")

        # Set db_path with default fallback
        if db_path is None:
            self.db_path = Path.home() / ".maxos" / "personality.db"
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Communication style preferences (0.0 - 1.0)
        self.verbosity_preference = 0.5  # 0=terse, 1=verbose
        self.technical_level = 0.5  # 0=simple, 1=expert
        self.formality = 0.5  # 0=casual, 1=formal
        self.emoji_tolerance = 0.0  # User preference for emojis

        # Domain expertise levels (0.0 - 1.0)
        self.skill_levels = {
            'programming': 0.5,
            'devops': 0.5,
            'networking': 0.5,
            'filesystem': 0.5,
            'system_admin': 0.5,
        }

        # Behavioral patterns
        self.temporal_patterns = {}  # {hour: {common_tasks}}
        self.sequential_patterns = []  # [(action1, action2, frequency)]
        self.context_triggers = {}  # {context: likely_next_action}

        # Learning parameters
        self.learning_rate = 0.1  # How fast to adapt (0.0 - 1.0)
        self.confidence_threshold = 0.7  # Minimum confidence for predictions

        # Initialize database
        self._init_db()
        self._load_from_db()

    def _init_db(self) -> None:
        """Initialize SQLite database for persistent storage."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_input TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    response_length INTEGER,
                    technical_complexity REAL,
                    success INTEGER,
                    context TEXT,
                    user_reaction TEXT
                )
            """)

            # Personality state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS personality_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence REAL,
                    occurrences INTEGER,
                    last_seen TEXT
                )
            """)

            conn.commit()

    def _load_from_db(self) -> None:
        """Load personality state from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT key, value FROM personality_state")
                rows = cursor.fetchall()

                for key, value_json in rows:
                    try:
                        value = json.loads(value_json)
                        if key == 'verbosity_preference':
                            self.verbosity_preference = value
                        elif key == 'technical_level':
                            self.technical_level = value
                        elif key == 'formality':
                            self.formality = value
                        elif key == 'emoji_tolerance':
                            self.emoji_tolerance = value
                        elif key == 'skill_levels':
                            self.skill_levels = value
                    except (json.JSONDecodeError, KeyError):
                        # Log but don't crash - just use defaults
                        pass
        except sqlite3.Error:
            # Database error - use defaults
            pass

    def _save_to_db(self) -> None:
        """Persist personality state to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                updates = [
                    ('verbosity_preference', self.verbosity_preference),
                    ('technical_level', self.technical_level),
                    ('formality', self.formality),
                    ('emoji_tolerance', self.emoji_tolerance),
                    ('skill_levels', self.skill_levels),
                ]

                for key, value in updates:
                    cursor.execute("""
                        INSERT OR REPLACE INTO personality_state (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, json.dumps(value), now))

                conn.commit()
        except sqlite3.Error:
            # Database error - silently fail for now
            pass

    def observe(self, interaction: Interaction):
        """Learn from a single interaction."""
        # Store interaction
        self._store_interaction(interaction)

        # Update communication style preferences
        self._update_communication_style(interaction)

        # Update domain expertise
        self._update_expertise(interaction)

        # Detect patterns
        self._detect_patterns()

        # Persist changes
        self._save_to_db()

    def _store_interaction(self, interaction: Interaction) -> None:
        """Store interaction in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO interactions (
                        timestamp, user_input, agent, response_length,
                        technical_complexity, success, context, user_reaction
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interaction.timestamp.isoformat(),
                    interaction.user_input,
                    interaction.agent,
                    interaction.response_length,
                    interaction.technical_complexity,
                    1 if interaction.success else 0,
                    json.dumps(interaction.context),
                    interaction.user_reaction
                ))

                conn.commit()
        except sqlite3.Error:
            # Database error - silently fail for now
            pass

    def _update_communication_style(self, interaction: Interaction) -> None:
        """Update communication style preferences based on interaction."""
        if interaction.user_reaction == 'positive':
            # Reinforce current style
            # If they liked a verbose response, increase verbosity preference
            response_verbosity = min(1.0, interaction.response_length / 500)
            self.verbosity_preference += self.learning_rate * (response_verbosity - self.verbosity_preference)

            # Reinforce technical level
            self.technical_level += self.learning_rate * (interaction.technical_complexity - self.technical_level)

        elif interaction.user_reaction == 'negative':
            # Move away from current style
            response_verbosity = min(1.0, interaction.response_length / 500)
            self.verbosity_preference -= self.learning_rate * (response_verbosity - self.verbosity_preference)

            self.technical_level -= self.learning_rate * (interaction.technical_complexity - self.technical_level)

        # Implicit signals
        # If user used --json flag, they prefer terse output
        if '--json' in interaction.user_input:
            self.verbosity_preference -= self.learning_rate * 0.1

        # If user asks "how" or "why", they want more detail
        if any(word in interaction.user_input.lower() for word in ['how', 'why', 'explain']):
            self.verbosity_preference += self.learning_rate * 0.1

    def _update_expertise(self, interaction: Interaction) -> None:
        """Update domain expertise levels based on interaction success."""
        domain = interaction.context.get('domain')
        if not domain or domain not in self.skill_levels:
            return

        if interaction.success:
            # Successful interaction increases perceived expertise
            self.skill_levels[domain] += self.learning_rate * 0.05
            self.skill_levels[domain] = min(1.0, self.skill_levels[domain])
        else:
            # Failed interaction might indicate lower expertise
            self.skill_levels[domain] -= self.learning_rate * 0.02
            self.skill_levels[domain] = max(0.0, self.skill_levels[domain])

    def _detect_patterns(self) -> None:
        """Detect temporal and sequential patterns from interaction history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Detect temporal patterns (what user does at specific times)
                cursor.execute("""
                    SELECT
                        strftime('%H', timestamp) as hour,
                        user_input,
                        COUNT(*) as frequency
                    FROM interactions
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY hour, user_input
                    HAVING frequency > 3
                    ORDER BY hour, frequency DESC
                """)

                temporal_data = cursor.fetchall()
                self.temporal_patterns = {}
                for hour, task, freq in temporal_data:
                    if hour not in self.temporal_patterns:
                        self.temporal_patterns[hour] = []
                    self.temporal_patterns[hour].append({
                        'task': task,
                        'frequency': freq
                    })

                # Detect sequential patterns (action A followed by action B)
                cursor.execute("""
                    SELECT
                        i1.user_input as action1,
                        i2.user_input as action2,
                        COUNT(*) as frequency
                    FROM interactions i1
                    JOIN interactions i2 ON i2.id = i1.id + 1
                    WHERE i1.timestamp > datetime('now', '-30 days')
                    GROUP BY action1, action2
                    HAVING frequency > 2
                    ORDER BY frequency DESC
                    LIMIT 50
                """)

                self.sequential_patterns = cursor.fetchall()
        except sqlite3.Error:
            # Database error - keep existing patterns
            pass

    def predict_next_need(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """Predict what user will need next based on context and extracted features."""
        predictions: list[dict[str, Any]] = []
        features = self._extract_features(context)

        def add_prediction(task: str, confidence: float, reason: str, ptype: str) -> None:
            if confidence <= self.confidence_threshold:
                return
            entry = {
                'task': task,
                'confidence': round(confidence, 3),
                'reason': reason,
                'type': ptype,
            }
            for idx, existing in enumerate(predictions):
                if existing['task'] == task:
                    if confidence > existing['confidence']:
                        predictions[idx] = entry
                    return
            predictions.append(entry)

        # Time-based predictions
        current_hour = features['hour_of_day']
        if str(current_hour) in self.temporal_patterns:
            for pattern in self.temporal_patterns[str(current_hour)][:3]:  # Top 3
                add_prediction(
                    pattern['task'],
                    min(0.9, pattern['frequency'] / 10),
                    f'You usually do this around {current_hour}:00',
                    'temporal'
                )

        # Sequential predictions (based on last action)
        if features['last_action_is_git_status']:
            # Example: if last action was 'show git status', suggest 'commit changes'
            add_prediction(
                'commit changes',
                0.75,
                'You just checked git status, likely to commit',
                'sequential'
            )
        # Add more sequential predictions based on features['last_action_is_commit'] etc.

        # Context-based predictions using features
        if features['git_dirty_count'] > 0:
            add_prediction(
                'commit changes',
                min(0.9, 0.7 + 0.05 * features['git_dirty_count']),
                f'{features["git_dirty_count"]} repo(s) have uncommitted changes',
                'context'
            )
        if features['git_has_staged']:
            add_prediction(
                'push commits',
                0.82,
                "There are staged changes ready to push",
                'context'
            )

        if features['active_app_is_ide']:
            add_prediction(
                'show git status',
                0.74,
                'Active window looks like a coding session',
                'context'
            )

        if features['recent_python_file_modified']:
            add_prediction(
                'run tests',
                0.78,
                'Recent Python files were modified',
                'context'
            )

        if features['new_downloads_recently']:
            add_prediction(
                'organize downloads',
                0.72,
                'New files landed in Downloads recently',
                'context'
            )

        if features['cpu_percent'] > 80:
            add_prediction(
                'show system health',
                min(0.9, 0.7 + (features['cpu_percent'] - 80) / 100),
                f'CPU load is high at {features["cpu_percent"]:.0f}%',
                'context'
            )
        if features['memory_percent'] > 80:
            add_prediction(
                'show system health',
                min(0.88, 0.68 + (features['memory_percent'] - 80) / 120),
                f'Memory usage is high at {features["memory_percent"]:.0f}%',
                'context'
            )

        # Sort by confidence and return top predictions
        predictions.sort(key=lambda x: x['confidence'], reverse=True)
        self.logger.debug("Generated predictions: %s", predictions)
        return predictions[:5]

    @staticmethod
    def _is_recent_timestamp(timestamp: str | None, minutes: int = 10) -> bool:
        if not timestamp:
            return False
        try:
            normalized = timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return False
        if parsed.tzinfo:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return (datetime.now() - parsed) <= timedelta(minutes=minutes)

    def get_communication_params(self) -> dict[str, float]:
        """Get current communication style parameters."""
        return {
            'verbosity': self.verbosity_preference,
            'technical_level': self.technical_level,
            'formality': self.formality,
            'emoji_tolerance': self.emoji_tolerance,
        }

    def get_expertise_level(self, domain: str) -> float:
        """Get user's expertise level in a specific domain."""
        return self.skill_levels.get(domain, 0.5)

    def export_personality(self) -> dict[str, Any]:
        """Export personality model for inspection or transfer."""
        return {
            'communication_style': self.get_communication_params(),
            'skill_levels': self.skill_levels,
            'temporal_patterns': self.temporal_patterns,
            'sequential_patterns': [
                {'action1': a1, 'action2': a2, 'frequency': f}
                for a1, a2, f in self.sequential_patterns
            ],
            'learning_rate': self.learning_rate,
            'confidence_threshold': self.confidence_threshold,
        }

    def get_recent_interactions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent interaction history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT timestamp, user_input, agent, success, user_reaction
                    FROM interactions
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

                rows = cursor.fetchall()

            return [
                {
                    'timestamp': row[0],
                    'input': row[1],
                    'agent': row[2],
                    'success': bool(row[3]),
                    'reaction': row[4]
                }
                for row in rows
            ]
        except sqlite3.Error:
            # Database error - return empty list
            return []

    def get_score(self) -> float:
        """Returns a simple aggregated score representing the user's overall personality state."""
        # This is a placeholder. A more sophisticated score would involve
        # weighted averages, recent interaction sentiment, etc.
        return (
            self.verbosity_preference
            + self.technical_level
            + self.formality
            + (1 - self.emoji_tolerance) # Lower tolerance means higher score for "seriousness"
        ) / 4.0

    def _extract_features(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Extracts a structured feature vector from the current context and personality state.
        """
        features = {}
        now = datetime.now()

        # Time-based features
        features['hour_of_day'] = now.hour
        features['day_of_week'] = now.weekday() # Monday is 0, Sunday is 6
        features['is_weekend'] = 1 if now.weekday() >= 5 else 0

        # Personality traits
        features['verbosity_preference'] = self.verbosity_preference
        features['technical_level'] = self.technical_level
        features['formality'] = self.formality
        features['emoji_tolerance'] = self.emoji_tolerance

        # Context signals
        signals = context.get('signals', {})

        # Git status
        git_info = signals.get('git', {})
        features['git_dirty_count'] = git_info.get('dirty_count', 0)
        features['git_has_staged'] = 1 if any(repo.get('staged') for repo in git_info.get('repos', [])) else 0

        # Handle simplified git_status context (for tests or simplified usage)
        if 'git_status' in context and context['git_status'] == 'modified':
            features['git_dirty_count'] = max(features['git_dirty_count'], 1)

        # Active application
        active_window = (signals.get('applications', {}).get('active_window') or '').lower()
        features['active_app_is_ide'] = 1 if any(keyword in active_window for keyword in ['code', 'pycharm', 'vim', 'idea', 'studio', 'sublime']) else 0
        features['active_app_is_browser'] = 1 if any(keyword in active_window for keyword in ['chrome', 'firefox', 'edge', 'brave']) else 0

        # Filesystem activity
        filesystem_info = signals.get('filesystem', {})
        features['recent_python_file_modified'] = 1 if any(event.get('src_path', '').endswith('.py') for event in filesystem_info.get('recent_events', [])) else 0
        features['new_downloads_recently'] = 1 if (filesystem_info.get('downloads') and self._is_recent_timestamp(filesystem_info['downloads'][0].get('modified'))) else 0

        # System metrics
        system_metrics = signals.get('system', {})
        features['cpu_percent'] = (system_metrics.get('cpu') or {}).get('percent', 0.0)
        features['memory_percent'] = (system_metrics.get('memory') or {}).get('percent', 0.0)

        # Last action
        features['last_action_is_git_status'] = 1 if context.get('last_action', '').lower() == 'show git status' else 0
        features['last_action_is_commit'] = 1 if 'commit' in context.get('last_action', '').lower() else 0

        return features
