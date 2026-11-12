from sqlalchemy import inspect
from app.extensions import db

def test_database_has_at_least_40_tables(app):
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        print(f"Table count: {len(table_names)}")
        assert len(table_names) >= 40, f"Expected at least 40 physical tables, found {len(table_names)}"

def test_expected_tables_present(app):
    expected_tables = [
        "users", "roles", "user_sessions", "password_resets", "user_preferences", "login_histories",
        "account_types", "financial_accounts", "import_batches", "import_mappings", "import_errors",
        "transaction_types", "transaction_statuses", "transactions", "transaction_tags", "transaction_tag_links",
        "transaction_notes", "transaction_attachments", "transaction_splits", "categories", "subcategories",
        "merchants", "merchant_aliases", "category_rules", "budgets", "budget_items", "budget_alerts",
        "savings_goals", "savings_contributions", "anomaly_models", "analysis_runs", "anomaly_results",
        "anomaly_reviews", "subscriptions", "subscription_payments", "subscription_detections",
        "reports", "report_sections", "notifications", "notification_preferences", "user_feedbacks"
    ]
    with app.app_context():
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        for tbl in expected_tables:
            assert tbl in existing, f"Table '{tbl}' is missing from schema"

