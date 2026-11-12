import json
from datetime import date
from pathlib import Path
from dateutil.relativedelta import relativedelta
from flask import render_template, redirect, url_for, flash, request, g, abort, send_from_directory, current_app
from app.extensions import db
from app.blueprints.reports import reports_bp
from app.blueprints.reports.forms import ReportForm
from app.models.reporting import Report
from app.services.report_service import ReportService
from app.utils.decorators import login_required

@reports_bp.route("")
@login_required
def index():
    user = g.current_user
    reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    return render_template("reports/index.html", reports=reports)

@reports_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = ReportForm()
    if request.method == "GET" and not form.period_start.data:
        today = date.today()
        form.period_start.data = date(today.year, today.month, 1)
        next_m = form.period_start.data + relativedelta(months=1)
        form.period_end.data = next_m - relativedelta(days=1)

    if form.validate_on_submit():
        if form.period_end.data < form.period_start.data:
            flash("End date cannot precede start date.", "danger")
            return render_template("reports/new.html", form=form)

        try:
            report = ReportService.generate_financial_report(
                user_id=g.current_user.id,
                title=form.title.data.strip(),
                start_date=form.period_start.data,
                end_date=form.period_end.data,
                report_format=form.format.data,
                currency_code=form.currency_code.data
            )
            flash("Financial report generated successfully!", "success")
            return redirect(url_for("reports.view", report_id=report.id))
        except Exception as e:
            flash(f"Failed to generate report: {str(e)}", "danger")

    return render_template("reports/new.html", form=form)

@reports_bp.route("/<int:report_id>")
@login_required
def view(report_id):
    report = Report.query.get_or_404(report_id)
    if report.user_id != g.current_user.id:
        abort(403)

    sections_data = []
    for s in report.sections:
        try:
            content = json.loads(s.content_json)
        except Exception:
            content = s.content_json
        sections_data.append({
            "key": s.section_key,
            "title": s.title,
            "content": content
        })

    return render_template("reports/view.html", report=report, sections=sections_data)

@reports_bp.route("/<int:report_id>/download")
@login_required
def download(report_id):
    report = Report.query.get_or_404(report_id)
    if report.user_id != g.current_user.id:
        abort(403)

    if not report.file_path:
        flash("No generated download file found for this report.", "warning")
        return redirect(url_for("reports.view", report_id=report.id))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    return send_from_directory(
        directory=upload_dir,
        path=report.file_path,
        as_attachment=True,
        download_name=f"Report_{report.title.replace(' ', '_')}.csv"
    )

