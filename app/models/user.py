from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    users = db.relationship("User", back_populates="role", lazy="selectin")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    role = db.relationship("Role", back_populates="users")
    preferences = db.relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notification_preferences = db.relationship("NotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = db.relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    password_resets = db.relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")
    login_history = db.relationship("LoginHistory", back_populates="user")
    accounts = db.relationship("FinancialAccount", back_populates="user", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="user")
    import_batches = db.relationship("ImportBatch", back_populates="user", cascade="all, delete-orphan")
    import_mappings = db.relationship("ImportMapping", back_populates="user")
    budgets = db.relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    savings_goals = db.relationship("SavingsGoal", back_populates="user", cascade="all, delete-orphan")
    subscriptions = db.relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    subscription_detections = db.relationship("SubscriptionDetection", back_populates="user", cascade="all, delete-orphan")
    analysis_runs = db.relationship("AnalysisRun", back_populates="user", cascade="all, delete-orphan")
    reports = db.relationship("Report", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    feedback = db.relationship("UserFeedback", back_populates="user")
    category_rules = db.relationship("CategoryRule", back_populates="user")
    tags = db.relationship("TransactionTag", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    ip_hash = db.Column(db.String(128), nullable=True)

    user = db.relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession user_id={self.user_id}>"


class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="password_resets")

    def __repr__(self):
        return f"<PasswordReset user_id={self.user_id}>"


class UserPreference(db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    currency_code = db.Column(db.String(3), default="PKR", nullable=False)
    timezone = db.Column(db.String(64), default="Asia/Karachi", nullable=False)
    theme = db.Column(db.String(20), default="light", nullable=False)
    week_start = db.Column(db.Integer, default=0, nullable=False) # 0 = Monday
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreference user_id={self.user_id}>"


class LoginHistory(db.Model):
    __tablename__ = "login_histories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(30), nullable=False) # Success, Failure, Logout
    occurred_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    ip_hash = db.Column(db.String(128), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="login_history")

    def __repr__(self):
        return f"<LoginHistory event={self.event_type} user_id={self.user_id}>"

