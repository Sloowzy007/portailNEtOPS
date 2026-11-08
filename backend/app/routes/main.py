from flask import Blueprint, jsonify

bp = Blueprint("main", __name__)


@bp.get("/health")
def health():
    return jsonify(status="ok")


# TODO : login, logout, dashboard, CRUD equipements (milestone 2)
@bp.get("/login")
def login():
    return "Page de connexion (a faire)", 200
