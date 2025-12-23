"""Test script to verify token configuration is working."""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from max_os.utils.analytics import get_ga_client
from max_os.utils.config import load_settings


def test_env_loading():
    """Test that .env file is loaded."""
    print("Testing .env file loading...")

    # Check if python-dotenv loaded the .env file
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    ga_measurement_id = os.environ.get("GA_MEASUREMENT_ID")
    ga_api_secret = os.environ.get("GA_API_SECRET")

    print(f"  ANTHROPIC_API_KEY: {'✓ Set' if anthropic_key else '✗ Not set'}")
    print(f"  OPENAI_API_KEY: {'✓ Set' if openai_key else '✗ Not set'}")
    print(f"  GA_MEASUREMENT_ID: {'✓ Set' if ga_measurement_id else '✗ Not set'}")
    print(f"  GA_API_SECRET: {'✓ Set' if ga_api_secret else '✗ Not set'}")
    print()


def test_settings_loading():
    """Test that settings.yaml is loaded correctly."""
    print("Testing settings.yaml loading...")

    try:
        settings = load_settings()
        print(f"  Orchestrator provider: {settings.orchestrator.get('provider', 'Not set')}")
        print(f"  Orchestrator model: {settings.orchestrator.get('model', 'Not set')}")
        print(
            f"  LLM Anthropic key (from config): {'✓ Set' if settings.llm.get('anthropic_api_key') else '✗ Not set'}"
        )
        print(
            f"  LLM OpenAI key (from config): {'✓ Set' if settings.llm.get('openai_api_key') else '✗ Not set'}"
        )
        print(f"  Telemetry enabled: {settings.telemetry.get('enabled', False)}")

        ga_config = settings.telemetry.get("google_analytics", {})
        if ga_config:
            print(
                f"  GA Measurement ID (from config): {ga_config.get('measurement_id', 'Not set')}"
            )
            print(
                f"  GA API Secret (from config): {'✓ Set' if ga_config.get('api_secret') else '✗ Not set'}"
            )
        else:
            print("  Google Analytics: Not configured in settings.yaml")

        print()
        return settings
    except Exception as e:
        print(f"  ✗ Error loading settings: {e}")
        print()
        return None


def test_ga_client(settings):
    """Test Google Analytics client initialization."""
    print("Testing Google Analytics client...")

    try:
        ga_client = get_ga_client(settings.telemetry if settings else None)
        print(f"  GA Client enabled: {ga_client.enabled}")
        print(f"  GA Measurement ID: {ga_client.measurement_id or 'Not set'}")
        print(f"  GA API Secret: {'✓ Set' if ga_client.api_secret else '✗ Not set'}")
        print()
    except Exception as e:
        print(f"  ✗ Error initializing GA client: {e}")
        print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("MaxOS Token Configuration Test")
    print("=" * 60)
    print()

    test_env_loading()
    settings = test_settings_loading()
    test_ga_client(settings)

    print("=" * 60)
    print("Test complete!")
    print()
    print("Next steps:")
    print("1. Copy .env.example to .env and fill in your API keys")
    print("2. Copy config/settings.example.yaml to config/settings.yaml")
    print("3. Run this test again to verify configuration")
    print("4. See docs/TOKEN_SETUP.md for detailed setup instructions")
    print("=" * 60)


if __name__ == "__main__":
    main()
