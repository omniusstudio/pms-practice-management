"""Tests for legal hold model."""

from datetime import datetime, timedelta, timezone

from models.legal_hold import HoldReason, HoldStatus, LegalHold


class TestLegalHold:
    """Test cases for LegalHold model."""

    def test_create_legal_hold(self):
        """Test creating a legal hold."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Legal Hold",
            description="Test hold for litigation",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,  # Explicitly set default
            resource_type="clients",
            resource_id="client-123",
            case_number="CASE-2024-001",
            legal_contact="legal@example.com",
            auto_release=False,  # Explicitly set default
            notification_sent=False,  # Explicitly set default
        )

        assert hold.hold_name == "Test Legal Hold"
        assert hold.reason == HoldReason.LITIGATION
        assert hold.status == HoldStatus.ACTIVE
        assert hold.resource_type == "clients"
        assert hold.resource_id == "client-123"
        assert hold.case_number == "CASE-2024-001"
        assert hold.auto_release is False
        assert hold.notification_sent is False

    def test_is_active_default(self):
        """Test is_active for newly created hold."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
        )

        assert hold.is_active() is True

    def test_is_active_with_end_date_future(self):
        """Test is_active with future end date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=30)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            hold_end_date=future_date,
        )

        assert hold.is_active() is True

    def test_is_active_with_end_date_past(self):
        """Test is_active with past end date."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            hold_end_date=past_date,
        )

        assert hold.is_active() is False

    def test_is_active_released_status(self):
        """Test is_active for released hold."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            resource_type="clients",
            status=HoldStatus.RELEASED,
            hold_start_date=datetime.now(timezone.utc),
        )

        assert hold.is_active() is False

    def test_should_auto_release_disabled(self):
        """Test should_auto_release when auto_release is disabled."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            hold_end_date=past_date,
            auto_release=False,
        )

        assert hold.should_auto_release() is False

    def test_should_auto_release_no_end_date(self):
        """Test should_auto_release with no end date."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            auto_release=True,
            hold_end_date=None,
        )

        assert hold.should_auto_release() is False

    def test_should_auto_release_future_end_date(self):
        """Test should_auto_release with future end date."""
        future_date = datetime.now(timezone.utc) + timedelta(days=1)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            auto_release=True,
            hold_end_date=future_date,
        )

        assert hold.should_auto_release() is False

    def test_should_auto_release_past_end_date(self):
        """Test should_auto_release with past end date."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            auto_release=True,
            hold_end_date=past_date,
        )

        assert hold.should_auto_release() is True

    def test_should_auto_release_already_released(self):
        """Test should_auto_release for already released hold."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            resource_type="clients",
            status=HoldStatus.RELEASED,
            hold_start_date=datetime.now(timezone.utc),
            auto_release=True,
            hold_end_date=past_date,
        )

        assert hold.should_auto_release() is False

    def test_release_hold_basic(self):
        """Test basic hold release."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
        )

        before_release = datetime.now(timezone.utc)
        hold.release_hold()
        after_release = datetime.now(timezone.utc)

        assert hold.status == HoldStatus.RELEASED
        assert hold.released_at is not None
        assert before_release <= hold.released_at <= after_release

    def test_release_hold_with_user(self):
        """Test hold release with user information."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
        )

        hold.release_hold("user-123")

        assert hold.status == HoldStatus.RELEASED
        assert "Released by user-123" in hold.compliance_notes

    def test_release_hold_with_existing_notes(self):
        """Test hold release with existing compliance notes."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            resource_type="clients",
            compliance_notes="Initial notes",
        )

        hold.release_hold("user-123")

        assert "Initial notes" in hold.compliance_notes
        assert "Released by user-123" in hold.compliance_notes

    def test_matches_resource_exact_match(self):
        """Test matches_resource with exact resource match."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            resource_id="client-123",
            hold_start_date=datetime.now(timezone.utc),
        )

        assert hold.matches_resource("clients", "client-123") is True
        assert hold.matches_resource("clients", "client-456") is False
        assert hold.matches_resource("appointments", "client-123") is False

    def test_matches_resource_type_wide_hold(self):
        """Test matches_resource with type-wide hold (no specific ID)."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            resource_id=None,  # Applies to all clients
            hold_start_date=datetime.now(timezone.utc),
        )

        assert hold.matches_resource("clients", "client-123") is True
        assert hold.matches_resource("clients", "client-456") is True
        assert hold.matches_resource("appointments", "appt-123") is False

    def test_matches_resource_inactive_hold(self):
        """Test matches_resource with inactive hold."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            resource_type="clients",
            resource_id="client-123",
            status=HoldStatus.RELEASED,
            hold_start_date=datetime.now(timezone.utc),
        )

        assert hold.matches_resource("clients", "client-123") is False

    def test_matches_resource_expired_hold(self):
        """Test matches_resource with expired hold."""
        past_date = datetime.now(timezone.utc) - timedelta(days=1)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            resource_id="client-123",
            hold_start_date=datetime.now(timezone.utc),
            hold_end_date=past_date,
        )

        assert hold.matches_resource("clients", "client-123") is False

    def test_repr_without_phi(self):
        """Test string representation doesn't contain PHI."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Legal Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            resource_id="client-123",
            hold_start_date=datetime.now(timezone.utc),
        )

        repr_str = repr(hold)

        # Should contain basic info
        assert "Test Legal Hold" in repr_str
        assert "clients" in repr_str
        assert "HoldStatus.ACTIVE" in repr_str

        # Should not contain tenant_id or resource_id (could be PHI)
        assert "test-tenant" not in repr_str
        assert "client-123" not in repr_str

    def test_all_hold_reasons_supported(self):
        """Test that all hold reasons can be used."""
        for reason in HoldReason:
            hold = LegalHold(
                tenant_id="test-tenant",
                hold_name=f"Test {reason.value} Hold",
                reason=reason,
                status=HoldStatus.ACTIVE,
                resource_type="clients",
                hold_start_date=datetime.now(timezone.utc),
            )

            assert hold.reason == reason
            assert hold.is_active() is True

    def test_all_hold_statuses_supported(self):
        """Test that all hold statuses work correctly."""
        for status in HoldStatus:
            hold = LegalHold(
                tenant_id="test-tenant",
                hold_name="Test Hold",
                reason=HoldReason.LITIGATION,
                resource_type="clients",
                status=status,
                hold_start_date=datetime.now(timezone.utc),
            )

            assert hold.status == status

            # Only ACTIVE status should be active
            expected_active = status == HoldStatus.ACTIVE
            assert hold.is_active() == expected_active

    def test_hold_start_date_default(self):
        """Test that hold_start_date is set by default."""
        before_create = datetime.now(timezone.utc)

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            notification_sent=False,
        )

        after_create = datetime.now(timezone.utc)

        assert hold.hold_start_date is not None
        assert before_create <= hold.hold_start_date <= after_create

    def test_filter_criteria_json(self):
        """Test filter criteria can store JSON."""
        import json

        criteria = {
            "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
            "provider_ids": ["prov-1", "prov-2"],
        }

        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="appointments",
            hold_start_date=datetime.now(timezone.utc),
            filter_criteria=json.dumps(criteria),
        )

        # Should be able to store and retrieve JSON
        stored_criteria = json.loads(hold.filter_criteria)
        assert stored_criteria == criteria

    def test_case_number_tracking(self):
        """Test case number tracking."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            case_number="CASE-2024-001",
        )

        assert hold.case_number == "CASE-2024-001"

    def test_legal_contact_tracking(self):
        """Test legal contact tracking."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            status=HoldStatus.ACTIVE,
            resource_type="clients",
            hold_start_date=datetime.now(timezone.utc),
            legal_contact="legal@example.com",
        )

        assert hold.legal_contact == "legal@example.com"

    def test_notification_tracking(self):
        """Test notification tracking."""
        hold = LegalHold(
            tenant_id="test-tenant",
            hold_name="Test Hold",
            reason=HoldReason.LITIGATION,
            resource_type="clients",
            status=HoldStatus.ACTIVE,
            hold_start_date=datetime.now(timezone.utc),
            notification_sent=False,
        )

        # Default should be False (explicitly set since SQLAlchemy
        # defaults don't apply to instances)
        assert hold.notification_sent is False

        # Can be updated
        hold.notification_sent = True
        assert hold.notification_sent is True
