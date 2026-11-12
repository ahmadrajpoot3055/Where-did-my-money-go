from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.insights import insights_bp
from app.models.intelligence import AnomalyResult, AnalysisRun
from app.models.transaction import Transaction
from app.services.anomaly_service import AnomalyService
from app.utils.decorators import login_required

@insights_bp.route("/anomalies")
@login_required
def anomalies():
    user = g.current_user
    status_filter = request.args.get("status", "New") # New, All, Reviewed

    query = AnomalyResult.query.join(Transaction).filter(
        Transaction.user_id == user.id
    )

    if status_filter != "All":
        if status_filter == "Reviewed":
            query = query.filter(AnomalyResult.status.in_(["Expected", "Incorrect", "FollowUp"]))
        else:
            query = query.filter(AnomalyResult.status == status_filter)

    results = query.order_by(AnomalyResult.created_at.desc()).all()
    runs = AnalysisRun.query.filter_by(user_id=user.id).order_by(AnalysisRun.created_at.desc() if hasattr(AnalysisRun, 'created_at') else AnalysisRun.id.desc()).limit(5).all()

    return render_template(
        "insights/anomalies.html",
        results=results,
        runs=runs,
        selected_status=status_filter
    )

@insights_bp.route("/anomalies/run", methods=["POST"])
@login_required
def trigger_analysis():
    user = g.current_user
    start_str = request.form.get("start_date")
    end_str = request.form.get("end_date")

    today = date.today()
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = today - relativedelta(months=1)
            end_date = today
    else:
        start_date = today - relativedelta(months=1)
        end_date = today

    try:
        run = AnomalyService.run_detection(user.id, start_date, end_date)
        flash("Anomaly analysis completed! Any unusual spending patterns are listed below.", "info")
    except Exception as e:
        flash(f"Analysis failed: {str(e)}", "danger")

    return redirect(url_for("insights.anomalies"))

@insights_bp.route("/anomalies/<int:result_id>/review", methods=["POST"])
@login_required
def review_anomaly(result_id):
    decision = request.form.get("decision", "Expected") # Expected / Incorrect / FollowUp
    comment = request.form.get("comment", "")

    try:
        AnomalyService.record_review(
            result_id=result_id,
            user_id=g.current_user.id,
            decision=decision,
            comment=comment
        )
        flash("Review decision recorded successfully.", "success")
    except Exception as e:
        flash(f"Error recording review: {str(e)}", "danger")

    return redirect(url_for("insights.anomalies"))

