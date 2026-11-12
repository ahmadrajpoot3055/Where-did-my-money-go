from decimal import Decimal
from datetime import date, timedelta
from app.extensions import db
from app.models.transaction import Transaction
from app.models.budget import Budget, BudgetItem
from app.services.analytics_service import AnalyticsService
from app.services.anomaly_service import AnomalyService
from app.services.subscription_service import SubscriptionService

def test_analytics_kpis(app):
    with app.app_context():
        # Add income and expense
        t1 = Transaction(
            user_id=1, account_id=1, transaction_type_id=1, transaction_status_id=1,
            transaction_date=date(2026, 11, 1), description_original="SALARY",
            description_normalized="SALARY", amount=Decimal("100000.00"), currency_code="PKR"
        )
        t2 = Transaction(
            user_id=1, account_id=1, transaction_type_id=2, transaction_status_id=1,
            transaction_date=date(2026, 11, 2), description_original="RENT",
            description_normalized="RENT", amount=Decimal("40000.00"), currency_code="PKR"
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        kpis = AnalyticsService.get_dashboard_kpis(user_id=1, currency_code="PKR")
        assert kpis["total_income"] == 100000.00
        assert kpis["total_expense"] == 40000.00
        assert kpis["net_cash_flow"] == 60000.00
        assert kpis["savings_rate"] == 60.00 # (100k - 40k) / 100k = 60%

def test_anomaly_detection_flags_outlier(app):
    with app.app_context():
        # Normal expenses around 1,000 to 2,000
        for i in range(10):
            tx = Transaction(
                user_id=1, account_id=1, transaction_type_id=2, transaction_status_id=1,
                transaction_date=date(2026, 10, 1 + i), description_original=f"LUNCH {i}",
                description_normalized="LUNCH", amount=Decimal("1500.00"), currency_code="PKR",
                category_id=1 # Food & Dining
            )
            db.session.add(tx)

        # Huge outlier expense in Food & Dining
        huge_tx = Transaction(
            user_id=1, account_id=1, transaction_type_id=2, transaction_status_id=1,
            transaction_date=date(2026, 10, 20), description_original="EXPENSIVE BANQUET",
            description_normalized="EXPENSIVE BANQUET", amount=Decimal("50000.00"), currency_code="PKR",
            category_id=1
        )
        db.session.add(huge_tx)
        db.session.commit()

        run = AnomalyService.run_detection(user_id=1, start_date=date(2026, 10, 1), end_date=date(2026, 10, 31))
        assert run.status == "Completed"
        assert len(run.results) >= 1
        assert run.results[0].transaction_id == huge_tx.id

def test_recurring_subscription_detection(app):
    with app.app_context():
        # Two monthly Netflix payments ~30 days apart
        d1 = date(2026, 9, 2)
        d2 = date(2026, 10, 2)
        t1 = Transaction(
            user_id=1, account_id=1, transaction_type_id=2, transaction_status_id=1,
            transaction_date=d1, description_original="NETFLIX.COM",
            description_normalized="NETFLIX.COM", amount=Decimal("1500.00"), currency_code="PKR"
        )
        t2 = Transaction(
            user_id=1, account_id=1, transaction_type_id=2, transaction_status_id=1,
            transaction_date=d2, description_original="NETFLIX.COM",
            description_normalized="NETFLIX.COM", amount=Decimal("1500.00"), currency_code="PKR"
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        candidates = SubscriptionService.detect_recurring_candidates(user_id=1)
        assert len(candidates) >= 1
        assert candidates[0].candidate_name == "NETFLIX.COM"
        assert candidates[0].frequency_guess == "Monthly"

