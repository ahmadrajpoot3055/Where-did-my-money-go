from datetime import date, datetime, timezone
from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.goals import goals_bp
from app.blueprints.goals.forms import SavingsGoalForm, SavingsContributionForm
from app.models.budget import SavingsGoal, SavingsContribution
from app.utils.decorators import login_required

def utcnow():
    return datetime.now(timezone.utc)

@goals_bp.route("")
@login_required
def index():
    user = g.current_user
    goals = SavingsGoal.query.filter_by(user_id=user.id).order_by(SavingsGoal.status.asc(), SavingsGoal.created_at.desc()).all()
    contrib_form = SavingsContributionForm()
    if not contrib_form.contribution_date.data:
        contrib_form.contribution_date.data = date.today()

    return render_template("goals/index.html", goals=goals, contrib_form=contrib_form)

@goals_bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    form = SavingsGoalForm()
    if form.validate_on_submit():
        goal = SavingsGoal(
            user_id=g.current_user.id,
            name=form.name.data.strip(),
            target_amount=form.target_amount.data,
            target_date=form.target_date.data,
            currency_code=form.currency_code.data,
            status="Active",
            created_at=utcnow()
        )
        db.session.add(goal)
        db.session.commit()
        flash(f"Savings goal '{goal.name}' created!", "success")
        return redirect(url_for("goals.index"))

    return render_template("goals/new.html", form=form)

@goals_bp.route("/<int:goal_id>/contribute", methods=["POST"])
@login_required
def contribute(goal_id):
    goal = SavingsGoal.query.get_or_404(goal_id)
    if goal.user_id != g.current_user.id:
        abort(403)

    form = SavingsContributionForm()
    if form.validate_on_submit():
        contrib = SavingsContribution(
            goal_id=goal.id,
            amount=form.amount.data,
            contribution_date=form.contribution_date.data,
            note=form.note.data.strip() if form.note.data else None
        )
        db.session.add(contrib)
        
        # Check if goal target reached
        if goal.current_saved + float(form.amount.data) >= float(goal.target_amount):
            goal.status = "Completed"
            flash(f"Congratulations! You reached your savings target for '{goal.name}'!", "success")
        else:
            flash(f"Contribution of {form.amount.data} {goal.currency_code} recorded.", "success")
            
        db.session.commit()
    else:
        flash("Invalid contribution amount or date.", "danger")

    return redirect(url_for("goals.index"))

