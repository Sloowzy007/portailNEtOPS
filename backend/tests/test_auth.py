import pytest

from app.auth import admin_required
from app.extensions import db
from app.models import AuditLog, User


def make_user(login="alice", password="secret123", role="user", active=True):
    u = User(login=login, email=f"{login}@x.fr", role=role, is_active=active)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def do_login(client, login="alice", password="secret123", **kw):
    return client.post("/login", data={"login": login, "password": password}, **kw)


@pytest.fixture
def admin_route(app):
    @app.get("/admin-only")
    @admin_required
    def admin_only():
        return "ok"


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


def test_index_requires_login(client):
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_login_success(client, app):
    user = make_user()
    r = do_login(client)
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    assert client.get("/").status_code == 200
    assert db.session.get(User, user.id).last_login is not None
    assert AuditLog.query.filter_by(action="login").count() == 1


def test_login_wrong_password(client, app):
    make_user()
    r = do_login(client, password="mauvais")
    assert r.status_code == 200 and "incorrect" in r.get_data(as_text=True)
    assert client.get("/").status_code == 302
    assert AuditLog.query.filter_by(action="login_failed").count() == 1


def test_login_unknown_user_same_message(client, app):
    r = do_login(client, login="inconnu")
    assert "incorrect" in r.get_data(as_text=True)


def test_inactive_user_cannot_login(client, app):
    make_user(active=False)
    do_login(client)
    assert client.get("/").status_code == 302


def test_open_redirect_blocked(client, app):
    make_user()
    r = do_login(client, query_string={"next": "https://evil.example"})
    assert "evil" not in r.headers["Location"]


def test_internal_next_allowed(client, app):
    make_user()
    r = do_login(client, query_string={"next": "/health"})
    assert r.headers["Location"].endswith("/health")


def test_logout(client, app):
    make_user()
    do_login(client)
    assert client.post("/logout").status_code == 302
    assert client.get("/").status_code == 302


def test_admin_required(client, app, admin_route):
    make_user("alice", role="user")
    make_user("root", role="admin")
    assert client.get("/admin-only").status_code == 302  # anonyme -> login
    do_login(client, "alice")
    assert client.get("/admin-only").status_code == 403  # simple utilisateur
    client.post("/logout")
    do_login(client, "root")
    assert client.get("/admin-only").status_code == 200  # admin
