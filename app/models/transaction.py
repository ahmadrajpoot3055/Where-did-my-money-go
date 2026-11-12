from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

# Association table for Transaction <-> TransactionTag
transaction_tag_links = db.Table(
    "transaction_tag_links",
    db.Column("transaction_id", db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("transaction_tags.id", ondelete="CASCADE"), primary_key=True)
)

class TransactionType(db.Model):
    __tablename__ = "transaction_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False) # income, expense, transfer
    description = db.Column(db.String(255), nullable=True)

    transactions = db.relationship("Transaction", back_populates="transaction_type")

    def __repr__(self):
        return f"<TransactionType {self.name}>"


class TransactionStatus(db.Model):
    __tablename__ = "transaction_statuses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False) # completed, pending, void, failed
    description = db.Column(db.String(255), nullable=True)

    transactions = db.relationship("Transaction", back_populates="transaction_status")

    def __repr__(self):
        return f"<TransactionStatus {self.name}>"


class TransactionTag(db.Model):
    __tablename__ = "transaction_tags"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(40), nullable=False)
    color = db.Column(db.String(20), default="#6c757d", nullable=False)

    user = db.relationship("User", back_populates="tags")
    transactions = db.relationship("Transaction", secondary=transaction_tag_links, back_populates="tags")

    def __repr__(self):
        return f"<TransactionTag {self.name}>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("financial_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_type_id = db.Column(db.Integer, db.ForeignKey("transaction_types.id"), nullable=False)
    transaction_status_id = db.Column(db.Integer, db.ForeignKey("transaction_statuses.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    description_original = db.Column(db.String(500), nullable=False)
    description_normalized = db.Column(db.String(500), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency_code = db.Column(db.String(3), default="PKR", nullable=False)
    reference = db.Column(db.String(120), nullable=True, index=True)
    
    category_confidence = db.Column(db.Numeric(5, 4), nullable=True) # 0.0000 to 1.0000
    category_method = db.Column(db.String(30), nullable=True) # Rule, Merchant, ML, Manual
    is_reviewed = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="transactions")
    account = db.relationship("FinancialAccount", back_populates="transactions")
    import_batch = db.relationship("ImportBatch", back_populates="transactions")
    transaction_type = db.relationship("TransactionType", back_populates="transactions")
    transaction_status = db.relationship("TransactionStatus", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")
    merchant = db.relationship("Merchant", back_populates="transactions")
    
    tags = db.relationship("TransactionTag", secondary=transaction_tag_links, back_populates="transactions")
    notes = db.relationship("TransactionNote", back_populates="transaction", cascade="all, delete-orphan")
    attachments = db.relationship("TransactionAttachment", back_populates="transaction", cascade="all, delete-orphan")
    splits = db.relationship("TransactionSplit", back_populates="transaction", cascade="all, delete-orphan")
    anomaly_results = db.relationship("AnomalyResult", back_populates="transaction", cascade="all, delete-orphan")
    subscription_payment = db.relationship("SubscriptionPayment", back_populates="transaction", uselist=False)

    def __repr__(self):
        return f"<Transaction {self.id}: {self.description_original} ({self.amount} {self.currency_code})>"


class TransactionNote(db.Model):
    __tablename__ = "transaction_notes"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    transaction = db.relationship("Transaction", back_populates="notes")
    user = db.relationship("User")

    def __repr__(self):
        return f"<TransactionNote tx={self.transaction_id}>"


class TransactionAttachment(db.Model):
    __tablename__ = "transaction_attachments"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    stored_name = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    transaction = db.relationship("Transaction", back_populates="attachments")
    user = db.relationship("User")

    def __repr__(self):
        return f"<TransactionAttachment {self.original_name}>"


class TransactionSplit(db.Model):
    __tablename__ = "transaction_splits"

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(255), nullable=True)

    transaction = db.relationship("Transaction", back_populates="splits")
    category = db.relationship("Category")

    def __repr__(self):
        return f"<TransactionSplit tx={self.transaction_id} cat={self.category_id} amount={self.amount}>"

