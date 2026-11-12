from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.subscriptions import subscriptions_bp
from app.blueprints.subscriptions.forms import SubscriptionForm
from app.models.subscription import Subscription, SubscriptionDetection
from app.services.subscription_service import SubscriptionService
from app.utils.decorators import login_required

@subscriptions_bp.route("")
@login_required
def index():
    user = g.current_user
    active_subs = Subscription.query.filter_by(user_id=user.id, status="Active").order_by(Subscription.name.asc()).all()
    cancelled_subs = Subscription.query.filter_by(user_id=user.id, status="Cancelled").all()
    detections = SubscriptionDetection.query.filter_by(user_id=user.id, status="Pending").order_by(SubscriptionDetection.created_at.desc()).all()

    total_monthly_est = sum(
        (float(s.expected_amount) * (4.33 if s.frequency == "Weekly" else (1.0 if s.frequency == "Monthly" else 1.0/12.0)))
        for s in active_subs
    )

    return render_template(
        "subscriptions/index.html",
        active_subs=active_subs,
        cancelled_subs=cancelled_subs,
        detections=detections,
        total_monthly_est=round(total_monthly_est, 2)
    )

@subscriptions_bp.route("/scan", methods=["POST"])
@login_required
def scan():
    user = g.current_user
    new_items = SubscriptionService.detect_recurring_candidates(user.id)
    if new_items:
        flash(f"Scan complete! Discovered {len(new_items)} recurring candidate(s) for your review.", "success")
    else:
        flash("Scan complete. No new recurring subscriptions identified.", "info")
    return redirect(url_for("subscriptions.index"))

@subscriptions_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = SubscriptionForm()
    if form.validate_on_submit():
        sub = Subscription(
            user_id=g.current_user.id,
            name=form.name.data.strip(),
            expected_amount=form.expected_amount.data,
            currency_code=form.currency_code.data,
            frequency=form.frequency.data,
            next_expected_date=form.next_expected_date.data,
            status="Active"
        )
        db.session.add(sub)
        db.session.commit()
        flash(f"Subscription '{sub.name}' added successfully.", "success")
        return redirect(url_for("subscriptions.index"))

    return render_template("subscriptions/new.html", form=form)

@subscriptions_bp.route("/detections/<int:id>/confirm", methods=["POST"])
@login_required
def confirm_detection(id):
    try:
        sub = SubscriptionService.confirm_detection(id, g.current_user.id)
        flash(f"Confirmed recurring subscription: '{sub.name}'.", "success")
    except Exception as e:
        flash(f"Failed to confirm: {str(e)}", "danger")

    return redirect(url_for("subscriptions.index"))

@subscriptions_bp.route("/detections/<int:id>/reject", methods=["POST"])
@login_required
def reject_detection(id):
    try:
        SubscriptionService.reject_detection(id, g.current_user.id)
        flash("Candidate dismissed.", "info")
    except Exception as e:
        flash(f"Failed to reject: {str(e)}", "danger")

    return redirect(url_for("subscriptions.index"))

@subscriptions_bp.route("/<int:id>/cancel", methods=["POST"])
@login_required
def cancel(id):
    sub = Subscription.query.get_or_404(id)
    if sub.user_id != g.current_user.id:
        abort(403)

    sub.status = "Cancelled" if sub.status == "Active" else "Active"
    db.session.commit()
    flash(f"Subscription status set to {sub.status}.", "info")
    return redirect(url_for("subscriptions.index"))

