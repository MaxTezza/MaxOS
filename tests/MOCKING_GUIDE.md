# Test Mocking Guide

This document explains how to properly mock external API calls in MaxOS tests.

## 🎯 Overview

All unit tests **MUST** mock external API calls to:
- ✅ Run without network access
- ✅ Run without API keys
- ✅ Execute quickly (< 5 seconds total)
- ✅ Avoid firewall blocks in CI/CD
- ✅ Prevent wasted API credits

## 🧪 Available Fixtures

The `tests/conftest.py` provides these fixtures:

### `mock_api_keys` (autouse)
Automatically sets fake API keys for all tests to prevent accidental real API calls.

```python
# This happens automatically for ALL tests
# No need to explicitly use this fixture
```

### `mock_anthropic_client`
Mock Anthropic/Claude client with pre-configured responses.

```python
from unittest.mock import patch

def test_with_anthropic(mock_anthropic_client):
    with patch('anthropic.Anthropic', return_value=mock_anthropic_client):
        # Your test code that uses Anthropic
        pass
```

### `mock_openai_client`
Mock OpenAI client with pre-configured responses.

```python
from unittest.mock import patch

def test_with_openai(mock_openai_client):
    with patch('openai.OpenAI', return_value=mock_openai_client):
        # Your test code that uses OpenAI
        pass
```

### `mock_gemini_client`
Mock Google Gemini client with pre-configured responses.

```python
from unittest.mock import patch

@pytest.mark.asyncio
async def test_with_gemini(mock_gemini_client):
    with patch('google.generativeai.GenerativeModel', return_value=mock_gemini_client):
        # Your async test code that uses Gemini
        pass
```

### `mock_llm_client`
Mock LLMClient that returns stub responses.

```python
def test_with_llm_client(mock_llm_client):
    # Pass mock_llm_client to your code via dependency injection
    classifier = IntentClassifier(llm_client=mock_llm_client, ...)
```

## 📝 Mocking Patterns

### Pattern 1: Mock at Import Location

Mock where the client is **imported**, not where it's **defined**.

```python
# ✅ CORRECT - Mock at import location
@patch('max_os.core.orchestrator.Anthropic')
def test_orchestrator(mock_anthropic):
    mock_anthropic.return_value.messages.create.return_value = Mock(
        content=[Mock(text="response")]
    )
    orchestrator = Orchestrator()
    result = orchestrator.process("test")

# ❌ WRONG - Mocking at definition location
@patch('anthropic.Anthropic')  # This won't work!
def test_orchestrator(mock_anthropic):
    pass
```

### Pattern 2: Dependency Injection (Preferred)

Pass mocks via constructor arguments when possible.

```python
@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.generate_async = AsyncMock(return_value="response")
    return mock

@pytest.mark.asyncio
async def test_classifier(mock_llm):
    # ✅ Inject the mock
    classifier = IntentClassifier(llm_client=mock_llm, ...)
    result = await classifier.classify("test")
    assert result is not None
```

### Pattern 3: Mock Async Methods

Use `AsyncMock` for async methods.

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_function():
    mock_client = Mock()
    # ✅ Use AsyncMock for async methods
    mock_client.generate_content_async = AsyncMock(
        return_value=Mock(text="response")
    )
    
    result = await mock_client.generate_content_async("prompt")
    assert result.text == "response"
```

### Pattern 4: Mock Multiple Clients

Patch multiple APIs in the same test.

```python
@patch('max_os.core.llm.genai')
@patch('max_os.core.llm.Anthropic')
def test_multi_provider(mock_anthropic, mock_genai):
    # Setup mocks
    mock_anthropic.return_value.messages.create.return_value = Mock(
        content=[Mock(text="anthropic response")]
    )
    
    mock_model = Mock()
    mock_model.generate_content.return_value = Mock(text="gemini response")
    mock_genai.GenerativeModel.return_value = mock_model
    
    # Your test code
```

### Pattern 5: Mock Environment Variables

Mock API keys or environment variables.

```python
from unittest.mock import patch

@patch.dict(os.environ, {
    "ANTHROPIC_API_KEY": "test-key",
    "GOOGLE_API_KEY": "test-key"
})
def test_with_env_vars():
    # Test code that reads environment variables
    pass
```

## 🚫 Anti-Patterns (Don't Do This)

### ❌ Making Real API Calls in Unit Tests
```python
# DON'T DO THIS
def test_bad():
    from anthropic import Anthropic
    client = Anthropic()  # Real API call!
    response = client.messages.create(...)  # Costs money and fails in CI!
```

### ❌ Requiring Real API Keys
```python
# DON'T DO THIS
def test_bad():
    api_key = os.getenv("ANTHROPIC_API_KEY")  # Fails if not set
    if not api_key:
        pytest.skip("API key required")  # Tests should not skip!
```

### ❌ Using Sleep for Async
```python
# DON'T DO THIS
async def test_bad():
    result = start_async_task()
    await asyncio.sleep(5)  # Slow and unreliable!
    assert result.is_done()
```

### ❌ Not Mocking at Import Location
```python
# DON'T DO THIS
@patch('anthropic.Anthropic')  # Wrong location!
def test_bad(mock):
    # If code imports it as: from anthropic import Anthropic
    # This mock won't work!
```

## 🔍 Integration Tests

For tests that **must** call real APIs:

1. Place them in `tests/integration/`
2. Mark with `@pytest.mark.integration`
3. Add `@pytest.mark.skipif(not os.getenv("API_KEY"), ...)`

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="API key required")
def test_real_anthropic():
    """This test makes real API calls."""
    from anthropic import Anthropic
    client = Anthropic()  # Real client
    # ... test code ...
```

Run integration tests separately:
```bash
# Skip integration tests (default in CI)
pytest -m "not integration"

# Run only integration tests
pytest tests/integration/
```

## ✅ Checklist for New Tests

Before adding a test:

- [ ] Does it import `anthropic`, `openai`, or `google.generativeai`? → Mock them
- [ ] Does it create API clients? → Use dependency injection or mocking
- [ ] Does it make network calls? → Mock the network layer
- [ ] Does it require API keys? → Use `mock_api_keys` fixture (automatic)
- [ ] Is it an async test? → Use `AsyncMock` and `@pytest.mark.asyncio`
- [ ] Should it call real APIs? → Move to `tests/integration/` and mark it

## 📚 Examples

See these files for good mocking examples:
- `tests/test_multi_agent_orchestrator.py` - Comprehensive mocking
- `tests/test_intent_classifier.py` - Dependency injection pattern
- `tests/test_multi_agent_integration.py` - Multiple mock patterns
- `tests/conftest.py` - Reusable fixtures

## 🛠️ Debugging

### Test is making real API calls
```bash
# Run tests with network disabled to verify mocking
python -m pytest tests/ -v --tb=short

# Check for unmocked imports
grep -r "import anthropic\|import openai" tests/ --include="*.py"
```

### Mock not working
1. Verify you're mocking at the **import location** (not definition)
2. Check the patch path matches where the code imports it
3. Ensure the mock is set up before the code runs
4. Use `mock.assert_called()` to verify mocks are being used

### Async mock issues
1. Use `AsyncMock` for async methods
2. Add `@pytest.mark.asyncio` to async tests
3. Ensure `pytest-asyncio` is installed
