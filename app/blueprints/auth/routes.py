from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, session, g
from app.extensions import db
from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import RegisterForm, LoginForm, ProfileForm
from app.models import User, Role, UserPreference, NotificationPreference, LoginHistory
from app.utils.security import hash_password, verify_password, hash_ip
from app.utils.decorators import login_required

def utcnow():
    return datetime.now(timezone.utc)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user", description="Standard account holder")
            db.session.add(user_role)
            db.session.flush()

        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            password_hash=hash_password(form.password.data),
            role_id=user_role.id,
            is_active=True,
            created_at=utcnow()
        )
        db.session.add(user)
        db.session.flush()

        # Create default preferences
        pref = UserPreference(
            user_id=user.id,
            currency_code="PKR",
            timezone="Asia/Karachi",
            theme="light",
            week_start=0,
            created_at=utcnow(),
            updated_at=utcnow()
        )
        db.session.add(pref)

        notif_pref = NotificationPreference(
            user_id=user.id,
            budget_alerts=True,
            anomaly_alerts=True,
            subscription_alerts=True,
            email_enabled=False,
            created_at=utcnow()
        )
        db.session.add(notif_pref)

        db.session.commit()
        flash("Registration successful! You can now sign in with your credentials.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        user = User.query.filter(User.email.ilike(email)).first()

        ip = request.remote_addr or ""
        ip_h = hash_ip(ip)
        agent = request.user_agent.string[:255] if request.user_agent else ""

        if user and user.is_active and verify_password(password, user.password_hash):
            session.clear()
            session["user_id"] = user.id
            session["user_name"] = user.full_name
            session["user_role"] = user.role.name if user.role else "user"

            # Record login success
            history = LoginHistory(
                user_id=user.id,
                event_type="Success",
                occurred_at=utcnow(),
                ip_hash=ip_h,
                user_agent=agent
            )
            db.session.add(history)
            db.session.commit()

            flash(f"Welcome back, {user.full_name}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        else:
            if user:
                history = LoginHistory(
                    user_id=user.id,
                    event_type="Failure",
                    occurred_at=utcnow(),
                    ip_hash=ip_h,
                    user_agent=agent
                )
                db.session.add(history)
                db.session.commit()
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    user_id = session.get("user_id")
    if user_id:
        ip = request.remote_addr or ""
        history = LoginHistory(
            user_id=user_id,
            event_type="Logout",
            occurred_at=utcnow(),
            ip_hash=hash_ip(ip),
            user_agent=request.user_agent.string[:255] if request.user_agent else ""
        )
        db.session.add(history)
        db.session.commit()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = g.current_user
    pref = user.preferences
    if not pref:
        pref = UserPreference(user_id=user.id, currency_code="PKR", timezone="Asia/Karachi", theme="light", week_start=0)
        db.session.add(pref)
        db.session.commit()

    form = ProfileForm(
        full_name=user.full_name,
        currency_code=pref.currency_code,
        timezone=pref.timezone,
        theme=pref.theme
    )

    if form.validate_on_submit():
        user.full_name = form.full_name.data.strip()
        pref.currency_code = form.currency_code.data
        pref.timezone = form.timezone.data
        pref.theme = form.theme.data
        pref.updated_at = utcnow()
        db.session.commit()
        session["user_name"] = user.full_name
        flash("Your profile preferences have been updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/profile.html", form=form, user=user)
