from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects import postgresql
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

# Types PostgreSQL (avec repli en texte pour SQLite, utilise par les tests)
INET = postgresql.INET().with_variant(db.String(45), "sqlite")
CIDR = postgresql.CIDR().with_variant(db.String(45), "sqlite")
JSONType = postgresql.JSONB().with_variant(db.JSON(), "sqlite")


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),)

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_login = db.Column(db.DateTime(timezone=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Site(db.Model):
    __tablename__ = "sites"

    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(200))
    description = db.Column(db.Text)

    vlans = db.relationship("Vlan", back_populates="site", cascade="all, delete-orphan")
    devices = db.relationship("Device", back_populates="site")


class Vlan(db.Model):
    __tablename__ = "vlans"
    __table_args__ = (
        UniqueConstraint("site_id", "vlan_number", name="uq_vlans_site_number"),
        CheckConstraint("vlan_number BETWEEN 1 AND 4094", name="ck_vlans_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    vlan_number = db.Column(db.Integer, nullable=False)
    vlan_name = db.Column(db.String(50))
    subnet = db.Column(CIDR)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)

    site = db.relationship("Site", back_populates="vlans")
    device_links = db.relationship("DeviceVlan", back_populates="vlan", cascade="all, delete-orphan")


class Device(db.Model):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("site_id", "ip_address", name="uq_devices_site_ip"),
        UniqueConstraint("site_id", "hostname", name="uq_devices_site_hostname"),
        CheckConstraint(
            "device_type IN ('switch', 'router', 'firewall', 'server')",
            name="ck_devices_type",
        ),
        Index("ix_devices_device_type", "device_type"),
        Index("ix_devices_vendor", "vendor"),
    )

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(INET, nullable=False)
    device_type = db.Column(db.String(20), nullable=False)
    device_role = db.Column(db.String(50))
    vendor = db.Column(db.String(50))
    model = db.Column(db.String(100))
    os_version = db.Column(db.String(100))
    description = db.Column(db.Text)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    site = db.relationship("Site", back_populates="devices")
    created_by = db.relationship("User")
    vlan_links = db.relationship("DeviceVlan", back_populates="device", cascade="all, delete-orphan")
    checks = db.relationship(
        "Check", back_populates="device", cascade="all, delete-orphan",
        order_by="Check.checked_at.desc()",
    )

    @property
    def last_check(self):
        return self.checks[0] if self.checks else None


class DeviceVlan(db.Model):
    __tablename__ = "devices_vlans"
    __table_args__ = (
        UniqueConstraint("device_id", "vlan_id", name="uq_devices_vlans_pair"),
        # un seul VLAN d'administration par equipement
        Index(
            "uq_devices_vlans_one_management", "device_id", unique=True,
            postgresql_where=db.text("is_management"),
            sqlite_where=db.text("is_management"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    vlan_id = db.Column(db.Integer, db.ForeignKey("vlans.id", ondelete="CASCADE"), nullable=False)
    interface_name = db.Column(db.String(50))
    is_management = db.Column(db.Boolean, nullable=False, default=False)

    device = db.relationship("Device", back_populates="vlan_links")
    vlan = db.relationship("Vlan", back_populates="device_links")


class Check(db.Model):
    __tablename__ = "checks"
    __table_args__ = (
        CheckConstraint("check_type IN ('icmp', 'dns', 'tcp')", name="ck_checks_type"),
        CheckConstraint("result IN ('success', 'failure')", name="ck_checks_result"),
        CheckConstraint("check_type <> 'tcp' OR port IS NOT NULL", name="ck_checks_tcp_port"),
        Index("ix_checks_device_checked_at", "device_id", "checked_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    check_type = db.Column(db.String(10), nullable=False)
    port = db.Column(db.Integer)
    result = db.Column(db.String(10), nullable=False)
    response_time_ms = db.Column(db.Float)
    message = db.Column(db.Text)
    checked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))  # NULL = automatique

    device = db.relationship("Device", back_populates="checks")
    user = db.relationship("User")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_action_at", "action_at"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(30), nullable=False)  # create, update, delete, login...
    target_table = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    details = db.Column(JSONType)  # valeurs avant / apres
    action_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User")
