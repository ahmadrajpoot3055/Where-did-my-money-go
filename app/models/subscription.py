from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    expected_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency_code = db.Column(db.String(3), default="PKR", nullable=False)
    frequency = db.Column(db.String(20), default="Monthly", nullable=False) # Weekly, Monthly, Yearly, Other
    next_expected_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="Active", nullable=False) # Active, Cancelled, Paused

    user = db.relationship("User", back_populates="subscriptions")
    merchant = db.relationship("Merchant")
    payments = db.relationship("SubscriptionPayment", back_populates="subscription", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subscription {self.name} ({self.frequency} - {self.expected_amount} {self.currency_code})>"


class SubscriptionPayment(db.Model):
    __tablename__ = "subscription_payments"

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), unique=True, nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), nullable=False)
    paid_date = db.Column(db.Date, nullable=False)

    subscription = db.relationship("Subscription", back_populates="payments")
    transaction = db.relationship("Transaction", back_populates="subscription_payment")

    def __repr__(self):
        return f"<SubscriptionPayment sub={self.subscription_id} tx={self.transaction_id} amount={self.paid_amount}>"


class SubscriptionDetection(db.Model):
    __tablename__ = "subscription_detections"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True)
    candidate_name = db.Column(db.String(120), nullable=False)
    frequency_guess = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Numeric(5, 4), nullable=False)
    evidence_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="Pending", nullable=False) # Pending, Confirmed, Rejected
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="subscription_detections")
    merchant = db.relationship("Merchant")

    def __repr__(self):
        return f"<SubscriptionDetection {self.candidate_name} ({self.frequency_guess})>"

