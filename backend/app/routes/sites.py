"""Sites : liste, creation et suppression (un site contenant des equipements ne se supprime pas)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..audit import log_action
from ..auth import admin_required
from ..extensions import db
from ..models import Device, Site

bp = Blueprint("sites", __name__, url_prefix="/sites")


@bp.get("/")
@login_required
def list_sites():
    rows = db.session.execute(
        select(Site, func.count(Device.id)).outerjoin(Device).group_by(Site.id).order_by(Site.site_name)
    ).all()
    return render_template("sites.html", rows=rows)


@bp.post("/")
@admin_required
def create():
    name = request.form.get("site_name", "").strip()
    location = request.form.get("location", "").strip() or None
    description = request.form.get("description", "").strip() or None

    if not name or len(name) > 100:
        flash("Le nom du site est obligatoire (100 caractères maximum).", "error")
    elif db.session.scalar(select(Site.id).where(Site.site_name == name)):
        flash("Un site avec ce nom existe déjà.", "error")
    else:
        site = Site(site_name=name, location=location, description=description)
        db.session.add(site)
        db.session.flush()
        log_action("create", "sites", site.id, {"site_name": name})
        db.session.commit()
        flash("Site créé.", "success")
    return redirect(url_for("sites.list_sites"))


@bp.post("/<int:site_id>/delete")
@admin_required
def delete(site_id):
    site = db.get_or_404(Site, site_id)
    if site.devices:
        flash("Impossible de supprimer un site qui contient des équipements.", "error")
        return redirect(url_for("sites.list_sites"))
    try:
        log_action("delete", "sites", site.id, {"site_name": site.site_name})
        db.session.delete(site)
        db.session.commit()
        flash("Site supprimé.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Suppression impossible.", "error")
    return redirect(url_for("sites.list_sites"))
