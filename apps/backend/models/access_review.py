"""Access review and audit logging models."""

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, func

from models.base import Base


class AccessReviewLog(Base):
    """Log table for access review activities."""

    __tablename__ = "access_review_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # login, access, permission_check
    resource = Column(String(255), nullable=True)  # endpoint or resource accessed
    method = Column(String(10), nullable=True)  # HTTP method
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)  # Additional context
    created_at = Column(
        DateTime, nullable=False, default=func.now(), server_default=func.now()
    )

    def __repr__(self):
        return (
            f"<AccessReviewLog(id={self.id}, user_id='{self.user_id}', "
            f"action='{self.action}', success={self.success})>"
        )


class QuarterlyAccessReview(Base):
    """Quarterly access review records."""

    __tablename__ = "quarterly_access_reviews"

    id = Column(Integer, primary_key=True, index=True)
    quarter = Column(String(7), nullable=False)  # Format: 2024-Q1
    year = Column(Integer, nullable=False)
    quarter_number = Column(Integer, nullable=False)  # 1, 2, 3, 4
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, in_progress, completed
    reviewer_id = Column(String(255), nullable=True)
    total_users = Column(Integer, nullable=False, default=0)
    reviewed_users = Column(Integer, nullable=False, default=0)
    findings = Column(JSON, nullable=True)  # Summary of review findings
    recommendations = Column(JSON, nullable=True)  # Action items
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=func.now(), server_default=func.now()
    )
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return (
            f"<QuarterlyAccessReview(id={self.id}, quarter='{self.quarter}', "
            f"status='{self.status}')>"
        )


class AccessReviewChecklist(Base):
    """Checklist items for access reviews."""

    __tablename__ = "access_review_checklists"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(
        Integer, nullable=False, index=True
    )  # Foreign key to quarterly_access_reviews
    user_id = Column(String(255), nullable=False, index=True)
    item_type = Column(
        String(50), nullable=False
    )  # role_review, permission_audit, activity_check
    description = Column(Text, nullable=False)
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending, completed, skipped
    reviewer_notes = Column(Text, nullable=True)
    completed_by = Column(String(255), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=func.now(), server_default=func.now()
    )

    def __repr__(self):
        return (
            f"<AccessReviewChecklist(id={self.id}, user_id='{self.user_id}', "
            f"item_type='{self.item_type}', status='{self.status}')>"
        )
