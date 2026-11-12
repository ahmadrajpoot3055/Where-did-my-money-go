import os
from flask import Flask, render_template, session, g
from config import config_by_name
from app.extensions import db, migrate, csrf
from app.models.user import User
from app.models.reporting import Notification

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Ensure required private storage folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["ML_ARTIFACTS_FOLDER"], exist_ok=True)

    # Context processors & template globals
    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        if user_id:
            g.current_user = db.session.get(User, user_id)
        else:
            g.current_user = None

    @app.context_processor
    def inject_global_data():
        unread_count = 0
        if getattr(g, "current_user", None):
            unread_count = Notification.query.filter_by(
                user_id=g.current_user.id,
                is_read=False
            ).count()
        return {
            "current_user": getattr(g, "current_user", None),
            "unread_notification_count": unread_count,
            "app_name": "Where Did My Money Go?"
        }

    # Custom Jinja filters
    @app.template_filter("currency")
    def format_currency(value, code="PKR"):
        try:
            val_f = float(value or 0.0)
            return f"{val_f:,.2f} {code}"
        except (ValueError, TypeError):
            return f"{value} {code}"

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.accounts import accounts_bp
    from app.blueprints.transactions import transactions_bp
    from app.blueprints.imports import imports_bp
    from app.blueprints.budgets import budgets_bp
    from app.blueprints.goals import goals_bp
    from app.blueprints.insights import insights_bp
    from app.blueprints.subscriptions import subscriptions_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(insights_bp)
    app.register_blueprint(subscriptions_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(admin_bp)

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
