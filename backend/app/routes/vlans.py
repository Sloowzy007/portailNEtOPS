"""VLAN : liste, creation, modification, suppression (un VLAN appartient a un site)."""
import ipaddress

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import contains_eager

from ..audit import log_action
from ..auth import admin_required
from ..extensions import db
from ..models import DeviceVlan, Site, Vlan

bp = Blueprint("vlans", __name__, url_prefix="/vlans")


def _parse(form, fixed_site_id=None, exclude_id=None):
    errors = []

    number_raw = form.get("vlan_number", "").strip()
    number = int(number_raw) if number_raw.isdecimal() else None
    if number is None or not 1 <= number <= 4094:
        errors.append("Le numéro de VLAN doit être compris entre 1 et 4094.")

    name = form.get("vlan_name", "").strip()
    if len(name) > 50:
        errors.append("Le nom du VLAN dépasse 50 caractères.")

    subnet_raw = form.get("subnet", "").strip()
    subnet = None
    if subnet_raw:
        try:
            subnet = str(ipaddress.ip_network(subnet_raw, strict=False))
        except ValueError:
            errors.append("Sous-réseau invalide (exemple : 10.0.10.0/24).")

    if fixed_site_id is not None:
        site = db.session.get(Site, fixed_site_id)
    else:
        site_raw = form.get("site_id", "").strip()
        site = db.session.get(Site, int(site_raw)) if site_raw.isdecimal() else None
    if site is None:
        errors.append("Site invalide.")

    if not errors:
        stmt = select(Vlan.id).where(Vlan.site_id == site.id, Vlan.vlan_number == number)
        if exclude_id:
            stmt = stmt.where(Vlan.id != exclude_id)
        if db.session.scalar(stmt) is not None:
            errors.append(f"Le VLAN {number} existe déjà sur ce site.")

    data = {"vlan_number": number, "vlan_name": name or None, "subnet": subnet, "site_id": site.id if site else None}
    return data, errors


def _render_form(vlan, data, errors=None):
    for e in errors or []:
        flash(e, "error")
    sites = db.session.scalars(select(Site).order_by(Site.site_name)).all()
    return render_template("vlans/form.html", vlan=vlan, data=data, sites=sites)


@bp.get("/")
@login_required
def list_vlans():
    site_id = request.args.get("site", type=int)
    stmt = (
        select(Vlan, func.count(DeviceVlan.id))
        .join(Site, Vlan.site_id == Site.id)
        .outerjoin(DeviceVlan, DeviceVlan.vlan_id == Vlan.id)
        .options(contains_eager(Vlan.site))
        .group_by(Vlan.id, Site.id)
        .order_by(Site.site_name, Vlan.vlan_number)
    )
    if site_id:
        stmt = stmt.where(Vlan.site_id == site_id)
    rows = db.session.execute(stmt).all()
    sites = db.session.scalars(select(Site).order_by(Site.site_name)).all()
    return render_template("vlans.html", rows=rows, sites=sites, site_id=site_id)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "GET":
        return _render_form(None, {"site_id": request.args.get("site", type=int)})
    data, errors = _parse(request.form)
    if errors:
        return _render_form(None, {**data, "vlan_number": request.form.get("vlan_number", "")}, errors)
    vlan = Vlan(**data)
    try:
        db.session.add(vlan)
        db.session.flush()
        log_action("create", "vlans", vlan.id, {"vlan_number": vlan.vlan_number, "site_id": vlan.site_id})
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _render_form(None, data, ["VLAN en doublon ou données invalides."])
    flash("VLAN créé.", "success")
    return redirect(url_for("vlans.list_vlans", site=vlan.site_id))


@bp.route("/<int:vlan_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(vlan_id):
    vlan = db.get_or_404(Vlan, vlan_id)
    if request.method == "GET":
        return _render_form(vlan, {
            "vlan_number": vlan.vlan_number, "vlan_name": vlan.vlan_name,
            "subnet": vlan.subnet, "site_id": vlan.site_id,
        })
    # le site d'un VLAN ne change pas (les equipements associes sont rattaches a ce site)
    data, errors = _parse(request.form, fixed_site_id=vlan.site_id, exclude_id=vlan.id)
    if errors:
        return _render_form(vlan, data, errors)

    changes = {}
    for key in ("vlan_number", "vlan_name", "subnet"):
        old, new = getattr(vlan, key), data[key]
        if (None if old is None else str(old)) != (None if new is None else str(new)):
            changes[key] = {"avant": None if old is None else str(old), "apres": None if new is None else str(new)}
            setattr(vlan, key, new)
    try:
        if changes:
            log_action("update", "vlans", vlan.id, changes)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _render_form(vlan, data, ["VLAN en doublon ou données invalides."])
    flash("VLAN modifié.", "success")
    return redirect(url_for("vlans.list_vlans", site=vlan.site_id))


@bp.post("/<int:vlan_id>/delete")
@admin_required
def delete(vlan_id):
    vlan = db.get_or_404(Vlan, vlan_id)
    site_id = vlan.site_id
    log_action("delete", "vlans", vlan.id, {"vlan_number": vlan.vlan_number, "site_id": site_id})
    db.session.delete(vlan)  # les associations avec les equipements sont supprimees (ON DELETE CASCADE)
    db.session.commit()
    flash("VLAN supprimé.", "success")
    return redirect(url_for("vlans.list_vlans", site=site_id))
