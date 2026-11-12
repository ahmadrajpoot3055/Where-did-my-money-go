import pytest
from decimal import Decimal
from datetime import date, datetime, timezone
from app import create_app
from app.extensions import db
from app.models import (
    Role, User, UserPreference, NotificationPreference,
    AccountType, FinancialAccount,
    Category, Subcategory, Merchant, MerchantAlias, CategoryRule,
    Transaction, TransactionType, TransactionStatus
)
from app.utils.security import hash_password

def utcnow():
    return datetime.now(timezone.utc)

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()

        # Seed minimal lookup data
        role_admin = Role(name="admin", description="Admin")
        role_user = Role(name="user", description="User")
        db.session.add_all([role_admin, role_user])

        acc_types = [AccountType(name=n) for n in ["current", "savings", "cash", "credit"]]
        db.session.add_all(acc_types)

        tx_types = [TransactionType(name=n) for n in ["income", "expense", "transfer"]]
        db.session.add_all(tx_types)

        tx_statuses = [TransactionStatus(name=n) for n in ["completed", "pending", "void", "failed"]]
        db.session.add_all(tx_statuses)

        cat_food = Category(name="Food & Dining", kind="Expense", user_id=None, is_active=True, created_at=utcnow())
        cat_transport = Category(name="Transport", kind="Expense", user_id=None, is_active=True, created_at=utcnow())
        cat_income = Category(name="Income", kind="Income", user_id=None, is_active=True, created_at=utcnow())
        cat_groceries = Category(name="Groceries", kind="Expense", user_id=None, is_active=True, created_at=utcnow())
        cat_subscriptions = Category(name="Subscriptions", kind="Expense", user_id=None, is_active=True, created_at=utcnow())
        cat_utilities = Category(name="Utilities", kind="Expense", user_id=None, is_active=True, created_at=utcnow())
        cat_cash = Category(name="Cash Withdrawal", kind="Expense", user_id=None, is_active=True, created_at=utcnow())
        db.session.add_all([cat_food, cat_transport, cat_income, cat_groceries, cat_subscriptions, cat_utilities, cat_cash])
        db.session.flush()

        # Seed Merchant & Alias
        merch_kfc = Merchant(name="KFC", default_category_id=cat_food.id, is_active=True)
        db.session.add(merch_kfc)
        db.session.flush()
        alias_kfc = MerchantAlias(merchant_id=merch_kfc.id, alias_text="POS PURCHASE KFC DHA", source="Admin", created_at=utcnow())
        db.session.add(alias_kfc)

        # Seed Rule
        rule_fuel = CategoryRule(category_id=cat_transport.id, pattern="SHELL", match_type="Contains", priority=15, is_active=True)
        db.session.add(rule_fuel)

        # Users
        u1 = User(
            full_name="Alice User",
            email="alice@test.com",
            password_hash=hash_password("Pass123!"),
            role_id=role_user.id,
            is_active=True,
            created_at=utcnow()
        )
        u2 = User(
            full_name="Bob User",
            email="bob@test.com",
            password_hash=hash_password("Pass123!"),
            role_id=role_user.id,
            is_active=True,
            created_at=utcnow()
        )
        admin = User(
            full_name="Admin User",
            email="admin@test.com",
            password_hash=hash_password("Admin123!"),
            role_id=role_admin.id,
            is_active=True,
            created_at=utcnow()
        )
        db.session.add_all([u1, u2, admin])
        db.session.flush()

        db.session.add_all([
            UserPreference(user_id=u1.id, currency_code="PKR", timezone="Asia/Karachi", theme="light", week_start=0, created_at=utcnow(), updated_at=utcnow()),
            UserPreference(user_id=u2.id, currency_code="PKR", timezone="Asia/Karachi", theme="light", week_start=0, created_at=utcnow(), updated_at=utcnow()),
            UserPreference(user_id=admin.id, currency_code="PKR", timezone="Asia/Karachi", theme="light", week_start=0, created_at=utcnow(), updated_at=utcnow()),
            NotificationPreference(user_id=u1.id, created_at=utcnow()),
            NotificationPreference(user_id=u2.id, created_at=utcnow()),
            NotificationPreference(user_id=admin.id, created_at=utcnow()),
        ])

        # Financial accounts
        a1 = FinancialAccount(user_id=u1.id, account_type_id=acc_types[0].id, name="Alice HBL", currency_code="PKR", opening_balance=Decimal("50000.00"), is_active=True, created_at=utcnow())
        a2 = FinancialAccount(user_id=u2.id, account_type_id=acc_types[0].id, name="Bob UBL", currency_code="PKR", opening_balance=Decimal("20000.00"), is_active=True, created_at=utcnow())
        db.session.add_all([a1, a2])

        db.session.commit()

        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client, app):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Alice User"
        sess["user_role"] = "user"
    return client

@pytest.fixture
def admin_client(client, app):
    with client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["user_name"] = "Admin User"
        sess["user_role"] = "admin"
    return client

