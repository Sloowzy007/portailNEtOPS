"""Journal d'audit : qui a fait quoi (l'appelant fait le commit)."""
from flask_login import current_user

from .extensions import db
from .models import AuditLog


def log_action(action, table, target_id, details=None):
    user_id = current_user.id if current_user.is_authenticated else None
    db.session.add(
        AuditLog(user_id=user_id, action=action, target_table=table, target_id=target_id, details=details)
    )
