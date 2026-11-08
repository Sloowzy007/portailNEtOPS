"""Authentification : login, logout et controle des roles (admin / user)."""
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import AuditLog, User, utcnow

bp = Blueprint("auth", __name__)


def admin_required(view):
    """Reserve une route aux administrateurs (401 -> login, 403 si simple utilisateur)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def _is_safe_next(target):
    """N'accepte que les chemins internes (evite la redirection vers un site externe)."""
    if not target or "\\" in target:
        return False
    parts = urlsplit(target)
    return target.startswith("/") and not target.startswith("//") and not parts.scheme and not parts.netloc


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(login=login_value).first()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            user.last_login = utcnow()
            db.session.add(AuditLog(user_id=user.id, action="login", target_table="users", target_id=user.id))
            db.session.commit()
            target = request.args.get("next")
            return redirect(target if _is_safe_next(target) else url_for("main.index"))

        # message volontairement identique : ne revele pas si le compte existe
        db.session.add(AuditLog(action="login_failed", target_table="users", details={"login": login_value[:50]}))
        db.session.commit()
        flash("Identifiant ou mot de passe incorrect.", "error")

    return render_template("login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
