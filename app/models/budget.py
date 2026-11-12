from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    period_type = db.Column(db.String(20), default="Monthly", nullable=False) # Monthly / Weekly / Custom
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    currency_code = db.Column(db.String(3), default="PKR", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship("User", back_populates="budgets")
    items = db.relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Budget {self.name} ({self.period_type})>"


class BudgetItem(db.Model):
    __tablename__ = "budget_items"

    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    limit_amount = db.Column(db.Numeric(12, 2), nullable=False)
    warning_percent = db.Column(db.Numeric(5, 2), default=80.00, nullable=False)

    budget = db.relationship("Budget", back_populates="items")
    category = db.relationship("Category", back_populates="budget_items")
    alerts = db.relationship("BudgetAlert", back_populates="budget_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BudgetItem budget_id={self.budget_id} category_id={self.category_id} limit={self.limit_amount}>"


class BudgetAlert(db.Model):
    __tablename__ = "budget_alerts"

    id = db.Column(db.Integer, primary_key=True)
    budget_item_id = db.Column(db.Integer, db.ForeignKey("budget_items.id", ondelete="CASCADE"), nullable=False, index=True)
    threshold_percent = db.Column(db.Numeric(5, 2), nullable=False)
    actual_percent = db.Column(db.Numeric(7, 2), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)

    budget_item = db.relationship("BudgetItem", back_populates="alerts")

    def __repr__(self):
        return f"<BudgetAlert item={self.budget_item_id} percent={self.actual_percent}%>"


class SavingsGoal(db.Model):
    __tablename__ = "savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    target_date = db.Column(db.Date, nullable=True)
    currency_code = db.Column(db.String(3), default="PKR", nullable=False)
    status = db.Column(db.String(20), default="Active", nullable=False) # Active / Completed / Paused
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="savings_goals")
    contributions = db.relationship("SavingsContribution", back_populates="goal", cascade="all, delete-orphan")

    @property
    def current_saved(self):
        return sum(float(c.amount) for c in self.contributions)

    @property
    def progress_percent(self):
        target = float(self.target_amount)
        if target <= 0:
            return 0.0
        return min(100.0, round((self.current_saved / target) * 100, 1))

    def __repr__(self):
        return f"<SavingsGoal {self.name} target={self.target_amount}>"


class SavingsContribution(db.Model):
    __tablename__ = "savings_contributions"

    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    contribution_date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(255), nullable=True)

    goal = db.relationship("SavingsGoal", back_populates="contributions")

    def __repr__(self):
        return f"<SavingsContribution goal_id={self.goal_id} amount={self.amount}>"

