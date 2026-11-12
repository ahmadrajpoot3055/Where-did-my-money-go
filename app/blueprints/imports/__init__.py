from flask import Blueprint

imports_bp = Blueprint("imports", __name__, url_prefix="/imports")

from app.blueprints.imports import routes

