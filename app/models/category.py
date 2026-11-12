from datetime import datetime, timezone
from app.extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True) # Null for global
    name = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(20), default="Expense", nullable=False) # Income / Expense / Both
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    subcategories = db.relationship("Subcategory", back_populates="category", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="category")
    rules = db.relationship("CategoryRule", back_populates="category", cascade="all, delete-orphan")
    merchants = db.relationship("Merchant", back_populates="default_category")
    budget_items = db.relationship("BudgetItem", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name} ({self.kind})>"


class Subcategory(db.Model):
    __tablename__ = "subcategories"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    category = db.relationship("Category", back_populates="subcategories")

    def __repr__(self):
        return f"<Subcategory {self.name}>"


class Merchant(db.Model):
    __tablename__ = "merchants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    default_category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    default_category = db.relationship("Category", back_populates="merchants")
    aliases = db.relationship("MerchantAlias", back_populates="merchant", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", back_populates="merchant")

    def __repr__(self):
        return f"<Merchant {self.name}>"


class MerchantAlias(db.Model):
    __tablename__ = "merchant_aliases"

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False, index=True)
    alias_text = db.Column(db.String(180), nullable=False, index=True)
    source = db.Column(db.String(30), default="Admin", nullable=False) # Admin / User / Imported
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    merchant = db.relationship("Merchant", back_populates="aliases")

    def __repr__(self):
        return f"<MerchantAlias {self.alias_text} -> {self.merchant_id}>"


class CategoryRule(db.Model):
    __tablename__ = "category_rules"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    pattern = db.Column(db.String(200), nullable=False)
    match_type = db.Column(db.String(20), default="Contains", nullable=False) # Contains / Exact / Regex
    priority = db.Column(db.Integer, default=10, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    category = db.relationship("Category", back_populates="rules")
    user = db.relationship("User", back_populates="category_rules")

    def __repr__(self):
        return f"<CategoryRule pattern='{self.pattern}' cat_id={self.category_id}>"

