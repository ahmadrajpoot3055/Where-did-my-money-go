from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from flask import render_template, request, session, redirect, url_for, g
from app.blueprints.dashboard import dashboard_bp
from app.utils.decorators import login_required
from app.services.analytics_service import AnalyticsService
from app.models.account import FinancialAccount
from app.models.transaction import Transaction
from app.models.intelligence import AnomalyResult
from app.models.subscription import SubscriptionDetection

@dashboard_bp.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))
    return render_template("landing.html")

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    user = g.current_user
    currency_code = user.preferences.currency_code if user.preferences else "PKR"

    # Filters
    account_id = request.args.get("account_id", type=int)
    period = request.args.get("period", "this_month") # this_month, last_30_days, this_year, custom
    
    today = date.today()
    if period == "this_month":
        start_date = date(today.year, today.month, 1)
        next_m = start_date + relativedelta(months=1)
        end_date = next_m - relativedelta(days=1)
    elif period == "last_30_days":
        start_date = today - relativedelta(days=30)
        end_date = today
    elif period == "this_year":
        start_date = date(today.year, 1, 1)
        end_date = date(today.year, 12, 31)
    elif period == "custom":
        try:
            start_date = datetime.strptime(request.args.get("start_date", ""), "%Y-%m-%d").date()
            end_date = datetime.strptime(request.args.get("end_date", ""), "%Y-%m-%d").date()
        except ValueError:
            start_date = date(today.year, today.month, 1)
            end_date = today
    else:
        start_date = date(today.year, today.month, 1)
        end_date = today

    # Analytics Service calls
    kpis = AnalyticsService.get_dashboard_kpis(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        currency_code=currency_code
    )

    category_breakdown = AnalyticsService.get_category_breakdown(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        account_id=account_id,
        currency_code=currency_code
    )

    monthly_trends = AnalyticsService.get_monthly_trends(
        user_id=user.id,
        months=6,
        currency_code=currency_code
    )

    # Recent transactions
    recent_transactions = Transaction.query.filter_by(
        user_id=user.id
    ).order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(8).all()

    # Accounts
    accounts = FinancialAccount.query.filter_by(user_id=user.id, is_active=True).all()

    # Review Alerts count
    pending_anomalies = AnomalyResult.query.join(Transaction).filter(
        Transaction.user_id == user.id,
        AnomalyResult.status == "New"
    ).count()

    pending_subs = SubscriptionDetection.query.filter_by(
        user_id=user.id,
        status="Pending"
    ).count()

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        category_breakdown=category_breakdown,
        monthly_trends=monthly_trends,
        recent_transactions=recent_transactions,
        accounts=accounts,
        selected_account_id=account_id,
        selected_period=period,
        start_date=start_date,
        end_date=end_date,
        pending_anomalies=pending_anomalies,
        pending_subs=pending_subs,
        currency_code=currency_code
    )

