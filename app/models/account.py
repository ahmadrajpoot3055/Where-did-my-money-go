from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class AccountType(db.Model):
    __tablename__ = "account_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False) # current, savings, cash, wallet, credit
    description = db.Column(db.String(255), nullable=True)

    accounts = db.relationship("FinancialAccount", back_populates="account_type")

    def __repr__(self):
        return f"<AccountType {self.name}>"


class FinancialAccount(db.Model):
    __tablename__ = "financial_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_type_id = db.Column(db.Integer, db.ForeignKey("account_types.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    institution_name = db.Column(db.String(120), nullable=True)
    currency_code = db.Column(db.String(3), default="PKR", nullable=False)
    opening_balance = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="accounts")
    account_type = db.relationship("AccountType", back_populates="accounts")
    transactions = db.relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    import_batches = db.relationship("ImportBatch", back_populates="account")

    @property
    def current_balance(self):
        # Calculate balance = opening_balance + income - expense (transfers depend on direction)
        from app.models.transaction import Transaction
        balance = float(self.opening_balance)
        for tx in self.transactions:
            if tx.transaction_status and tx.transaction_status.name in ("completed", "posted"):
                if tx.transaction_type and tx.transaction_type.name == "income":
                    balance += float(tx.amount)
                elif tx.transaction_type and tx.transaction_type.name == "expense":
                    balance -= float(tx.amount)
        return balance

    def __repr__(self):
        return f"<FinancialAccount {self.name} ({self.currency_code})>"

