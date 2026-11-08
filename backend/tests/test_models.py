import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Device, Site, User


def test_health(client):
    assert client.get("/health").json == {"status": "ok"}


def test_password_is_hashed():
    u = User(login="a", email="a@x.fr", role="user")
    u.set_password("secret")
    assert u.password_hash != "secret"
    assert u.check_password("secret")
    assert not u.check_password("autre")


def test_invalid_role_rejected(app):
    db.session.add(User(login="a", email="a@x.fr", password_hash="x", role="root"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_same_hostname_allowed_on_two_sites(app):
    s1, s2 = Site(site_name="Cayenne"), Site(site_name="Kourou")
    db.session.add_all([s1, s2])
    db.session.flush()
    db.session.add_all([
        Device(hostname="SW-CORE", ip_address="10.0.0.1", device_type="switch", site_id=s1.id),
        Device(hostname="SW-CORE", ip_address="10.0.1.1", device_type="switch", site_id=s2.id),
    ])
    db.session.commit()
    assert Device.query.count() == 2


def test_duplicate_ip_same_site_rejected(app):
    s = Site(site_name="Cayenne")
    db.session.add(s)
    db.session.flush()
    db.session.add_all([
        Device(hostname="A", ip_address="10.0.0.1", device_type="switch", site_id=s.id),
        Device(hostname="B", ip_address="10.0.0.1", device_type="router", site_id=s.id),
    ])
    with pytest.raises(IntegrityError):
        db.session.commit()
