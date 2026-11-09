"""Equipements : liste (recherche/filtres), fiche, creation, modification, suppression, controles."""
import ipaddress

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.exc import IntegrityError

from ..audit import log_action
from ..auth import admin_required
from ..checks import run_check
from ..extensions import db
from ..models import Check, Device, Site

bp = Blueprint("devices", __name__, url_prefix="/devices")

DEVICE_TYPES = ["switch", "router", "firewall", "server"]
CHECK_TYPES = ["icmp", "dns", "tcp"]
PER_PAGE = 20
FIELDS = (
    "hostname", "ip_address", "device_type", "device_role",
    "vendor", "model", "os_version", "description", "site_id",
)
MAX_LEN = {"hostname": 100, "device_role": 50, "vendor": 50, "model": 100, "os_version": 100}


def _parse_form(form):
    """Valide le formulaire. Renvoie (donnees nettoyees, liste d'erreurs)."""
    raw = {k: form.get(k, "").strip() for k in FIELDS}
    errors = []

    for field, limit in MAX_LEN.items():
        if len(raw[field]) > limit:
            errors.append(f"Le champ {field} dépasse {limit} caractères.")
    if not raw["hostname"]:
        errors.append("Le nom (hostname) est obligatoire.")

    try:
        raw["ip_address"] = str(ipaddress.ip_address(raw["ip_address"]))
    except ValueError:
        errors.append("Adresse IP invalide.")

    if raw["device_type"] not in DEVICE_TYPES:
        errors.append("Type d'équipement invalide.")

    site = db.session.get(Site, int(raw["site_id"])) if raw["site_id"].isdigit() else None
    if site is None:
        errors.append("Site invalide.")

    data = {k: (v or None) for k, v in raw.items()}
    data["hostname"] = raw["hostname"]
    data["site_id"] = site.id if site else None
    return data, errors


def _duplicate_errors(data, exclude_id=None):
    errors = []
    for field, label in (("ip_address", "adresse IP"), ("hostname", "nom")):
        stmt = select(Device.id).where(
            Device.site_id == data["site_id"], getattr(Device, field) == data[field]
        )
        if exclude_id:
            stmt = stmt.where(Device.id != exclude_id)
        if db.session.scalar(stmt) is not None:
            errors.append(f"Un équipement avec cette {label} existe déjà sur ce site.")
    return errors


def _render_form(device, data, errors=None):
    for e in errors or []:
        flash(e, "error")
    sites = db.session.scalars(select(Site).order_by(Site.site_name)).all()
    return render_template("devices/form.html", device=device, data=data, sites=sites, types=DEVICE_TYPES)


def _last_checks(device_ids):
    """Dernier controle de chaque equipement de la page (2 requetes, sans N+1)."""
    if not device_ids:
        return {}
    latest = (
        select(Check.device_id, func.max(Check.checked_at).label("m"))
        .where(Check.device_id.in_(device_ids))
        .group_by(Check.device_id)
        .subquery()
    )
    rows = db.session.scalars(
        select(Check).join(latest, and_(Check.device_id == latest.c.device_id, Check.checked_at == latest.c.m))
    )
    return {c.device_id: c for c in rows}


@bp.get("/")
@login_required
def list_devices():
    q = request.args.get("q", "").strip()
    device_type = request.args.get("type", "")
    site_id = request.args.get("site", type=int)
    vendor = request.args.get("vendor", "").strip()
    page = request.args.get("page", 1, type=int)

    stmt = select(Device).order_by(Device.hostname)
    if q:
        stmt = stmt.where(or_(
            Device.hostname.icontains(q, autoescape=True),
            cast(Device.ip_address, String).icontains(q, autoescape=True),
            Device.vendor.icontains(q, autoescape=True),
            Device.model.icontains(q, autoescape=True),
            Device.description.icontains(q, autoescape=True),
        ))
    if device_type in DEVICE_TYPES:
        stmt = stmt.where(Device.device_type == device_type)
    if site_id:
        stmt = stmt.where(Device.site_id == site_id)
    if vendor:
        stmt = stmt.where(Device.vendor == vendor)

    pagination = db.paginate(stmt, page=page, per_page=PER_PAGE, error_out=False)
    vendors = db.session.scalars(
        select(Device.vendor).where(Device.vendor.is_not(None)).distinct().order_by(Device.vendor)
    ).all()
    sites = db.session.scalars(select(Site).order_by(Site.site_name)).all()
    args = {k: v for k, v in {"q": q, "type": device_type, "site": site_id, "vendor": vendor}.items() if v}

    return render_template(
        "devices/list.html", pagination=pagination, devices=pagination.items,
        last_checks=_last_checks([d.id for d in pagination.items]),
        types=DEVICE_TYPES, sites=sites, vendors=vendors, args=args,
        q=q, device_type=device_type, site_id=site_id, vendor=vendor,
    )


@bp.get("/<int:device_id>")
@login_required
def detail(device_id):
    device = db.get_or_404(Device, device_id)
    history = db.session.scalars(
        select(Check).where(Check.device_id == device.id).order_by(Check.checked_at.desc()).limit(20)
    ).all()
    return render_template("devices/detail.html", device=device, history=history, check_types=CHECK_TYPES)


@bp.route("/new", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "GET":
        return _render_form(None, {})
    data, errors = _parse_form(request.form)
    if not errors:
        errors = _duplicate_errors(data)
    if errors:
        return _render_form(None, data, errors)

    device = Device(created_by_id=current_user.id, **data)
    try:
        db.session.add(device)
        db.session.flush()
        log_action("create", "devices", device.id, {"hostname": device.hostname, "ip_address": data["ip_address"]})
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _render_form(None, data, ["Équipement en doublon ou données invalides."])
    flash("Équipement créé.", "success")
    return redirect(url_for("devices.detail", device_id=device.id))


@bp.route("/<int:device_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(device_id):
    device = db.get_or_404(Device, device_id)
    if request.method == "GET":
        return _render_form(device, {k: getattr(device, k) for k in FIELDS})

    data, errors = _parse_form(request.form)
    if not errors:
        errors = _duplicate_errors(data, exclude_id=device.id)
    if errors:
        return _render_form(device, data, errors)

    changes = {}
    for key in FIELDS:
        old, new = getattr(device, key), data[key]
        if (None if old is None else str(old)) != (None if new is None else str(new)):
            changes[key] = {"avant": None if old is None else str(old), "apres": None if new is None else str(new)}
            setattr(device, key, new)
    try:
        if changes:
            log_action("update", "devices", device.id, changes)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _render_form(device, data, ["Équipement en doublon ou données invalides."])
    flash("Équipement modifié.", "success")
    return redirect(url_for("devices.detail", device_id=device.id))


@bp.post("/<int:device_id>/delete")
@admin_required
def delete(device_id):
    device = db.get_or_404(Device, device_id)
    log_action("delete", "devices", device.id, {"hostname": device.hostname, "ip_address": str(device.ip_address)})
    db.session.delete(device)
    db.session.commit()
    flash("Équipement supprimé.", "success")
    return redirect(url_for("devices.list_devices"))


@bp.post("/<int:device_id>/check")
@admin_required
def check(device_id):
    device = db.get_or_404(Device, device_id)
    check_type = request.form.get("check_type", "")
    port = request.form.get("port", "").strip()

    if check_type not in CHECK_TYPES:
        flash("Type de contrôle invalide.", "error")
    elif check_type == "tcp" and not (port.isdigit() and 1 <= int(port) <= 65535):
        flash("Port TCP invalide (1 à 65535).", "error")
    else:
        result = run_check(device, check_type, port=int(port) if check_type == "tcp" else None, user=current_user)
        flash(f"Contrôle {check_type} : {result.result} - {result.message}",
              "success" if result.result == "success" else "error")
    return redirect(url_for("devices.detail", device_id=device.id))
