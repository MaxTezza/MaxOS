"""Integration tests that require real API access.

These tests are skipped by default in CI/CD. To run them:
    pytest tests/integration/ --run-integration

Or to run all tests except integration tests:
    pytest -m "not integration"
"""
