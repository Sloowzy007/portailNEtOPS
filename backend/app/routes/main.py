from flask import Blueprint, jsonify, render_template
from flask_login import login_required

bp = Blueprint("main", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.get("/")
@login_required
def index():
    # TODO : tableau de bord synthetique (milestone 3)
    return render_template("dashboard.html")
