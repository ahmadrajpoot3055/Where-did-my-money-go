import json
from flask import render_template, redirect, url_for, flash, request, g, abort, session
from app.extensions import db
from app.blueprints.imports import imports_bp
from app.blueprints.imports.forms import StatementUploadForm, ColumnMappingForm
from app.models.imports import ImportBatch, ImportMapping, ImportError
from app.models.account import FinancialAccount
from app.services.import_service import ImportService
from app.utils.decorators import login_required

@imports_bp.route("")
@login_required
def index():
    user = g.current_user
    batches = ImportBatch.query.filter_by(user_id=user.id).order_by(ImportBatch.created_at.desc()).all()
    return render_template("imports/index.html", batches=batches)

@imports_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    user = g.current_user
    accounts = FinancialAccount.query.filter_by(user_id=user.id, is_active=True).all()
    if not accounts:
        flash("Please create an account first before uploading a statement.", "warning")
        return redirect(url_for("accounts.new"))

    form = StatementUploadForm()
    form.account_id.choices = [(a.id, f"{a.name} ({a.currency_code})") for a in accounts]

    if form.validate_on_submit():
        account = db.session.get(FinancialAccount, form.account_id.data)
        if not account or account.user_id != user.id:
            flash("Invalid account selected.", "danger")
            return redirect(url_for("imports.new"))

        try:
            batch = ImportService.create_batch_from_upload(
                user_id=user.id,
                account_id=account.id,
                uploaded_file=form.file.data
            )
            flash("Statement uploaded successfully. Please map the file columns.", "success")
            return redirect(url_for("imports.map_columns", batch_id=batch.id))
        except Exception as e:
            flash(f"Upload failed: {str(e)}", "danger")

    return render_template("imports/new.html", form=form)

@imports_bp.route("/<int:batch_id>/map", methods=["GET", "POST"])
@login_required
def map_columns(batch_id):
    batch = ImportBatch.query.get_or_404(batch_id)
    if batch.user_id != g.current_user.id:
        abort(403)

    try:
        df = ImportService.read_file_dataframe(batch)
        columns = list(df.columns)
    except Exception as e:
        flash(f"Error reading file: {str(e)}", "danger")
        return redirect(url_for("imports.index"))

    form = ColumnMappingForm()
    col_choices = [("", "-- Select Column --")] + [(c, c) for c in columns]
    form.date_column.choices = col_choices
    form.description_column.choices = col_choices
    form.amount_column.choices = col_choices
    form.debit_column.choices = col_choices
    form.credit_column.choices = col_choices

    # Smart auto-detection of column headers
    if request.method == "GET":
        for c in columns:
            clow = c.lower()
            if "date" in clow and not form.date_column.data:
                form.date_column.data = c
            elif any(k in clow for k in ["desc", "particular", "narrat", "detail"]) and not form.description_column.data:
                form.description_column.data = c
            elif any(k in clow for k in ["amount", "balance", "net"]) and not form.amount_column.data:
                form.amount_column.data = c
            elif any(k in clow for k in ["debit", "withdrawal", "dr", "spent"]) and not form.debit_column.data:
                form.debit_column.data = c
            elif any(k in clow for k in ["credit", "deposit", "cr", "income"]) and not form.credit_column.data:
                form.credit_column.data = c

    if form.validate_on_submit():
        mapping = {
            "date_column": form.date_column.data,
            "description_column": form.description_column.data,
            "amount_column": form.amount_column.data if form.mapping_type.data == "single" else None,
            "debit_column": form.debit_column.data if form.mapping_type.data == "debit_credit" else None,
            "credit_column": form.credit_column.data if form.mapping_type.data == "debit_credit" else None,
            "date_format": form.date_format.data.strip() if form.date_format.data else None
        }

        # Store in session or execute parse
        try:
            preview_data = ImportService.parse_and_preview(batch, mapping)
            session[f"import_preview_{batch.id}"] = preview_data["all_valid_rows"]
            return redirect(url_for("imports.preview", batch_id=batch.id))
        except Exception as e:
            flash(f"Failed to process statement: {str(e)}", "danger")

    return render_template(
        "imports/map.html",
        form=form,
        batch=batch,
        columns=columns,
        sample_rows=df.head(3).to_dict(orient="records")
    )

@imports_bp.route("/<int:batch_id>/preview")
@login_required
def preview(batch_id):
    batch = ImportBatch.query.get_or_404(batch_id)
    if batch.user_id != g.current_user.id:
        abort(403)

    rows = session.get(f"import_preview_{batch.id}", [])
    errors = ImportError.query.filter_by(batch_id=batch.id).all()

    return render_template(
        "imports/preview.html",
        batch=batch,
        valid_rows=rows,
        errors=errors
    )

@imports_bp.route("/<int:batch_id>/confirm", methods=["POST"])
@login_required
def confirm(batch_id):
    batch = ImportBatch.query.get_or_404(batch_id)
    if batch.user_id != g.current_user.id:
        abort(403)

    rows = session.get(f"import_preview_{batch.id}", [])
    if not rows:
        flash("No parsed rows found in session. Please re-run mapping.", "warning")
        return redirect(url_for("imports.map_columns", batch_id=batch.id))

    try:
        count = ImportService.commit_batch(batch, rows)
        session.pop(f"import_preview_{batch.id}", None)
        flash(f"Successfully imported {count} transactions!", "success")
        return redirect(url_for("imports.summary", batch_id=batch.id))
    except Exception as e:
        flash(f"Import commit failed: {str(e)}", "danger")
        return redirect(url_for("imports.preview", batch_id=batch.id))

@imports_bp.route("/<int:batch_id>")
@login_required
def summary(batch_id):
    batch = ImportBatch.query.get_or_404(batch_id)
    if batch.user_id != g.current_user.id:
        abort(403)

    errors = ImportError.query.filter_by(batch_id=batch.id).all()
    return render_template("imports/summary.html", batch=batch, errors=errors)

