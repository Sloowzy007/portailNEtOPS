import socket

import pytest

from app.extensions import db
from app.models import AuditLog, Check, Device, Site, User


def make_user(login, role):
    u = User(login=login, email=f"{login}@x.fr", role=role)
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    return u


def logged_client(app, login, role):
    user = make_user(login, role)
    c = app.test_client()
    c.post("/login", data={"login": login, "password": "secret123"})
    c.user_id = user.id
    return c


@pytest.fixture
def admin(app):
    return logged_client(app, "root", "admin")


@pytest.fixture
def user(app):
    return logged_client(app, "alice", "user")


@pytest.fixture
def site(app):
    s = Site(site_name="Cayenne")
    db.session.add(s)
    db.session.commit()
    return s


def add_device(site, hostname="SW-CORE", ip="10.0.0.1", dtype="switch", **kw):
    d = Device(hostname=hostname, ip_address=ip, device_type=dtype, site_id=site.id, **kw)
    db.session.add(d)
    db.session.commit()
    return d


def payload(site, **over):
    data = {"hostname": "SW-01", "ip_address": "10.0.0.10", "device_type": "switch",
            "site_id": site.id, "vendor": "Cisco", "model": "C9300"}
    data.update(over)
    return data


@pytest.fixture
def open_port():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    yield srv.getsockname()[1]
    srv.close()


def test_requires_login(client, site):
    assert client.get("/devices/").status_code == 302
    assert client.get("/sites/").status_code == 302


def test_user_can_read_but_not_write(user, site):
    d = add_device(site)
    assert user.get("/devices/").status_code == 200
    assert user.get(f"/devices/{d.id}").status_code == 200
    assert user.get("/sites/").status_code == 200
    assert user.get("/devices/new").status_code == 403
    assert user.post("/devices/new", data=payload(site)).status_code == 403
    assert user.post(f"/devices/{d.id}/edit", data=payload(site)).status_code == 403
    assert user.post(f"/devices/{d.id}/delete").status_code == 403
    assert user.post(f"/devices/{d.id}/check", data={"check_type": "icmp"}).status_code == 403
    assert user.post("/sites/", data={"site_name": "X"}).status_code == 403
    assert Device.query.count() == 1


def test_admin_creates_device(admin, site):
    r = admin.post("/devices/new", data=payload(site))
    assert r.status_code == 302
    d = Device.query.one()
    assert d.hostname == "SW-01" and d.created_by_id == admin.user_id
    assert AuditLog.query.filter_by(action="create", target_table="devices", target_id=d.id).count() == 1


@pytest.mark.parametrize("over,text", [
    ({"ip_address": "999.1.1.1"}, "Adresse IP invalide"),
    ({"hostname": ""}, "obligatoire"),
    ({"device_type": "toaster"}, "Type d"),
    ({"site_id": "9999"}, "Site invalide"),
])
def test_invalid_input_rejected(admin, site, over, text):
    r = admin.post("/devices/new", data=payload(site, **over))
    assert r.status_code == 200 and text in r.get_data(as_text=True)
    assert Device.query.count() == 0


def test_duplicate_ip_same_site_rejected(admin, site):
    add_device(site, "A", "10.0.0.10")
    r = admin.post("/devices/new", data=payload(site))
    assert "existe déjà" in r.get_data(as_text=True)
    assert Device.query.count() == 1


def test_edit_device_logs_changes(admin, site):
    d = add_device(site, vendor="Cisco")
    r = admin.post(f"/devices/{d.id}/edit", data=payload(site, hostname="SW-CORE", ip_address="10.0.0.1", vendor="HP"))
    assert r.status_code == 302
    assert db.session.get(Device, d.id).vendor == "HP"
    log = AuditLog.query.filter_by(action="update").one()
    assert log.details["vendor"] == {"avant": "Cisco", "apres": "HP"}


def test_edit_can_keep_own_ip(admin, site):
    d = add_device(site)
    r = admin.post(f"/devices/{d.id}/edit", data=payload(site, hostname="SW-CORE", ip_address="10.0.0.1"))
    assert r.status_code == 302


def test_delete_removes_checks_too(admin, site):
    d = add_device(site)
    db.session.add(Check(device_id=d.id, check_type="icmp", result="success"))
    db.session.commit()
    assert admin.post(f"/devices/{d.id}/delete").status_code == 302
    assert Device.query.count() == 0 and Check.query.count() == 0
    assert AuditLog.query.filter_by(action="delete").count() == 1


def test_unknown_device_404(admin):
    assert admin.get("/devices/999").status_code == 404


def test_search_and_filters(user, site):
    add_device(site, "SW-CORE", "10.0.0.1", "switch", vendor="Cisco")
    add_device(site, "FW-EDGE", "10.0.0.2", "firewall", vendor="Fortinet")
    add_device(site, "SRV-WEB", "10.0.0.3", "server", vendor="Dell", description="serveur 100%")

    def names(**params):
        html = user.get("/devices/", query_string=params).get_data(as_text=True)
        return {n for n in ("SW-CORE", "FW-EDGE", "SRV-WEB") if f">{n}<" in html}

    assert names() == {"SW-CORE", "FW-EDGE", "SRV-WEB"}
    assert names(q="core") == {"SW-CORE"}
    assert names(q="10.0.0.2") == {"FW-EDGE"}
    assert names(type="server") == {"SRV-WEB"}
    assert names(vendor="Cisco") == {"SW-CORE"}
    assert names(site=site.id, type="firewall") == {"FW-EDGE"}
    assert names(q="%") == {"SRV-WEB"}  # % traite comme texte, pas comme joker
    assert names(q="zzz") == set()


def test_pagination(user, site):
    for i in range(25):
        add_device(site, f"H{i:02d}", f"10.1.0.{i + 1}")
    assert user.get("/devices/").get_data(as_text=True).count("/devices/") >= 20
    page2 = user.get("/devices/", query_string={"page": 2}).get_data(as_text=True)
    assert ">H24<" in page2 and ">H00<" not in page2


def test_admin_runs_tcp_check(admin, site, open_port):
    d = add_device(site, "LOCAL", "127.0.0.1", "server")
    r = admin.post(f"/devices/{d.id}/check", data={"check_type": "tcp", "port": open_port})
    assert r.status_code == 302
    c = Check.query.one()
    assert c.result == "success" and c.port == open_port and c.user_id == admin.user_id
    assert "success" in admin.get(f"/devices/{d.id}").get_data(as_text=True)
    assert "success" in admin.get("/devices/").get_data(as_text=True)


def test_check_validation(admin, site):
    d = add_device(site)
    admin.post(f"/devices/{d.id}/check", data={"check_type": "tcp", "port": "abc"})
    admin.post(f"/devices/{d.id}/check", data={"check_type": "tcp", "port": "70000"})
    admin.post(f"/devices/{d.id}/check", data={"check_type": "ssh"})
    assert Check.query.count() == 0


def test_sites_create_and_delete(admin, site):
    admin.post("/sites/", data={"site_name": "Kourou", "location": "IUT"})
    kourou = Site.query.filter_by(site_name="Kourou").one()
    admin.post("/sites/", data={"site_name": "Kourou"})  # doublon ignore
    assert Site.query.count() == 2
    add_device(site)
    r = admin.post(f"/sites/{site.id}/delete", follow_redirects=True)
    assert "contient des équipements" in r.get_data(as_text=True) and Site.query.count() == 2
    admin.post(f"/sites/{kourou.id}/delete")
    assert Site.query.count() == 1
