# MaxOS Test Suite

This directory contains the comprehensive test suite for MaxOS.

## 📁 Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── MOCKING_GUIDE.md         # Comprehensive guide for mocking external APIs
├── integration/             # Integration tests (require real API keys)
│   ├── README.md
│   ├── test_anthropic_integration.py
│   ├── test_gemini_integration.py
│   └── test_openai_integration.py
└── test_*.py                # Unit tests (fully mocked, no network)
```

## 🚀 Running Tests

### Run all unit tests (default, no network required)
```bash
pytest tests/
```

### Run tests excluding integration tests (CI default)
```bash
pytest tests/ -m "not integration"
```

### Run with coverage
```bash
pytest tests/ --cov=max_os --cov-report=term --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_orchestrator.py -v
```

### Run specific test
```bash
pytest tests/test_orchestrator.py::test_filesystem_routing -v
```

### Run integration tests (requires API keys)
```bash
# Set API keys first
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"

# Run integration tests
pytest tests/integration/ -v
```

## 🧪 Test Types

### Unit Tests (`tests/test_*.py`)
- **No network access required**
- **No API keys required**
- **Fast execution** (< 10 seconds total)
- **Fully mocked** external dependencies
- **Run in CI/CD** on every commit

All external API clients (Anthropic, OpenAI, Google) are mocked using pytest fixtures.

### Integration Tests (`tests/integration/`)
- **Require network access**
- **Require valid API keys**
- **May incur costs**
- **Skipped in CI/CD** by default
- **Run manually** for end-to-end validation

## 🔒 API Mocking

All unit tests automatically mock API keys via the `mock_api_keys` fixture in `conftest.py`. This prevents:
- ❌ Accidental real API calls
- ❌ Firewall blocks in CI/CD
- ❌ Wasted API credits
- ❌ Flaky tests dependent on network

See [MOCKING_GUIDE.md](./MOCKING_GUIDE.md) for detailed mocking patterns.

## 📊 Coverage

Generate coverage reports:

```bash
# Terminal report
pytest tests/ --cov=max_os --cov-report=term -m "not integration"

# HTML report
pytest tests/ --cov=max_os --cov-report=html -m "not integration"
open htmlcov/index.html

# XML report (for CI)
pytest tests/ --cov=max_os --cov-report=xml -m "not integration"
```

## ✅ Writing New Tests

1. **Read the mocking guide**: [MOCKING_GUIDE.md](./MOCKING_GUIDE.md)
2. **Use existing fixtures**: Check `conftest.py`
3. **Mock external APIs**: Use provided fixtures or create new ones
4. **Follow patterns**: See existing tests for examples
5. **Test isolation**: Each test should be independent

### Quick checklist:
- [ ] Test file named `test_*.py`
- [ ] Imports mocked (no real API calls)
- [ ] Async tests use `@pytest.mark.asyncio`
- [ ] External dependencies mocked
- [ ] Test is isolated (no shared state)
- [ ] Fast execution (< 1 second per test)

## 🏗️ Test Infrastructure

### Fixtures (`conftest.py`)
- `mock_api_keys` - Auto-mocks all API keys (autouse)
- `mock_anthropic_client` - Mocked Anthropic client
- `mock_openai_client` - Mocked OpenAI client
- `mock_gemini_client` - Mocked Google Gemini client
- `mock_llm_client` - Mocked LLMClient

### Markers (`pyproject.toml`)
- `@pytest.mark.integration` - Integration tests (skipped in CI)
- `@pytest.mark.slow` - Slow tests (can be deselected)

## 🐛 Debugging Tests

### View detailed output
```bash
pytest tests/ -v -s
```

### Show print statements
```bash
pytest tests/ -v -s --capture=no
```

### Stop on first failure
```bash
pytest tests/ -x
```

### Debug with pdb
```bash
pytest tests/ --pdb
```

### Collect tests without running
```bash
pytest tests/ --collect-only
```

## 🔧 Common Issues

### Tests making real API calls
**Symptom**: Tests fail with network errors or "API key required"  
**Solution**: Ensure API clients are mocked. See [MOCKING_GUIDE.md](./MOCKING_GUIDE.md)

### Async tests not running
**Symptom**: `RuntimeWarning: coroutine 'test_xyz' was never awaited`  
**Solution**: Add `@pytest.mark.asyncio` decorator

### Mocks not working
**Symptom**: Mock not being called or returning None  
**Solution**: Mock at import location, not definition. See [MOCKING_GUIDE.md](./MOCKING_GUIDE.md)

### Slow tests
**Symptom**: Tests take > 30 seconds  
**Solution**: Check for unmocked API calls or missing `AsyncMock`

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [MaxOS Mocking Guide](./MOCKING_GUIDE.md)

## 🎯 CI/CD

Tests run automatically in GitHub Actions:

```yaml
# Unit tests (no network, no API keys)
pytest --cov=max_os --cov-report=xml -m "not integration"
```

Integration tests are **skipped** in CI/CD to prevent:
- Firewall blocks (e.g., `api.anthropic.com`)
- API quota exhaustion
- Flaky network-dependent tests
- Wasted API credits

## 📝 Notes

- All unit tests must pass without network access
- Integration tests are for manual validation only
- Mock all external dependencies
- Keep tests fast and isolated
- Follow the mocking guide for consistency
