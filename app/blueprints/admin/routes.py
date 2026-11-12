from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request
from app.extensions import db
from app.blueprints.admin import admin_bp
from app.blueprints.admin.forms import (
    AdminCategoryForm, AdminSubcategoryForm,
    AdminMerchantForm, AdminMerchantAliasForm,
    AdminCategoryRuleForm
)
from app.models.category import Category, Subcategory, Merchant, MerchantAlias, CategoryRule
from app.models.user import User
from app.models.transaction import Transaction
from app.models.intelligence import AnomalyModel
from app.services.categorization_service import CategorizationService
from app.utils.decorators import admin_required
from app.utils.validators import normalize_description

def utcnow():
    return datetime.now(timezone.utc)

@admin_bp.route("")
@admin_required
def index():
    user_count = User.query.count()
    tx_count = Transaction.query.count()
    cat_count = Category.query.count()
    merch_count = Merchant.query.count()
    alias_count = MerchantAlias.query.count()
    rule_count = CategoryRule.query.count()

    users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template(
        "admin/index.html",
        user_count=user_count,
        tx_count=tx_count,
        cat_count=cat_count,
        merch_count=merch_count,
        alias_count=alias_count,
        rule_count=rule_count,
        users=users
    )

@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    form = AdminCategoryForm()
    sub_form = AdminSubcategoryForm()
    all_categories = Category.query.order_by(Category.kind.asc(), Category.name.asc()).all()
    sub_form.category_id.choices = [(c.id, c.name) for c in all_categories]

    if form.validate_on_submit() and "kind" in request.form:
        name = form.name.data.strip()
        dup = Category.query.filter_by(name=name, user_id=None).first()
        if dup:
            flash(f"Global category '{name}' already exists.", "warning")
        else:
            cat = Category(
                name=name,
                kind=form.kind.data,
                user_id=None, # Global
                is_active=True,
                created_at=utcnow()
            )
            db.session.add(cat)
            db.session.commit()
            flash(f"Category '{cat.name}' created.", "success")
            return redirect(url_for("admin.categories"))

    return render_template("admin/categories.html", categories=all_categories, form=form, sub_form=sub_form)

@admin_bp.route("/subcategories/new", methods=["POST"])
@admin_required
def add_subcategory():
    sub_form = AdminSubcategoryForm()
    all_categories = Category.query.all()
    sub_form.category_id.choices = [(c.id, c.name) for c in all_categories]

    if sub_form.validate_on_submit():
        sub = Subcategory(
            category_id=sub_form.category_id.data,
            name=sub_form.name.data.strip(),
            is_active=True
        )
        db.session.add(sub)
        db.session.commit()
        flash(f"Subcategory '{sub.name}' added.", "success")

    return redirect(url_for("admin.categories"))

@admin_bp.route("/merchants", methods=["GET", "POST"])
@admin_required
def merchants():
    m_form = AdminMerchantForm()
    all_cats = Category.query.order_by(Category.name.asc()).all()
    m_form.default_category_id.choices = [(0, "-- None --")] + [(c.id, c.name) for c in all_cats]

    alias_form = AdminMerchantAliasForm()
    all_merchants = Merchant.query.order_by(Merchant.name.asc()).all()
    alias_form.merchant_id.choices = [(m.id, m.name) for m in all_merchants]

    if m_form.validate_on_submit() and "website" in request.form:
        name = m_form.name.data.strip()
        dup = Merchant.query.filter_by(name=name).first()
        if dup:
            flash(f"Merchant '{name}' already exists.", "warning")
        else:
            cat_id = m_form.default_category_id.data if m_form.default_category_id.data != 0 else None
            merch = Merchant(
                name=name,
                default_category_id=cat_id,
                website=m_form.website.data.strip() if m_form.website.data else None,
                is_active=True
            )
            db.session.add(merch)
            db.session.commit()
            flash(f"Merchant '{merch.name}' created.", "success")
            return redirect(url_for("admin.merchants"))

    return render_template(
        "admin/merchants.html",
        merchants=all_merchants,
        m_form=m_form,
        alias_form=alias_form
    )

@admin_bp.route("/merchants/alias/new", methods=["POST"])
@admin_required
def add_merchant_alias():
    all_merchants = Merchant.query.all()
    alias_form = AdminMerchantAliasForm()
    alias_form.merchant_id.choices = [(m.id, m.name) for m in all_merchants]

    if alias_form.validate_on_submit():
        alias_text = normalize_description(alias_form.alias_text.data)
        alias = MerchantAlias(
            merchant_id=alias_form.merchant_id.data,
            alias_text=alias_text,
            source="Admin",
            created_at=utcnow()
        )
        db.session.add(alias)
        db.session.commit()
        flash(f"Alias '{alias_text}' attached to merchant.", "success")

    return redirect(url_for("admin.merchants"))

@admin_bp.route("/rules", methods=["GET", "POST"])
@admin_required
def rules():
    form = AdminCategoryRuleForm()
    all_cats = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(c.id, c.name) for c in all_cats]

    if form.validate_on_submit():
        rule = CategoryRule(
            user_id=None, # Global rule
            category_id=form.category_id.data,
            pattern=form.pattern.data.strip().upper(),
            match_type=form.match_type.data,
            priority=form.priority.data,
            is_active=True
        )
        db.session.add(rule)
        db.session.commit()
        flash(f"Global categorization rule '{rule.pattern}' added.", "success")
        return redirect(url_for("admin.rules"))

    all_rules = CategoryRule.query.order_by(CategoryRule.priority.desc()).all()
    return render_template("admin/rules.html", rules=all_rules, form=form)

@admin_bp.route("/retrain-ml", methods=["POST"])
@admin_required
def retrain_ml():
    success = CategorizationService.train_baseline_model()
    if success:
        flash("Baseline ML Categorization model retrained and updated successfully!", "success")
    else:
        flash("Model training could not proceed (insufficient training classes).", "warning")
    return redirect(url_for("admin.index"))

