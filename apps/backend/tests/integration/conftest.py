"""Pytest configuration for integration tests."""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for importing main
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
try:
    from main import app
except ImportError:
    # Fallback for test execution
    sys.path.append("/Volumes/external storage /PMS/apps/backend")
    from main import app


@pytest.fixture
def client():
    """Create a test client for integration tests."""
    return TestClient(app)


@pytest.fixture
def mock_all_services_enabled(monkeypatch):
    """Enable all mock services for integration tests."""

    def mock_is_edi_enabled(self):
        return True

    def mock_is_payments_enabled(self):
        return True

    def mock_is_video_enabled(self):
        return True

    monkeypatch.setattr(
        "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled", mock_is_edi_enabled
    )
    monkeypatch.setattr(
        "utils.feature_flags.FeatureFlags." "is_mock_payments_enabled",
        mock_is_payments_enabled,
    )
    monkeypatch.setattr(
        "utils.feature_flags.FeatureFlags." "is_mock_video_enabled",
        mock_is_video_enabled,
    )


@pytest.fixture
def mock_all_services_disabled(monkeypatch):
    """Disable all mock services for integration tests."""

    def mock_is_edi_disabled(self):
        return False

    def mock_is_payments_disabled(self):
        return False

    def mock_is_video_disabled(self):
        return False

    monkeypatch.setattr(
        "utils.feature_flags.FeatureFlags." "is_mock_edi_enabled", mock_is_edi_disabled
    )
    monkeypatch.setattr(
        "utils.feature_flags.FeatureFlags." "is_mock_payments_enabled",
        mock_is_payments_disabled,
    )
    monkeypatch.setattr(
        "utils.feature_flags.FeatureFlags." "is_mock_video_enabled",
        mock_is_video_disabled,
    )
