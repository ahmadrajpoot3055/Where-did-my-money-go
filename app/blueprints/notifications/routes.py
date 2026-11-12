from flask import render_template, redirect, url_for, flash, request, g, abort
from app.extensions import db
from app.blueprints.notifications import notifications_bp
from app.models.reporting import Notification
from app.utils.decorators import login_required

@notifications_bp.route("")
@login_required
def index():
    user = g.current_user
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    unread_count = sum(1 for n in notifications if not n.is_read)
    return render_template("notifications/index.html", notifications=notifications, unread_count=unread_count)

@notifications_bp.route("/<int:id>/read", methods=["POST"])
@login_required
def mark_read(id):
    notif = Notification.query.get_or_404(id)
    if notif.user_id != g.current_user.id:
        abort(403)

    notif.is_read = True
    db.session.commit()
    target = request.args.get("next") or url_for("notifications.index")
    return redirect(target)

@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    user = g.current_user
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "info")
    return redirect(url_for("notifications.index"))

