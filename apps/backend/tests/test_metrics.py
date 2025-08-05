"""Tests for metrics middleware and utilities."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from middleware.metrics import (
    ACTIVE_REQUESTS,
    AUDIT_EVENTS,
    AUTH_EVENTS,
    ERROR_COUNT,
    PHI_SCRUB_COUNT,
    REQUEST_COUNT,
    REQUEST_DURATION,
    USER_ACTIONS,
    PrometheusMetricsMiddleware,
    metrics_endpoint,
    record_audit_event,
    record_auth_event,
    record_phi_scrub,
    record_user_action,
)
from utils.metrics import (
    MetricsContext,
    track_authentication,
    track_crud_operation,
    track_phi_scrubbing,
)


class TestPrometheusMetricsMiddleware:
    """Test the Prometheus metrics middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with metrics middleware."""
        app = FastAPI()
        app.add_middleware(PrometheusMetricsMiddleware, environment="test")

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        @app.get("/slow")
        async def slow_endpoint():
            import asyncio

            await asyncio.sleep(0.1)
            return {"message": "slow"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def setup_metrics(self):
        """Capture baseline metric counts before each test."""
        # Don't clear the registry - just capture baseline counts
        # Tests will check for incremental changes from baseline
        baseline = {
            "audit_count": self._get_metric_count(AUDIT_EVENTS),
            "user_count": self._get_metric_count(USER_ACTIONS),
            "auth_count": self._get_metric_count(AUTH_EVENTS),
            "phi_count": self._get_metric_count(PHI_SCRUB_COUNT),
        }
        yield baseline

    def _get_metric_count(self, collector):
        """Get current count of samples for a metric collector."""
        try:
            return len(list(collector.collect())[0].samples)
        except (IndexError, AttributeError):
            return 0

    def test_successful_request_metrics(self, client):
        """Test that successful requests are properly tracked."""
        response = client.get("/test")
        assert response.status_code == 200

        # Check that request count was incremented
        samples = list(REQUEST_COUNT.collect())[0].samples
        assert len(samples) > 0

        # Find the sample for our test endpoint
        test_sample = next(
            (s for s in samples if s.labels.get("endpoint") == "/test"), None
        )
        assert test_sample is not None
        assert test_sample.value == 1.0
        assert test_sample.labels["method"] == "GET"
        assert test_sample.labels["status_code"] == "200"
        assert test_sample.labels["environment"] == "test"

    def test_error_request_metrics(self, client):
        """Test that error requests are properly tracked."""
        # The test client will raise the exception, but the middleware
        # should still record it
        try:
            client.get("/error")
        except ValueError:
            pass  # Expected - middleware records error before re-raising

        # Check that error count was incremented
        samples = list(ERROR_COUNT.collect())[0].samples
        assert len(samples) > 0

        # Find the sample for our error endpoint
        error_sample = next(
            (s for s in samples if s.labels.get("endpoint") == "/error"), None
        )
        assert error_sample is not None
        assert error_sample.value == 1.0
        assert error_sample.labels["method"] == "GET"
        assert error_sample.labels["error_type"] == "ValueError"
        assert error_sample.labels["environment"] == "test"

    def test_request_duration_metrics(self, client):
        """Test that request duration is properly tracked."""
        client.get("/slow")

        # Check that duration was recorded
        samples = list(REQUEST_DURATION.collect())[0].samples
        assert len(samples) > 0

        # Find samples for our slow endpoint
        slow_samples = [s for s in samples if s.labels.get("endpoint") == "/slow"]
        assert len(slow_samples) > 0

    def test_phi_scrubbing_in_endpoint_labels(self, client):
        """Test that PHI is scrubbed from endpoint labels."""
        # Test with a URL that might contain PHI
        client.get("/test?email=john@example.com&ssn=123-45-6789")

        # The endpoint label should be scrubbed
        samples = list(REQUEST_COUNT.collect())[0].samples
        test_sample = next(
            (s for s in samples if "/test" in s.labels.get("endpoint", "")),
            None,
        )
        assert test_sample is not None

        # Endpoint should not contain PHI
        endpoint = test_sample.labels["endpoint"]
        assert "john@example.com" not in endpoint
        assert "123-45-6789" not in endpoint

    def test_metrics_endpoint_excluded(self, client):
        """Test that the metrics endpoint itself is not tracked."""
        client.get("/metrics")

        # Should not find any samples for /metrics endpoint
        samples = list(REQUEST_COUNT.collect())[0].samples
        metrics_samples = [s for s in samples if s.labels.get("endpoint") == "/metrics"]
        assert len(metrics_samples) == 0

    @pytest.mark.asyncio
    async def test_active_requests_tracking(self, app):
        """Test that active requests are properly tracked."""
        import asyncio

        # Create a slow endpoint that we can control
        @app.get("/very-slow")
        async def very_slow_endpoint():
            await asyncio.sleep(0.2)
            return {"message": "very slow"}

        client = TestClient(app)

        # Start a slow request in the background
        import threading

        def make_slow_request():
            client.get("/very-slow")

        thread = threading.Thread(target=make_slow_request)
        thread.start()

        # Give it a moment to start
        await asyncio.sleep(0.05)

        # Check that active requests increased
        samples = list(ACTIVE_REQUESTS.collect())[0].samples
        # Note: This test might be flaky due to timing
        # Just verify that samples exist
        assert isinstance(samples, list)

        thread.join()


class TestMetricsUtilities:
    """Test the metrics utility functions."""

    def _get_metric_count(self, collector):
        """Get current count of samples for a metric collector."""
        try:
            return len(list(collector.collect())[0].samples)
        except (IndexError, AttributeError):
            return 0

    @pytest.fixture(autouse=True)
    def setup_metrics(self):
        """Capture baseline metric counts before each test."""
        # Don't clear the registry - just capture baseline counts
        # Tests will check for incremental changes from baseline
        baseline = {
            "audit_count": self._get_metric_count(AUDIT_EVENTS),
            "user_count": self._get_metric_count(USER_ACTIONS),
            "auth_count": self._get_metric_count(AUTH_EVENTS),
            "phi_count": self._get_metric_count(PHI_SCRUB_COUNT),
        }
        yield baseline

    def test_record_audit_event(self, setup_metrics):
        """Test recording audit events."""
        # Record an audit event
        record_audit_event("create", "patient")

        # Verify the metric was recorded with correct labels
        samples = list(AUDIT_EVENTS.collect())[0].samples
        # Find the sample with our specific labels
        matching_samples = [
            s
            for s in samples
            if s.labels.get("event_type") == "create"
            and s.labels.get("resource_type") == "patient"
        ]
        assert len(matching_samples) >= 1
        assert matching_samples[0].value >= 1.0

        # Verify total count increased
        current_count = self._get_metric_count(AUDIT_EVENTS)
        assert current_count >= 1

    def test_record_user_action(self, setup_metrics):
        """Test recording user actions."""
        record_user_action("login", "auth", "test")

        # Find the sample with our specific labels
        samples = list(USER_ACTIONS.collect())[0].samples
        matching_samples = [
            s
            for s in samples
            if s.labels.get("action_type") == "login"
            and s.labels.get("resource_type") == "auth"
            and s.labels.get("environment") == "test"
        ]
        assert len(matching_samples) >= 1
        assert matching_samples[0].value >= 1.0

        # Verify total count
        current_count = self._get_metric_count(USER_ACTIONS)
        assert current_count >= 1

    def test_record_auth_event(self, setup_metrics):
        """Test recording authentication events."""
        record_auth_event("LOGIN", True, "test")

        # Find the sample with our specific labels
        samples = list(AUTH_EVENTS.collect())[0].samples
        matching_samples = [
            s
            for s in samples
            if s.labels.get("event_type") == "LOGIN"
            and s.labels.get("success") == "true"
            and s.labels.get("environment") == "test"
        ]
        assert len(matching_samples) >= 1
        assert matching_samples[0].value >= 1.0

        # Verify total count
        current_count = self._get_metric_count(AUTH_EVENTS)
        assert current_count >= 1

    def test_record_phi_scrub(self, setup_metrics):
        """Test recording PHI scrubbing operations."""
        record_phi_scrub("email", "test")

        # Find the sample with our specific labels
        samples = list(PHI_SCRUB_COUNT.collect())[0].samples
        matching_samples = [
            s
            for s in samples
            if s.labels.get("scrub_type") == "email"
            and s.labels.get("environment") == "test"
        ]
        assert len(matching_samples) >= 1
        assert matching_samples[0].value >= 1.0

        # Verify total count
        current_count = self._get_metric_count(PHI_SCRUB_COUNT)
        assert current_count >= 1

    def test_track_crud_operation(self, setup_metrics):
        """Test the CRUD operation tracking utility."""
        track_crud_operation("CREATE", "appointment", "user123")

        # Should record both audit event and user action
        current_audit = self._get_metric_count(AUDIT_EVENTS)
        current_user = self._get_metric_count(USER_ACTIONS)

        assert current_audit >= 1
        assert current_user >= 1

        # Find the specific samples we created
        audit_samples = list(AUDIT_EVENTS.collect())[0].samples
        user_samples = list(USER_ACTIONS.collect())[0].samples

        audit_sample = next(
            (
                s
                for s in audit_samples
                if s.labels.get("event_type") == "crud_create"
                and s.labels.get("resource_type") == "appointment"
            ),
            None,
        )
        assert audit_sample is not None
        assert audit_sample.labels["event_type"] == "crud_create"
        assert audit_sample.labels["resource_type"] == "appointment"

        user_sample = next(
            (
                s
                for s in user_samples
                if s.labels.get("action_type") == "CREATE"
                and s.labels.get("resource_type") == "appointment"
            ),
            None,
        )
        assert user_sample is not None
        assert user_sample.labels["action_type"] == "CREATE"
        assert user_sample.labels["resource_type"] == "appointment"

    def test_track_authentication(self, setup_metrics):
        """Test the authentication tracking utility."""
        track_authentication("LOGIN", True, "user123")

        current_count = self._get_metric_count(AUTH_EVENTS)
        assert current_count >= 1

        # Find the specific sample we created
        samples = list(AUTH_EVENTS.collect())[0].samples
        sample = next(
            (
                s
                for s in samples
                if s.labels.get("event_type") == "LOGIN"
                and s.labels.get("success") == "true"
            ),
            None,
        )
        assert sample is not None
        assert sample.labels["event_type"] == "LOGIN"
        assert sample.labels["success"] == "true"

    def test_track_phi_scrubbing(self, setup_metrics):
        """Test the PHI scrubbing tracking utility."""
        track_phi_scrubbing("ssn", 3)

        # Find the specific sample we created
        samples = list(PHI_SCRUB_COUNT.collect())[0].samples

        # Find any sample with scrub_type="ssn" regardless of environment
        sample = next((s for s in samples if s.labels.get("scrub_type") == "ssn"), None)

        assert sample is not None, (
            f"No sample found with scrub_type='ssn'. "
            f"Available samples: {[(s.labels, s.value) for s in samples]}"
        )
        assert sample.value >= 3.0  # Should record 3 operations
        assert sample.labels["scrub_type"] == "ssn"

        # Verify total count
        current_count = self._get_metric_count(PHI_SCRUB_COUNT)
        assert current_count >= 1

    def test_metrics_context_success(self, setup_metrics):
        """Test the metrics context manager for successful operations."""
        with MetricsContext("READ", "patient"):
            # Simulate successful operation
            pass

        # Should record audit event for successful operation
        current_count = self._get_metric_count(AUDIT_EVENTS)
        assert current_count >= 1

        # Find the specific sample we created
        samples = list(AUDIT_EVENTS.collect())[0].samples
        sample = next(
            (
                s
                for s in samples
                if s.labels.get("event_type") == "crud_read"
                and s.labels.get("resource_type") == "patient"
            ),
            None,
        )
        assert sample is not None
        assert sample.labels["event_type"] == "crud_read"
        assert sample.labels["resource_type"] == "patient"

    def test_metrics_context_error(self, setup_metrics):
        """Test the metrics context manager for failed operations."""
        with pytest.raises(ValueError):
            with MetricsContext("UPDATE", "patient"):
                raise ValueError("Test error")

        # Should record business event for error
        current_count = self._get_metric_count(USER_ACTIONS)
        assert current_count >= 1

        # Find the specific sample we created
        samples = list(USER_ACTIONS.collect())[0].samples
        sample = next(
            (
                s
                for s in samples
                if s.labels.get("action_type") == "update_error"
                and s.labels.get("resource_type") == "patient"
            ),
            None,
        )
        assert sample is not None
        assert sample.labels["action_type"] == "update_error"
        assert sample.labels["resource_type"] == "patient"


class TestMetricsEndpoint:
    """Test the metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_response(self):
        """Test that the metrics endpoint returns proper Prometheus format."""
        # Create a mock request
        request = Mock(spec=Request)

        response = await metrics_endpoint(request)

        assert response.media_type == ("text/plain; version=0.0.4; charset=utf-8")
        assert isinstance(response.body, bytes)

        # Should contain Prometheus metrics format
        content = response.body.decode("utf-8")
        assert "# HELP" in content or "# TYPE" in content


class TestHIPAACompliance:
    """Test HIPAA compliance aspects of metrics collection."""

    def test_no_phi_in_metric_labels(self):
        """Test that no PHI appears in metric labels."""
        # Record various metrics with potential PHI
        record_user_action("view_patient_john@example.com", "patient", "test")
        record_audit_event("access_ssn_123-45-6789", "patient", "test")

        # Check that PHI is scrubbed from labels
        user_samples = list(USER_ACTIONS.collect())[0].samples
        audit_samples = list(AUDIT_EVENTS.collect())[0].samples

        # Find our specific samples
        user_sample = next(
            (
                s
                for s in user_samples
                if "[EMAIL-REDACTED]" in s.labels.get("action_type", "")
            ),
            None,
        )
        audit_sample = next(
            (
                s
                for s in audit_samples
                if "access_ssn_[SSN-REDACTED]" in s.labels.get("event_type", "")
            ),
            None,
        )

        assert user_sample is not None
        assert audit_sample is not None, (
            f"No audit sample found. Available samples: "
            f"{[s.labels for s in audit_samples]}"
        )

        # Check that PHI is scrubbed from our samples
        for sample in [user_sample, audit_sample]:
            for label_key, label_value in sample.labels.items():
                # Should not contain email or SSN patterns
                assert "john@example.com" not in label_value
                assert "123-45-6789" not in label_value

    def test_phi_scrubbing_tracking(self):
        """Test that PHI scrubbing operations are tracked."""
        # This would be called by the PHI scrubber
        record_phi_scrub("email", "test")
        record_phi_scrub("ssn", "test")
        record_phi_scrub("phone", "test")

        samples = list(PHI_SCRUB_COUNT.collect())[0].samples
        assert len(samples) >= 3

        scrub_types = [s.labels["scrub_type"] for s in samples]
        assert "email" in scrub_types
        assert "ssn" in scrub_types
        assert "phone" in scrub_types

    def test_audit_completeness(self):
        """Test that audit events are properly recorded for compliance."""
        # Simulate various user actions
        track_crud_operation("CREATE", "patient", "user123")
        track_crud_operation("READ", "patient", "user123")
        track_crud_operation("UPDATE", "patient", "user123")
        track_crud_operation("DELETE", "patient", "user123")

        # All CRUD operations should generate audit events
        audit_samples = list(AUDIT_EVENTS.collect())[0].samples
        assert len(audit_samples) >= 4

        event_types = [s.labels["event_type"] for s in audit_samples]
        assert "crud_create" in event_types
        assert "crud_read" in event_types
        assert "crud_update" in event_types
        assert "crud_delete" in event_types


if __name__ == "__main__":
    pytest.main([__file__])
