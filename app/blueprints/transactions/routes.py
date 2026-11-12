from datetime import datetime, date, timezone
from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.transactions import transactions_bp
from app.blueprints.transactions.forms import TransactionForm, TransactionSplitForm, TransactionNoteForm
from app.models.transaction import (
    Transaction, TransactionType, TransactionStatus,
    TransactionTag, TransactionNote, TransactionSplit
)
from app.models.account import FinancialAccount
from app.models.category import Category
from app.services.categorization_service import CategorizationService
from app.utils.decorators import login_required
from app.utils.validators import normalize_description

def utcnow():
    return datetime.now(timezone.utc)

@transactions_bp.route("")
@login_required
def index():
    user = g.current_user
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    cat_id = request.args.get("category_id", type=int)
    acc_id = request.args.get("account_id", type=int)
    type_id = request.args.get("type_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    query = Transaction.query.filter_by(user_id=user.id)

    if search:
        query = query.filter(
            (Transaction.description_original.ilike(f"%{search}%")) |
            (Transaction.reference.ilike(f"%{search}%"))
        )
    if cat_id:
        query = query.filter(Transaction.category_id == cat_id)
    if acc_id:
        query = query.filter(Transaction.account_id == acc_id)
    if type_id:
        query = query.filter(Transaction.transaction_type_id == type_id)
    if start_date:
        try:
            d = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date >= d)
        except ValueError:
            pass
    if end_date:
        try:
            d = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Transaction.transaction_date <= d)
        except ValueError:
            pass

    pagination = query.order_by(
        Transaction.transaction_date.desc(),
        Transaction.id.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    accounts = FinancialAccount.query.filter_by(user_id=user.id, is_active=True).all()
    categories = Category.query.filter(
        (Category.user_id == user.id) | (Category.user_id == None),
        Category.is_active == True
    ).order_by(Category.name.asc()).all()
    types = TransactionType.query.all()

    return render_template(
        "transactions/index.html",
        pagination=pagination,
        transactions=pagination.items,
        accounts=accounts,
        categories=categories,
        types=types,
        search=search,
        selected_category_id=cat_id,
        selected_account_id=acc_id,
        selected_type_id=type_id,
        start_date=start_date,
        end_date=end_date
    )

@transactions_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    user = g.current_user
    accounts = FinancialAccount.query.filter_by(user_id=user.id, is_active=True).all()
    if not accounts:
        flash("Please create a financial account first before adding transactions.", "warning")
        return redirect(url_for("accounts.new"))

    form = TransactionForm()
    form.account_id.choices = [(a.id, f"{a.name} ({a.currency_code})") for a in accounts]
    form.transaction_type_id.choices = [(t.id, t.name.title()) for t in TransactionType.query.all()]
    
    categories = Category.query.filter(
        (Category.user_id == user.id) | (Category.user_id == None),
        Category.is_active == True
    ).order_by(Category.name.asc()).all()
    form.category_id.choices = [(0, "-- Auto-categorize / None --")] + [(c.id, f"{c.name} ({c.kind})") for c in categories]

    if request.method == "GET" and not form.transaction_date.data:
        form.transaction_date.data = date.today()

    if form.validate_on_submit():
        account = db.session.get(FinancialAccount, form.account_id.data)
        if not account or account.user_id != user.id:
            flash("Invalid account selected.", "danger")
            return redirect(url_for("transactions.new"))

        desc = form.description.data.strip()
        norm_desc = normalize_description(desc)
        selected_cat_id = form.category_id.data if form.category_id.data != 0 else None

        cat = None
        merchant = None
        confidence = None
        method = "Manual" if selected_cat_id else None

        if selected_cat_id:
            cat = db.session.get(Category, selected_cat_id)
        else:
            cat, merchant, confidence, method = CategorizationService.categorize(desc, user.id)

        completed_status = TransactionStatus.query.filter_by(name="completed").first()

        tx = Transaction(
            user_id=user.id,
            account_id=account.id,
            transaction_type_id=form.transaction_type_id.data,
            transaction_status_id=completed_status.id,
            category_id=cat.id if cat else None,
            merchant_id=merchant.id if merchant else None,
            transaction_date=form.transaction_date.data,
            description_original=desc,
            description_normalized=norm_desc,
            amount=form.amount.data,
            currency_code=account.currency_code,
            reference=form.reference.data.strip() if form.reference.data else None,
            category_confidence=Decimal(str(confidence)) if confidence else None,
            category_method=method,
            is_reviewed=True if selected_cat_id else False,
            created_at=utcnow(),
            updated_at=utcnow()
        )

        # Tags handling
        if form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(",") if t.strip()]
            for t_name in tag_names:
                tag = TransactionTag.query.filter_by(user_id=user.id, name=t_name).first()
                if not tag:
                    tag = TransactionTag(user_id=user.id, name=t_name)
                    db.session.add(tag)
                tx.tags.append(tag)

        # Note handling
        if form.note.data and form.note.data.strip():
            note = TransactionNote(
                transaction=tx,
                user_id=user.id,
                body=form.note.data.strip(),
                created_at=utcnow(),
                updated_at=utcnow()
            )
            db.session.add(note)

        db.session.add(tx)
        db.session.commit()

        flash(f"Transaction recorded successfully. {f'Categorized as {cat.name} ({method})' if cat else ''}", "success")
        return redirect(url_for("transactions.detail", transaction_id=tx.id))

    return render_template("transactions/new.html", form=form)

@transactions_bp.route("/<int:transaction_id>")
@login_required
def detail(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    if tx.user_id != g.current_user.id:
        abort(403)

    split_form = TransactionSplitForm()
    categories = Category.query.filter(
        (Category.user_id == g.current_user.id) | (Category.user_id == None),
        Category.is_active == True
    ).all()
    split_form.category_id.choices = [(c.id, c.name) for c in categories]
    note_form = TransactionNoteForm()

    return render_template(
        "transactions/detail.html",
        tx=tx,
        split_form=split_form,
        note_form=note_form
    )

@transactions_bp.route("/<int:transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    if tx.user_id != g.current_user.id:
        abort(403)

    user = g.current_user
    form = TransactionForm(obj=tx)
    accounts = FinancialAccount.query.filter_by(user_id=user.id, is_active=True).all()
    form.account_id.choices = [(a.id, f"{a.name} ({a.currency_code})") for a in accounts]
    form.transaction_type_id.choices = [(t.id, t.name.title()) for t in TransactionType.query.all()]
    categories = Category.query.filter(
        (Category.user_id == user.id) | (Category.user_id == None),
        Category.is_active == True
    ).order_by(Category.name.asc()).all()
    form.category_id.choices = [(0, "-- Uncategorized --")] + [(c.id, c.name) for c in categories]

    if request.method == "GET":
        form.category_id.data = tx.category_id or 0
        form.tags.data = ", ".join([t.name for t in tx.tags])

    if form.validate_on_submit():
        tx.account_id = form.account_id.data
        tx.transaction_date = form.transaction_date.data
        tx.description_original = form.description.data.strip()
        tx.description_normalized = normalize_description(form.description.data)
        tx.amount = form.amount.data
        tx.transaction_type_id = form.transaction_type_id.data
        tx.reference = form.reference.data.strip() if form.reference.data else None
        
        selected_cat_id = form.category_id.data if form.category_id.data != 0 else None
        if selected_cat_id != tx.category_id:
            tx.category_id = selected_cat_id
            tx.category_method = "Manual"
            tx.is_reviewed = True

        # Update tags
        tx.tags.clear()
        if form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(",") if t.strip()]
            for t_name in tag_names:
                tag = TransactionTag.query.filter_by(user_id=user.id, name=t_name).first()
                if not tag:
                    tag = TransactionTag(user_id=user.id, name=t_name)
                    db.session.add(tag)
                tx.tags.append(tag)

        tx.updated_at = utcnow()
        db.session.commit()
        flash("Transaction updated successfully.", "success")
        return redirect(url_for("transactions.detail", transaction_id=tx.id))

    return render_template("transactions/edit.html", form=form, tx=tx)

@transactions_bp.route("/<int:transaction_id>/delete", methods=["POST"])
@login_required
def delete(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    if tx.user_id != g.current_user.id:
        abort(403)

    db.session.delete(tx)
    db.session.commit()
    flash("Transaction deleted successfully.", "info")
    return redirect(url_for("transactions.index"))

@transactions_bp.route("/<int:transaction_id>/split", methods=["POST"])
@login_required
def add_split(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    if tx.user_id != g.current_user.id:
        abort(403)

    form = TransactionSplitForm()
    categories = Category.query.filter(
        (Category.user_id == g.current_user.id) | (Category.user_id == None),
        Category.is_active == True
    ).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        split = TransactionSplit(
            transaction_id=tx.id,
            category_id=form.category_id.data,
            amount=form.amount.data,
            note=form.note.data.strip() if form.note.data else None
        )
        db.session.add(split)
        db.session.commit()
        flash("Split allocation added.", "success")

    return redirect(url_for("transactions.detail", transaction_id=tx.id))

@transactions_bp.route("/<int:transaction_id>/notes", methods=["POST"])
@login_required
def add_note(transaction_id):
    tx = Transaction.query.get_or_404(transaction_id)
    if tx.user_id != g.current_user.id:
        abort(403)

    form = TransactionNoteForm()
    if form.validate_on_submit():
        note = TransactionNote(
            transaction_id=tx.id,
            user_id=g.current_user.id,
            body=form.body.data.strip(),
            created_at=utcnow(),
            updated_at=utcnow()
        )
        db.session.add(note)
        db.session.commit()
        flash("Note added to transaction.", "success")

    return redirect(url_for("transactions.detail", transaction_id=tx.id))

