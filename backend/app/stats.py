"""Statistiques du tableau de bord.

Etat d'un equipement = resultat de son controle le plus recent (tous types confondus) ;
sans controle, l'etat est "inconnu".
"""
from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from .extensions import db
from .models import Check, Device, Site

RECENT_LIMIT = 10
DOWN_LIMIT = 10


def _latest_check_ids():
    return select(func.max(Check.id)).group_by(Check.device_id).scalar_subquery()


def dashboard_stats():
    latest = _latest_check_ids()

    rows = db.session.execute(
        select(Device.site_id, Device.device_type, Check.result)
        .outerjoin(Check, and_(Check.device_id == Device.id, Check.id.in_(latest)))
    ).all()

    up = sum(1 for r in rows if r.result == "success")
    down = sum(1 for r in rows if r.result == "failure")
    checked = up + down

    by_type, by_site = {}, {}
    for site_id, dtype, result in rows:
        for bucket, key in ((by_type, dtype), (by_site, site_id)):
            total, bad = bucket.get(key, (0, 0))
            bucket[key] = (total + 1, bad + (result == "failure"))

    site_names = dict(db.session.execute(select(Site.id, Site.site_name)).all())

    down_devices = db.session.execute(
        select(Device, Check)
        .join(Check, Check.device_id == Device.id)
        .where(Check.id.in_(latest), Check.result == "failure")
        .order_by(Check.checked_at.desc(), Check.id.desc())
        .limit(DOWN_LIMIT)
    ).all()

    recent = db.session.scalars(
        select(Check)
        .options(joinedload(Check.device), joinedload(Check.user))
        .order_by(Check.checked_at.desc(), Check.id.desc())
        .limit(RECENT_LIMIT)
    ).all()

    return {
        "total": len(rows),
        "up": up,
        "down": down,
        "unknown": len(rows) - checked,
        "availability": round(100 * up / checked, 1) if checked else None,
        "by_type": sorted((t, n, d) for t, (n, d) in by_type.items()),
        "by_site": sorted((site_names.get(s, "?"), n, d) for s, (n, d) in by_site.items()),
        "down_devices": down_devices,
        "recent": recent,
    }
