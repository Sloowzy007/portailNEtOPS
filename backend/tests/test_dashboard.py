import pytest

from app.extensions import db
from app.models import Check, Device, Site, User
from app.stats import dashboard_stats


def logged_client(app, login="alice", role="user"):
    u = User(login=login, email=f"{login}@x.fr", role=role)
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    c = app.test_client()
    c.post("/login", data={"login": login, "password": "secret123"})
    return c


def add_device(site, hostname, ip, dtype="switch"):
    d = Device(hostname=hostname, ip_address=ip, device_type=dtype, site_id=site.id)
    db.session.add(d)
    db.session.commit()
    return d


def add_check(device, result, check_type="icmp"):
    c = Check(device_id=device.id, check_type=check_type, result=result, message=f"msg-{result}")
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def sites(app):
    a, b = Site(site_name="Cayenne"), Site(site_name="Kourou")
    db.session.add_all([a, b])
    db.session.commit()
    return a, b


def test_dashboard_requires_login(client):
    assert client.get("/").status_code == 302


def test_empty_dashboard(app):
    stats = dashboard_stats()
    assert stats["total"] == 0 and stats["availability"] is None
    r = logged_client(app).get("/")
    assert r.status_code == 200 and "Aucun équipement pour le moment" in r.get_data(as_text=True)


def test_stats_use_latest_check(app, sites):
    cay, kou = sites
    d1 = add_device(cay, "SW-1", "10.0.0.1", "switch")
    d2 = add_device(cay, "FW-1", "10.0.0.2", "firewall")
    d3 = add_device(kou, "SRV-1", "10.0.1.1", "server")
    add_check(d1, "failure")
    add_check(d1, "success")   # le plus recent : d1 est en ligne
    add_check(d2, "success")
    add_check(d2, "failure")   # le plus recent : d2 est hors ligne
    # d3 : jamais controle

    s = dashboard_stats()
    assert (s["total"], s["up"], s["down"], s["unknown"]) == (3, 1, 1, 1)
    assert s["availability"] == 50.0
    assert s["by_site"] == [("Cayenne", 2, 1), ("Kourou", 1, 0)]
    assert s["by_type"] == [("firewall", 1, 1), ("server", 1, 0), ("switch", 1, 0)]
    assert [d.hostname for d, _ in s["down_devices"]] == ["FW-1"]
    assert len(s["recent"]) == 4 and s["recent"][0].device_id == d2.id


def test_dashboard_page_content(app, sites):
    cay, _ = sites
    d = add_device(cay, "FW-EDGE", "10.0.0.2", "firewall")
    add_check(d, "failure")
    html = logged_client(app).get("/").get_data(as_text=True)
    assert "FW-EDGE" in html and "Hors ligne" in html and "msg-failure" in html
    assert "0.0 %" in html


def test_recent_is_limited(app, sites):
    d = add_device(sites[0], "SW-1", "10.0.0.1")
    for _ in range(15):
        add_check(d, "success")
    assert len(dashboard_stats()["recent"]) == 10
