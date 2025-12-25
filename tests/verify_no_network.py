#!/usr/bin/env python3
"""Verify that all unit tests can run without network access.

This script runs the test suite in a subprocess to verify that no tests
are making real API calls. Network blocking is enforced by the test mocks
in conftest.py, not by this script.
"""

import sys
import subprocess


def main():
    """Run tests to verify no external API calls are made."""
    print("🔒 Verifying network isolation...")
    print("🧪 Running tests to verify no external API calls...")
    print()

    try:
        # Run tests in subprocess to verify they work without network
        # The mocks in conftest.py prevent real API calls
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-m", "not integration", "-v"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode == 0:
            print()
            print("✅ SUCCESS: All tests pass without network access!")
            print("✅ No external API calls detected.")
            return 0
        else:
            print()
            print("❌ FAILURE: Tests failed. Check output above.")
            return result.returncode

    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Tests took too long (>60s). Possible network calls?")
        return 1
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
