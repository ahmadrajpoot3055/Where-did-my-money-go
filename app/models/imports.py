from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class ImportBatch(db.Model):
    __tablename__ = "import_batches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey("financial_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=True)
    file_hash = db.Column(db.String(64), nullable=True)
    file_type = db.Column(db.String(10), nullable=True) # CSV / XLSX
    status = db.Column(db.String(30), default="Uploaded", nullable=False) # Uploaded, Processing, Preview, Completed, CompletedWithErrors, Failed
    total_rows = db.Column(db.Integer, default=0, nullable=False)
    accepted_rows = db.Column(db.Integer, default=0, nullable=False)
    rejected_rows = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="import_batches")
    account = db.relationship("FinancialAccount", back_populates="import_batches")
    errors = db.relationship("ImportError", back_populates="batch", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="import_batch")

    def __repr__(self):
        return f"<ImportBatch id={self.id} status={self.status}>"


class ImportMapping(db.Model):
    __tablename__ = "import_mappings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    account_type_id = db.Column(db.Integer, db.ForeignKey("account_types.id", ondelete="SET NULL"), nullable=True)
    mapping_name = db.Column(db.String(100), nullable=False)
    date_column = db.Column(db.String(100), nullable=False)
    description_column = db.Column(db.String(100), nullable=False)
    amount_column = db.Column(db.String(100), nullable=True)
    debit_column = db.Column(db.String(100), nullable=True)
    credit_column = db.Column(db.String(100), nullable=True)
    date_format = db.Column(db.String(40), nullable=True)
    delimiter = db.Column(db.String(5), default=",", nullable=False)

    user = db.relationship("User", back_populates="import_mappings")
    account_type = db.relationship("AccountType")

    def __repr__(self):
        return f"<ImportMapping {self.mapping_name}>"


class ImportError(db.Model):
    __tablename__ = "import_errors"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = db.Column(db.Integer, nullable=False)
    error_code = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    raw_row_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    batch = db.relationship("ImportBatch", back_populates="errors")

    def __repr__(self):
        return f"<ImportError batch={self.batch_id} row={self.row_number}>"

