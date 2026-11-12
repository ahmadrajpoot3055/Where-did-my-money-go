from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.accounts import accounts_bp
from app.blueprints.accounts.forms import AccountForm
from app.models.account import FinancialAccount, AccountType
from app.utils.decorators import login_required

def utcnow():
    return datetime.now(timezone.utc)

@accounts_bp.route("")
@login_required
def index():
    user = g.current_user
    accounts = FinancialAccount.query.filter_by(user_id=user.id).order_by(FinancialAccount.is_active.desc(), FinancialAccount.name.asc()).all()
    return render_template("accounts/index.html", accounts=accounts)

@accounts_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = AccountForm()
    form.account_type_id.choices = [(t.id, t.name.title()) for t in AccountType.query.all()]

    if form.validate_on_submit():
        account = FinancialAccount(
            user_id=g.current_user.id,
            account_type_id=form.account_type_id.data,
            name=form.name.data.strip(),
            institution_name=form.institution_name.data.strip() if form.institution_name.data else None,
            currency_code=form.currency_code.data,
            opening_balance=form.opening_balance.data,
            is_active=True,
            created_at=utcnow()
        )
        db.session.add(account)
        db.session.commit()
        flash(f"Account '{account.name}' created successfully.", "success")
        return redirect(url_for("accounts.index"))

    return render_template("accounts/new.html", form=form)

@accounts_bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
@login_required
def edit(account_id):
    account = FinancialAccount.query.get_or_404(account_id)
    if account.user_id != g.current_user.id:
        abort(403)

    form = AccountForm(obj=account)
    form.account_type_id.choices = [(t.id, t.name.title()) for t in AccountType.query.all()]

    if form.validate_on_submit():
        account.name = form.name.data.strip()
        account.account_type_id = form.account_type_id.data
        account.institution_name = form.institution_name.data.strip() if form.institution_name.data else None
        account.currency_code = form.currency_code.data
        account.opening_balance = form.opening_balance.data
        db.session.commit()
        flash(f"Account '{account.name}' updated.", "success")
        return redirect(url_for("accounts.index"))

    return render_template("accounts/edit.html", form=form, account=account)

@accounts_bp.route("/<int:account_id>/archive", methods=["POST"])
@login_required
def archive(account_id):
    account = FinancialAccount.query.get_or_404(account_id)
    if account.user_id != g.current_user.id:
        abort(403)

    account.is_active = not account.is_active
    db.session.commit()
    status_str = "activated" if account.is_active else "archived"
    flash(f"Account '{account.name}' {status_str}.", "info")
    return redirect(url_for("accounts.index"))

