# MaxOS Learning System Demo

## What Just Happened

We built a self-learning AI operating system that **learns your personality in real-time** and adapts its communication style to match you.

## The Foundation (Week 1 Complete!)

### ✅ Built Components

1. **UserPersonalityModel** (`max_os/learning/personality.py`)
   - Tracks verbosity, technical level, formality, emoji tolerance
   - Learns domain expertise (programming, devops, networking, etc.)
   - Detects temporal patterns (what you do at specific times)
   - Detects sequential patterns (action A → action B)
   - Stores everything in local SQLite (fully private!)

2. **PromptOptimizationFilter** (`max_os/learning/prompt_filter.py`)
   - Adapts response verbosity based on your preference
   - Adjusts technical complexity to your skill level
   - Makes responses casual or formal based on your style
   - Strips emojis if you don't like them
   - Adds/removes technical details intelligently

3. **Integrated Learning** (into orchestrator)
   - Every interaction is recorded and analyzed
   - Responses are optimized before being shown to you
   - Predictive suggestions added when patterns detected
   - Learning rate of 0.1 (gradual, stable adaptation)

## How It Learns

### Signal Detection

The system learns from:

**Explicit Signals:**
- Using `--json` flag → You prefer terse output
- Asking "how" or "why" → You want detailed explanations
- Asking "explain" → You prefer verbose responses

**Implicit Signals:**
- Success/failure of responses → Updates domain expertise
- Response length preferences → Adjusts verbosity
- Time of day patterns → Predicts routine tasks
- Sequential actions → Predicts next steps

### Example Learning Session

```bash
# Fresh system starts at defaults
verbosity: 0.50, technical_level: 0.50

# User uses --json 5 times
$ python -m max_os.interfaces.cli.main "show system health" --json
# System learns: User prefers terse output
verbosity: 0.45 (shifted down due to --json signal)

# User asks detailed questions
$ python -m max_os.interfaces.cli.main "explain how git branches work"
$ python -m max_os.interfaces.cli.main "why is my memory usage high"
# System learns: User wants explanations
verbosity: 0.60 (shifted up due to explanation requests)

# After 50 interactions about programming
# System learns: User is expert in programming domain
skill_levels['programming']: 0.85
```

## Current Capabilities

### ✅ Working Now

- [x] Real-time personality tracking
- [x] Communication style adaptation
- [x] Domain expertise tracking
- [x] Pattern detection (temporal & sequential)
- [x] Persistent storage (SQLite)
- [x] Privacy-first (all local, no cloud)
- [x] Personality inspection (`--show-personality`)
- [x] Export personality model (`--export-personality`)
- [x] **Context awareness engine** (`max_os/learning/context_engine.py`) hooked into every request. Inspect live signals via `--show-context`.

### 🚧 Coming Next (Week 2)

- [ ] Predictive agent spawning
- [ ] Proactive suggestions based on patterns
- [ ] Auto-execution of high-confidence predictions

## Context Awareness Engine (NEW)

`max_os/learning/context_engine.py` now gathers system, process, git, filesystem, time, network, and application signals in parallel. The orchestrator automatically injects this into each interaction so predictions get fresh state.

**Try it out:**

```bash
python -m max_os.interfaces.cli.main "show system health" --json --show-context
```

The `--show-context` flag prints the captured signals so you can watch git status, recent downloads, active window, etc., in real time.

## CLI Commands

```bash
# Normal usage (learning happens automatically)
python -m max_os.interfaces.cli.main "show system health"

# View your learned personality
python -m max_os.interfaces.cli.main --show-personality

# Export personality model
python -m max_os.interfaces.cli.main --export-personality ~/my_personality.json

# The system learns from every interaction!
```

## Personality Model Structure

```json
{
  "communication_style": {
    "verbosity": 0.59,
    "technical_level": 0.50,
    "formality": 0.50,
    "emoji_tolerance": 0.00
  },
  "skill_levels": {
    "programming": 0.50,
    "devops": 0.50,
    "networking": 0.50,
    "filesystem": 0.50,
    "system_admin": 0.50
  },
  "temporal_patterns": {
    "09": [
      {"task": "show system health", "frequency": 5}
    ]
  },
  "sequential_patterns": [
    {"action1": "git status", "action2": "git commit", "frequency": 8}
  ]
}
```

## What Makes This Powerful

### 1. Learning Rate
- Set to 0.1 (conservative)
- Means it takes ~10 signals to significantly shift preferences
- Prevents wild swings from one-off actions
- Gradual, stable learning over time

### 2. Multi-Signal Learning
- Explicit: flags, keywords
- Implicit: success rates, response preferences
- Temporal: time-of-day patterns
- Sequential: action→action patterns

### 3. Privacy First
- All data stored locally in `~/.maxos/personality.db`
- No telemetry, no cloud sync
- You can inspect/modify/delete anytime
- Export as JSON for full transparency

## Next Steps: The Vision

### Week 2: Context Awareness
```python
class ContextAwarenessEngine:
    """Monitors everything to predict needs."""

    async def gather_signals(self):
        return {
            'git_status': 'modified',
            'time': '09:00',
            'last_action': 'git add',
            'open_files': ['laser_project.py'],
            'system_health': 'good',
        }
```

### Week 3: Predictive Spawning
```python
# System detects pattern: Every weekday at 9am you check system health
# So at 8:59am...
agent_spawner.spawn({
    'task': 'system_health',
    'confidence': 0.95,
    'reason': 'User checks health every weekday morning'
})

# At 9:00am when you sit down:
"Good morning! System healthy: CPU 15%, Memory 42%, All services running ✓"
# You didn't ask - it predicted!
```

### Week 4: The Magic
```
[You: "git status"]
System: 5 modified files
Pattern detected: After checking status, you commit 90% of the time
Prediction: You'll commit next

[System prepares specialist agent, drafts commit message]

[You: "git commit"]
System: "Here's your commit message based on changes:
        'Add laser control interface and update calibration parameters'

        Sound good? (y/n)"

[You didn't have to write the message - it predicted and prepared it]
```

## Current Test Results

```
Initial state:
  verbosity: 0.50

After 5x --json:
  verbosity: 0.45 ← Learned you prefer terse

After 3x "explain/why/how":
  verbosity: 0.60 ← Learned you want details

After 20x successful git commands:
  skill_levels['programming']: 0.60 ← Recognized expertise
```

## Files

- `max_os/learning/personality.py` - Core personality model
- `max_os/learning/prompt_filter.py` - Response optimization
- `max_os/core/orchestrator.py` - Learning integration
- `~/.maxos/personality.db` - Your learned personality (SQLite)

## Try It Now!

```bash
cd ~/ai-os
source .venv/bin/activate

# Use MaxOS naturally
python -m max_os.interfaces.cli.main "show git status"
python -m max_os.interfaces.cli.main "list files in Downloads"
python -m max_os.interfaces.cli.main "ping google.com"

# Check what it learned about you
python -m max_os.interfaces.cli.main --show-personality

# The more you use it, the better it gets at being YOU!
```

---

Last Updated: 2025-11-15
Status: Week 1 Complete ✅
Next: Context Awareness Engine
