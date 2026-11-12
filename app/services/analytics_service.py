from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from app.extensions import db
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.category import Category
from app.models.account import FinancialAccount

class AnalyticsService:
    @classmethod
    def get_dashboard_kpis(
        cls,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[int] = None,
        currency_code: str = "PKR"
    ) -> Dict[str, Any]:
        """
        Calculate KPI cards: Total Income, Total Expenses, Net Cash Flow, Savings Rate.
        Excludes transfers and cancelled/void/failed transactions.
        """
        completed_status = TransactionStatus.query.filter_by(name="completed").first()
        income_type = TransactionType.query.filter_by(name="income").first()
        expense_type = TransactionType.query.filter_by(name="expense").first()

        status_id = completed_status.id if completed_status else 1
        income_type_id = income_type.id if income_type else 1
        expense_type_id = expense_type.id if expense_type else 2

        query = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.transaction_status_id == status_id,
            Transaction.currency_code == currency_code
        )

        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        all_txs = query.all()

        total_income = Decimal("0.00")
        total_expense = Decimal("0.00")

        for tx in all_txs:
            if tx.transaction_type_id == income_type_id:
                total_income += tx.amount
            elif tx.transaction_type_id == expense_type_id:
                total_expense += tx.amount

        net_cash_flow = total_income - total_expense

        savings_rate = None
        if total_income > Decimal("0.00"):
            rate = ((total_income - total_expense) / total_income) * Decimal("100.0")
            savings_rate = float(round(rate, 2))

        # Month-over-month calculation if date range is monthly or default
        prev_month_expense = Decimal("0.00")
        if start_date and end_date:
            # Shift back by 1 month
            prev_start = start_date - relativedelta(months=1)
            prev_end = end_date - relativedelta(months=1)
            prev_txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_status_id == status_id,
                Transaction.currency_code == currency_code,
                Transaction.transaction_type_id == expense_type_id,
                Transaction.transaction_date >= prev_start,
                Transaction.transaction_date <= prev_end
            ).all()
            for ptx in prev_txs:
                prev_month_expense += ptx.amount

        mom_change = None
        if prev_month_expense > Decimal("0.00"):
            change = ((total_expense - prev_month_expense) / prev_month_expense) * Decimal("100.0")
            mom_change = float(round(change, 1))

        return {
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "net_cash_flow": float(net_cash_flow),
            "savings_rate": savings_rate,
            "mom_expense_change": mom_change,
            "currency_code": currency_code,
            "transaction_count": len(all_txs)
        }

    @classmethod
    def get_category_breakdown(
        cls,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[int] = None,
        currency_code: str = "PKR"
    ) -> List[Dict[str, Any]]:
        """
        Sum of expense transactions grouped by category.
        """
        completed_status = TransactionStatus.query.filter_by(name="completed").first()
        expense_type = TransactionType.query.filter_by(name="expense").first()

        status_id = completed_status.id if completed_status else 1
        expense_type_id = expense_type.id if expense_type else 2

        query = db.session.query(
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("tx_count")
        ).outerjoin(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_status_id == status_id,
            Transaction.transaction_type_id == expense_type_id,
            Transaction.currency_code == currency_code
        )

        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        if start_date:
            query = query.filter(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.filter(Transaction.transaction_date <= end_date)

        rows = query.group_by(Category.name).all()

        results = []
        total_sum = sum(float(r.total_amount or 0) for r in rows)

        for r in rows:
            amount = float(r.total_amount or 0)
            cat_name = r.category_name or "Uncategorized"
            pct = round((amount / total_sum * 100), 1) if total_sum > 0 else 0
            results.append({
                "category": cat_name,
                "amount": amount,
                "percentage": pct,
                "count": r.tx_count
            })

        results.sort(key=lambda x: x["amount"], reverse=True)
        return results

    @classmethod
    def get_monthly_trends(
        cls,
        user_id: int,
        months: int = 6,
        currency_code: str = "PKR"
    ) -> List[Dict[str, Any]]:
        """
        Get income vs expense trends for the last N months.
        """
        completed_status = TransactionStatus.query.filter_by(name="completed").first()
        income_type = TransactionType.query.filter_by(name="income").first()
        expense_type = TransactionType.query.filter_by(name="expense").first()

        status_id = completed_status.id if completed_status else 1
        income_type_id = income_type.id if income_type else 1
        expense_type_id = expense_type.id if expense_type else 2

        today = date.today()
        trends = []

        for i in range(months - 1, -1, -1):
            m_date = today - relativedelta(months=i)
            m_start = date(m_date.year, m_date.month, 1)
            # Last day of month
            next_m = m_start + relativedelta(months=1)
            m_end = next_m - relativedelta(days=1)

            txs = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.transaction_status_id == status_id,
                Transaction.currency_code == currency_code,
                Transaction.transaction_date >= m_start,
                Transaction.transaction_date <= m_end
            ).all()

            inc = sum(float(t.amount) for t in txs if t.transaction_type_id == income_type_id)
            exp = sum(float(t.amount) for t in txs if t.transaction_type_id == expense_type_id)

            trends.append({
                "month_label": m_start.strftime("%b %Y"),
                "income": round(inc, 2),
                "expense": round(exp, 2),
                "net": round(inc - exp, 2)
            })

        return trends

