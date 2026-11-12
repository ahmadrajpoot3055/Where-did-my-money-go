from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, g

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        
        # Ensure g.current_user is set
        if not getattr(g, "current_user", None):
            from app.extensions import db
            from app.models.user import User
            user = db.session.get(User, user_id)
            if not user or not user.is_active:
                session.clear()
                flash("Your account is disabled or does not exist.", "danger")
                return redirect(url_for("auth.login"))
            g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        
        if not getattr(g, "current_user", None):
            from app.extensions import db
            from app.models.user import User
            user = db.session.get(User, user_id)
            if not user or not user.is_active:
                session.clear()
                flash("Your account is disabled or does not exist.", "danger")
                return redirect(url_for("auth.login"))
            g.current_user = user
            
        if not g.current_user.role or g.current_user.role.name.lower() != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
