#!/usr/bin/env python3
"""Test runner script for the HIPAA-compliant database infrastructure."""

import os
import subprocess
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def run_tests():
    """Run the test suite with appropriate configuration."""

    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ASYNC_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    # Test command with coverage and verbose output
    test_cmd = [
        "python3",
        "-m",
        "pytest",
        "tests/",
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings",  # Disable warnings for cleaner output
        "--cov=models",  # Coverage for models
        "--cov=database",  # Coverage for database module
        "--cov=services",  # Coverage for services
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov",  # HTML coverage report
    ]

    print("Running HIPAA-compliant database tests...")
    print(f"Command: {' '.join(test_cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(test_cmd, cwd=backend_dir, check=False)

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ All tests passed successfully!")
            print("📊 Coverage report generated in htmlcov/")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ Some tests failed. Check the output above.")
            print("=" * 60)

        return result.returncode

    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install it:")
        print("   pip install pytest pytest-cov pytest-asyncio")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def run_specific_test(test_name):
    """Run a specific test or test class."""

    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["ASYNC_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    test_cmd = [
        "python3",
        "-m",
        "pytest",
        f"tests/{test_name}",
        "-v",
        "--tb=short",
    ]

    print(f"Running specific test: {test_name}")
    print(f"Command: {' '.join(test_cmd)}")
    print("-" * 60)

    try:
        result = subprocess.run(test_cmd, cwd=backend_dir, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        exit_code = run_specific_test(test_name)
    else:
        # Run all tests
        exit_code = run_tests()

    sys.exit(exit_code)
