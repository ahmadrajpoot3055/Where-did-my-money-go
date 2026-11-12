from datetime import date, datetime, timezone
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.budgets import budgets_bp
from app.blueprints.budgets.forms import BudgetForm, BudgetItemForm
from app.models.budget import Budget, BudgetItem, BudgetAlert
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.reporting import Notification
from app.utils.decorators import login_required

def utcnow():
    return datetime.now(timezone.utc)

@budgets_bp.route("")
@login_required
def index():
    user = g.current_user
    budgets = Budget.query.filter_by(user_id=user.id).order_by(Budget.is_active.desc(), Budget.start_date.desc()).all()

    completed_status = TransactionStatus.query.filter_by(name="completed").first()
    expense_type = TransactionType.query.filter_by(name="expense").first()
    status_id = completed_status.id if completed_status else 1
    expense_id = expense_type.id if expense_type else 2

    budget_data = []
    for b in budgets:
        total_limit = Decimal("0.00")
        total_spent = Decimal("0.00")
        item_details = []

        for item in b.items:
            total_limit += item.limit_amount
            # Calculate actual spending for this category in budget period
            txs = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.transaction_status_id == status_id,
                Transaction.transaction_type_id == expense_id,
                Transaction.category_id == item.category_id,
                Transaction.currency_code == b.currency_code,
                Transaction.transaction_date >= b.start_date,
                Transaction.transaction_date <= b.end_date
            ).all()

            spent = sum((t.amount for t in txs), Decimal("0.00"))
            total_spent += spent

            pct = round((float(spent) / float(item.limit_amount) * 100), 1) if item.limit_amount > 0 else 0
            remaining = item.limit_amount - spent

            # Alert threshold check
            if pct >= float(item.warning_percent):
                existing_alert = BudgetAlert.query.filter_by(
                    budget_item_id=item.id,
                    threshold_percent=item.warning_percent
                ).first()

                if not existing_alert:
                    alert = BudgetAlert(
                        budget_item_id=item.id,
                        threshold_percent=item.warning_percent,
                        actual_percent=Decimal(str(pct)),
                        message=f"{item.category.name} spending reached {pct}% of your limit ({spent:,.2f}/{item.limit_amount:,.2f} {b.currency_code})",
                        created_at=utcnow(),
                        is_read=False
                    )
                    db.session.add(alert)
                    notif = Notification(
                        user_id=user.id,
                        notification_type="BudgetAlert",
                        title=f"Budget Alert: {item.category.name}",
                        body=alert.message,
                        target_url=f"/budgets/{b.id}"
                    )
                    db.session.add(notif)
                    db.session.commit()

            item_details.append({
                "item": item,
                "spent": float(spent),
                "remaining": float(remaining),
                "percent": pct
            })

        overall_pct = round((float(total_spent) / float(total_limit) * 100), 1) if total_limit > 0 else 0
        budget_data.append({
            "budget": b,
            "total_limit": float(total_limit),
            "total_spent": float(total_spent),
            "remaining": float(total_limit - total_spent),
            "overall_pct": overall_pct,
            "items": item_details
        })

    return render_template("budgets/index.html", budget_data=budget_data)

@budgets_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = BudgetForm()
    if request.method == "GET" and not form.start_date.data:
        today = date.today()
        form.start_date.data = date(today.year, today.month, 1)
        next_m = form.start_date.data + relativedelta(months=1)
        form.end_date.data = next_m - relativedelta(days=1)

    if form.validate_on_submit():
        if form.end_date.data < form.start_date.data:
            flash("End date must not precede start date.", "danger")
            return render_template("budgets/new.html", form=form)

        budget = Budget(
            user_id=g.current_user.id,
            name=form.name.data.strip(),
            period_type=form.period_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            currency_code=form.currency_code.data,
            is_active=True
        )
        db.session.add(budget)
        db.session.commit()
        flash("Budget created! Now add category limits below.", "success")
        return redirect(url_for("budgets.detail", budget_id=budget.id))

    return render_template("budgets/new.html", form=form)

@budgets_bp.route("/<int:budget_id>")
@login_required
def detail(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != g.current_user.id:
        abort(403)

    item_form = BudgetItemForm()
    # Categories excluding already assigned
    existing_cat_ids = [it.category_id for it in budget.items]
    categories = Category.query.filter(
        (Category.user_id == g.current_user.id) | (Category.user_id == None),
        Category.is_active == True,
        ~Category.id.in_(existing_cat_ids) if existing_cat_ids else True
    ).order_by(Category.name.asc()).all()

    item_form.category_id.choices = [(c.id, c.name) for c in categories]

    return render_template("budgets/detail.html", budget=budget, item_form=item_form, available_categories=categories)

@budgets_bp.route("/<int:budget_id>/items/new", methods=["POST"])
@login_required
def add_item(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != g.current_user.id:
        abort(403)

    form = BudgetItemForm()
    categories = Category.query.all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        # Prevent duplicate category within same budget
        dup = BudgetItem.query.filter_by(budget_id=budget.id, category_id=form.category_id.data).first()
        if dup:
            flash("This category is already included in this budget.", "warning")
        else:
            item = BudgetItem(
                budget_id=budget.id,
                category_id=form.category_id.data,
                limit_amount=form.limit_amount.data,
                warning_percent=form.warning_percent.data
            )
            db.session.add(item)
            db.session.commit()
            flash("Budget category limit added.", "success")

    return redirect(url_for("budgets.detail", budget_id=budget.id))

@budgets_bp.route("/<int:budget_id>/archive", methods=["POST"])
@login_required
def archive(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != g.current_user.id:
        abort(403)

    budget.is_active = not budget.is_active
    db.session.commit()
    flash(f"Budget '{budget.name}' status updated.", "info")
    return redirect(url_for("budgets.index"))

