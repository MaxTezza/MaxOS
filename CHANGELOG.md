# MaxOS Changelog

## [Unreleased] - 2025-11-18

### Fixed
- **Critical: AgentEvolver Integration** - Fixed AgentEvolverAgent to properly handle AgentRequest instead of Intent objects
  - Updated `can_handle()` method to use `request.intent` and `request.text`
  - Updated `handle()` method parameter from `intent` to `request`
  - Fixed agent registration order to prioritize AgentEvolver before SystemAgent
  - Location: `max_os/agents/agent_evolver/__init__.py`

- **Critical: Async/Await in Tests** - Fixed orchestrator tests to properly use async/await
  - Added `@pytest.mark.asyncio` decorators to all test functions
  - Changed test functions to async and added await for `handle_text()` calls
  - Location: `tests/test_orchestrator.py`

- **Critical: LLM API Async Issues** - Fixed synchronous LLM client calls in async context
  - Wrapped Anthropic and OpenAI API calls with `asyncio.to_thread()` to run in thread pool
  - Updated default model to `claude-3-5-sonnet-20241022`
  - Location: `max_os/utils/llm_api.py`

- **Personality Prediction Logic** - Fixed git status prediction for simplified context format
  - Added support for top-level `git_status: "modified"` context field
  - Feature extraction now sets `git_dirty_count` when simplified git_status is present
  - Location: `max_os/learning/personality.py:516-518`

### Added
- **AgentEvolver Agent** - Self-evolving agent management system
  - Task generation from predefined templates
  - Policy refinement for FileSystemAgent and SystemAgent
  - Performance metrics tracking
  - Status reporting with full metrics
  - Location: `max_os/agents/agent_evolver/__init__.py`

- **Knowledge Agent** - RAG (Retrieval-Augmented Generation) capabilities
  - Document retrieval and summarization
  - Question answering with context augmentation
  - Simple keyword-based retrieval mechanism
  - LLM integration for response generation
  - Location: `max_os/agents/knowledge/__init__.py`

- **Context Awareness Engine** - Real-time system signal collection
  - Git repository monitoring with caching
  - Filesystem change tracking with watchdog
  - Process and system metrics collection
  - Network interface and connection monitoring
  - Active window and clipboard detection (X11/Wayland)
  - Location: `max_os/learning/context_engine.py`

- **Predictive Agent Spawner** - Proactive task prediction
  - Continuous prediction loop based on context signals
  - High-confidence threshold filtering (>0.8)
  - Automatic agent spawning for predicted needs
  - Location: `max_os/learning/prediction.py`

- **Real-Time Learning Engine** - Batch interaction processing
  - Interaction queue management with automatic dropping
  - Batch metrics calculation (success rate, complexity, domain analysis)
  - Anomaly detection using IsolationForest ML model
  - Integration with AgentEvolver for anomaly response
  - Location: `max_os/learning/realtime_engine.py`

- **Intent Classifier** - Context-aware intent classification
  - Fallback to existing rule-based planner
  - Support for context-driven intent detection
  - Location: `max_os/core/intent_classifier.py`

- **Agent Registry** - Centralized agent instance management
  - Simple registration and retrieval system
  - Global `AGENT_REGISTRY` singleton
  - Location: `max_os/core/registry.py`

- **REST API** - FastAPI-based HTTP interface
  - `/intent` endpoint for handling user text
  - Integration with orchestrator
  - Location: `max_os/interfaces/api/main.py`

- **Comprehensive Test Suite**
  - Context engine tests (7 tests)
  - Intent classifier tests (3 tests)
  - Personality prediction tests (2 tests)
  - Prediction spawner tests (1 test)
  - Real-time learning tests (2 tests)
  - All tests passing (31/31)

- **Documentation**
  - AgentEvolver integration guide
  - Learning system demonstration
  - Predictive agent architecture

### Changed
- **Agent Registration Order** - Reordered agents for better intent matching
  - AgentEvolverAgent now registered first
  - SystemAgent moved to last position (broad keyword matching)
  - Ensures evolver-specific commands are caught correctly

- **Orchestrator Enhancements**
  - Added learning system integration with personality model
  - Context signal gathering with timeout protection
  - Git status detection and context enrichment
  - Predictive suggestion system
  - Location: `max_os/core/orchestrator.py`

### Technical Details
- All critical bugs identified and fixed
- Zero failing tests (31/31 passing)
- AgentEvolver fully functional with status, task generation, and policy refinement
- Learning system operational with real-time interaction tracking
- Context awareness engine gathering signals from 7 different sources
