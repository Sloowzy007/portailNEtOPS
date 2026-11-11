from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from ..stats import dashboard_stats

bp = Blueprint("main", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.get("/")
@login_required
def index():
    return render_template("dashboard.html", stats=dashboard_stats())
