import pytest

from app.extensions import db
from app.models import AuditLog, Device, DeviceVlan, Site, User, Vlan


def logged_client(app, login, role):
    u = User(login=login, email=f"{login}@x.fr", role=role)
    u.set_password("secret123")
    db.session.add(u)
    db.session.commit()
    c = app.test_client()
    c.post("/login", data={"login": login, "password": "secret123"})
    return c


@pytest.fixture
def admin(app):
    return logged_client(app, "root", "admin")


@pytest.fixture
def user(app):
    return logged_client(app, "alice", "user")


@pytest.fixture
def sites(app):
    a, b = Site(site_name="Cayenne"), Site(site_name="Kourou")
    db.session.add_all([a, b])
    db.session.commit()
    return a, b


def add_vlan(site, number=10, name="MGMT", subnet=None):
    v = Vlan(site_id=site.id, vlan_number=number, vlan_name=name, subnet=subnet)
    db.session.add(v)
    db.session.commit()
    return v


def add_device(site, hostname="SW-1", ip="10.0.0.1"):
    d = Device(hostname=hostname, ip_address=ip, device_type="switch", site_id=site.id)
    db.session.add(d)
    db.session.commit()
    return d


def link(device, vlan, mgmt=False, iface=None):
    l = DeviceVlan(device_id=device.id, vlan_id=vlan.id, is_management=mgmt, interface_name=iface)
    db.session.add(l)
    db.session.commit()
    return l


def vlan_data(site, **over):
    d = {"site_id": site.id, "vlan_number": "10", "vlan_name": "MGMT", "subnet": "10.0.10.0/24"}
    d.update(over)
    return d


def mgmt_numbers(device):
    db.session.expire_all()
    return sorted(l.vlan.vlan_number for l in DeviceVlan.query.filter_by(device_id=device.id, is_management=True))


# ---------- gestion des VLAN ----------

def test_user_read_only(user, sites):
    v = add_vlan(sites[0])
    assert user.get("/vlans/").status_code == 200
    assert user.get("/vlans/new").status_code == 403
    assert user.post("/vlans/new", data=vlan_data(sites[0], vlan_number="20")).status_code == 403
    assert user.post(f"/vlans/{v.id}/edit", data=vlan_data(sites[0])).status_code == 403
    assert user.post(f"/vlans/{v.id}/delete").status_code == 403
    assert Vlan.query.count() == 1


def test_anonymous_redirected(client):
    assert client.get("/vlans/").status_code == 302


def test_admin_creates_vlan_and_normalizes_subnet(admin, sites):
    r = admin.post("/vlans/new", data=vlan_data(sites[0], subnet="10.0.10.5/24"))
    assert r.status_code == 302
    v = Vlan.query.one()
    assert v.vlan_number == 10 and str(v.subnet) == "10.0.10.0/24"
    assert AuditLog.query.filter_by(action="create", target_table="vlans").count() == 1


@pytest.mark.parametrize("over,text", [
    ({"vlan_number": "0"}, "entre 1 et 4094"),
    ({"vlan_number": "4095"}, "entre 1 et 4094"),
    ({"vlan_number": "abc"}, "entre 1 et 4094"),
    ({"vlan_number": "²"}, "entre 1 et 4094"),
    ({"subnet": "pas-un-reseau"}, "Sous-réseau invalide"),
    ({"site_id": "999"}, "Site invalide"),
    ({"vlan_name": "x" * 51}, "dépasse 50"),
])
def test_invalid_vlan_rejected(admin, sites, over, text):
    r = admin.post("/vlans/new", data=vlan_data(sites[0], **over))
    assert r.status_code == 200 and text in r.get_data(as_text=True)
    assert Vlan.query.count() == 0


def test_same_number_ok_on_other_site_but_not_same_site(admin, sites):
    cay, kou = sites
    admin.post("/vlans/new", data=vlan_data(cay))
    r = admin.post("/vlans/new", data=vlan_data(cay, subnet=""))
    assert "existe déjà" in r.get_data(as_text=True)
    assert admin.post("/vlans/new", data=vlan_data(kou)).status_code == 302
    assert Vlan.query.count() == 2


def test_edit_vlan_keeps_site(admin, sites):
    cay, kou = sites
    v = add_vlan(cay)
    r = admin.post(f"/vlans/{v.id}/edit", data=vlan_data(kou, vlan_name="VOIX", vlan_number="10"))
    assert r.status_code == 302
    v = db.session.get(Vlan, v.id)
    assert v.vlan_name == "VOIX" and v.site_id == cay.id
    assert AuditLog.query.filter_by(action="update", target_table="vlans").one().details["vlan_name"] == {
        "avant": "MGMT", "apres": "VOIX"}


def test_delete_vlan_removes_device_links(admin, sites):
    v = add_vlan(sites[0])
    d = add_device(sites[0])
    link(d, v)
    assert admin.post(f"/vlans/{v.id}/delete").status_code == 302
    assert Vlan.query.count() == 0 and DeviceVlan.query.count() == 0 and Device.query.count() == 1


def test_list_filter_by_site(user, sites):
    add_vlan(sites[0], 10)
    add_vlan(sites[1], 99, "AUTRE")
    html = user.get("/vlans/", query_string={"site": sites[0].id}).get_data(as_text=True)
    assert "MGMT" in html and "AUTRE" not in html


# ---------- VLAN d'un équipement ----------

def test_add_vlan_to_device(admin, sites):
    v, d = add_vlan(sites[0]), add_device(sites[0])
    r = admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v.id, "interface_name": "Gi0/1", "is_management": "on"})
    assert r.status_code == 302
    l = DeviceVlan.query.one()
    assert l.interface_name == "Gi0/1" and l.is_management
    assert AuditLog.query.filter_by(action="update", target_table="devices").one().details == {"vlan": {"ajoute": 10}}
    assert "Gi0/1" in admin.get(f"/devices/{d.id}").get_data(as_text=True)


def test_cannot_add_vlan_from_other_site_or_twice(admin, sites):
    v_cay, v_kou = add_vlan(sites[0], 10), add_vlan(sites[1], 20)
    d = add_device(sites[0])
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v_kou.id})
    assert DeviceVlan.query.count() == 0
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v_cay.id})
    r = admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v_cay.id}, follow_redirects=True)
    assert "déjà dans ce VLAN" in r.get_data(as_text=True) and DeviceVlan.query.count() == 1
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": "abc"})
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": "²"})
    assert DeviceVlan.query.count() == 1


def test_interface_name_too_long(admin, sites):
    v, d = add_vlan(sites[0]), add_device(sites[0])
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v.id, "interface_name": "x" * 51})
    assert DeviceVlan.query.count() == 0


def test_only_one_management_vlan(admin, sites):
    v10, v20 = add_vlan(sites[0], 10), add_vlan(sites[0], 20)
    d = add_device(sites[0])
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v10.id, "is_management": "on"})
    assert mgmt_numbers(d) == [10]
    admin.post(f"/devices/{d.id}/vlans", data={"vlan_id": v20.id, "is_management": "on"})
    assert mgmt_numbers(d) == [20]
    l10 = DeviceVlan.query.filter_by(vlan_id=v10.id).one()
    assert admin.post(f"/devices/{d.id}/vlans/{l10.id}/management").status_code == 302
    assert mgmt_numbers(d) == [10]


def test_remove_vlan_from_device(admin, sites):
    v, d = add_vlan(sites[0]), add_device(sites[0])
    l = link(d, v)
    assert admin.post(f"/devices/{d.id}/vlans/{l.id}/delete").status_code == 302
    assert DeviceVlan.query.count() == 0 and Vlan.query.count() == 1


def test_link_of_another_device_is_404(admin, sites):
    v = add_vlan(sites[0])
    d1, d2 = add_device(sites[0], "A", "10.0.0.1"), add_device(sites[0], "B", "10.0.0.2")
    l = link(d1, v)
    assert admin.post(f"/devices/{d2.id}/vlans/{l.id}/delete").status_code == 404
    assert admin.post(f"/devices/{d2.id}/vlans/{l.id}/management").status_code == 404
    assert DeviceVlan.query.count() == 1


def test_user_cannot_change_device_vlans(user, sites):
    v, d = add_vlan(sites[0]), add_device(sites[0])
    l = link(d, v)
    assert user.post(f"/devices/{d.id}/vlans", data={"vlan_id": v.id}).status_code == 403
    assert user.post(f"/devices/{d.id}/vlans/{l.id}/delete").status_code == 403
    assert user.post(f"/devices/{d.id}/vlans/{l.id}/management").status_code == 403
    assert DeviceVlan.query.count() == 1


def test_site_change_blocked_while_vlans_attached(admin, sites):
    cay, kou = sites
    v, d = add_vlan(cay), add_device(cay)
    l = link(d, v)
    data = {"hostname": "SW-1", "ip_address": "10.0.0.1", "device_type": "switch", "site_id": kou.id}
    r = admin.post(f"/devices/{d.id}/edit", data=data)
    assert "Retirez d" in r.get_data(as_text=True)
    assert db.session.get(Device, d.id).site_id == cay.id
    db.session.delete(db.session.get(DeviceVlan, l.id))
    db.session.commit()
    assert admin.post(f"/devices/{d.id}/edit", data=data).status_code == 302
    assert db.session.get(Device, d.id).site_id == kou.id


def test_device_list_shows_and_filters_vlans(user, sites):
    v10, v20 = add_vlan(sites[0], 10), add_vlan(sites[0], 20, "VOIX")
    d1, d2 = add_device(sites[0], "SW-A", "10.0.0.1"), add_device(sites[0], "SW-B", "10.0.0.2")
    link(d1, v10, mgmt=True)
    link(d1, v20)
    link(d2, v20)
    html = user.get("/devices/").get_data(as_text=True)
    assert "10*, 20" in html
    only = user.get("/devices/", query_string={"vlan": 10}).get_data(as_text=True)
    assert ">SW-A<" in only and ">SW-B<" not in only
