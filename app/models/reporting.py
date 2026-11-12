from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    format = db.Column(db.String(10), default="PDF", nullable=False) # PDF / CSV / HTML
    file_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="Ready", nullable=False) # Queued, Ready, Failed
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="reports")
    sections = db.relationship("ReportSection", back_populates="report", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Report {self.title} ({self.format})>"


class ReportSection(db.Model):
    __tablename__ = "report_sections"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    section_key = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    content_json = db.Column(db.Text, nullable=False)
    display_order = db.Column(db.Integer, default=0, nullable=False)

    report = db.relationship("Report", back_populates="sections")

    def __repr__(self):
        return f"<ReportSection {self.title} order={self.display_order}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = db.Column(db.String(40), nullable=False) # BudgetAlert, AnomalyAlert, SubscriptionReminder, System
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    target_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.title} user_id={self.user_id}>"


class NotificationPreference(db.Model):
    __tablename__ = "notification_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    budget_alerts = db.Column(db.Boolean, default=True, nullable=False)
    anomaly_alerts = db.Column(db.Boolean, default=True, nullable=False)
    subscription_alerts = db.Column(db.Boolean, default=True, nullable=False)
    email_enabled = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreference user_id={self.user_id}>"


class UserFeedback(db.Model):
    __tablename__ = "user_feedbacks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    feedback_type = db.Column(db.String(40), nullable=False) # CategoryCorrection, BugReport, FeatureRequest
    message = db.Column(db.Text, nullable=True)
    suggested_category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    review_status = db.Column(db.String(20), default="New", nullable=False) # New, Reviewed, Resolved

    user = db.relationship("User", back_populates="feedback")
    transaction = db.relationship("Transaction")
    suggested_category = db.relationship("Category")

    def __repr__(self):
        return f"<UserFeedback type={self.feedback_type} user_id={self.user_id}>"

