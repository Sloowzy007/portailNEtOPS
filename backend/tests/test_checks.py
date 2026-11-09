import socket
import subprocess

import pytest

from app import checks
from app.extensions import db
from app.models import Device, Site


@pytest.fixture
def device(app):
    site = Site(site_name="Cayenne")
    db.session.add(site)
    db.session.flush()
    dev = Device(hostname="localhost", ip_address="127.0.0.1", device_type="server", site_id=site.id)
    db.session.add(dev)
    db.session.commit()
    return dev


@pytest.fixture
def open_port():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    yield srv.getsockname()[1]
    srv.close()


def test_tcp_open(open_port):
    assert checks.check_tcp("127.0.0.1", open_port)["result"] == "success"


def test_tcp_closed():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # port libere : personne n'ecoute
    assert checks.check_tcp("127.0.0.1", port)["result"] == "failure"


def test_tcp_invalid_port():
    assert checks.check_tcp("127.0.0.1", 70000)["result"] == "failure"


def test_dns_ok():
    assert checks.check_dns("localhost", "127.0.0.1")["result"] == "success"


def test_dns_failure():
    assert checks.check_dns("nexiste-pas.invalid")["result"] == "failure"


def test_icmp_rejects_injection():
    out = checks.check_icmp("-f 8.8.8.8; rm -rf /")
    assert out["result"] == "failure" and "invalide" in out["message"]


def test_icmp_success(monkeypatch):
    fake = subprocess.CompletedProcess([], 0, stdout="64 bytes from x: time=0.045 ms", stderr="")
    monkeypatch.setattr(checks.subprocess, "run", lambda *a, **k: fake)
    out = checks.check_icmp("127.0.0.1")
    assert out["result"] == "success"
    assert abs(out["response_time_ms"] - 0.045) < 0.01


def test_icmp_failure(monkeypatch):
    fake = subprocess.CompletedProcess([], 1, stdout="", stderr="")
    monkeypatch.setattr(checks.subprocess, "run", lambda *a, **k: fake)
    assert checks.check_icmp("10.255.255.1")["result"] == "failure"


def test_run_check_saves_history(device, open_port):
    check = checks.run_check(device, "tcp", port=open_port)
    assert check.id is not None and check.result == "success"
    assert device.last_check.id == check.id


def test_run_check_tcp_requires_port(device):
    with pytest.raises(ValueError):
        checks.run_check(device, "tcp")
