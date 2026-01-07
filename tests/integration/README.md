# Integration Tests

This directory contains integration tests that make **real API calls** to external services.

## ⚠️ Important

- These tests require valid API keys (Anthropic, OpenAI, Google)
- These tests are **skipped by default** in CI/CD
- These tests may incur API costs
- These tests require network access

## Running Integration Tests

### Run integration tests only:
```bash
pytest tests/integration/ -v
```

### Run all tests INCLUDING integration:
```bash
pytest tests/ -v
```

### Run all tests EXCLUDING integration:
```bash
pytest tests/ -m "not integration" -v
```

## API Keys Required

Set these environment variables:
```bash
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
export GOOGLE_API_KEY="your-key-here"
```

## Guidelines

1. Keep integration tests minimal and focused
2. Use small, cheap API calls
3. Add proper error handling
4. Mark all tests with `@pytest.mark.integration`
5. Document what each test validates
