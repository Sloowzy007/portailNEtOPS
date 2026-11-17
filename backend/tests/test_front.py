"""Garde-fous : HTML, CSS et JS restent dans des fichiers séparés."""
import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app"
TEMPLATES = APP / "templates"
CSS = APP / "static" / "css" / "style.css"
JS = APP / "static" / "js" / "app.js"


def templates():
    return sorted(TEMPLATES.rglob("*.html"))


@pytest.mark.parametrize("path", templates(), ids=lambda p: str(p.relative_to(TEMPLATES)))
def test_template_has_no_inline_css_or_js(path):
    text = path.read_text(encoding="utf-8")
    assert "<style" not in text, "CSS dans le HTML : le mettre dans static/css/style.css"
    assert not re.search(r"\sstyle\s*=", text), "attribut style= interdit : utiliser une classe CSS"
    assert not re.search(r"\son[a-z]+\s*=", text), "gestionnaire onclick/onsubmit interdit : utiliser static/js/app.js"
    assert not re.search(r"<script(?![^>]*\ssrc=)", text), "JavaScript dans le HTML : le mettre dans static/js/app.js"


def test_every_css_class_used_in_html_is_defined():
    css = CSS.read_text(encoding="utf-8")
    missing = set()
    for path in templates():
        text = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", " ", path.read_text(encoding="utf-8"), flags=re.S)
        for value in re.findall(r'class="([^"]*)"', text):
            for name in value.split():
                if f".{name}" not in css:
                    missing.add(f"{name} ({path.relative_to(TEMPLATES)})")
    assert not missing, f"classes absentes de style.css : {sorted(missing)}"


def test_static_files_exist():
    assert CSS.is_file() and JS.is_file()


def test_pages_link_css_and_js(client):
    html = client.get("/login").get_data(as_text=True)
    assert "/static/css/style.css" in html and "/static/js/app.js" in html


def test_static_files_are_served(client):
    css = client.get("/static/css/style.css")
    js = client.get("/static/js/app.js")
    assert css.status_code == 200 and css.mimetype == "text/css"
    assert js.status_code == 200 and "javascript" in js.mimetype


def test_confirm_attribute_used_instead_of_inline_js(app):
    from app.extensions import db
    from app.models import Device, Site, User

    u = User(login="root", email="r@x.fr", role="admin")
    u.set_password("secret123")
    s = Site(site_name="Cayenne")
    db.session.add_all([u, s])
    db.session.commit()
    d = Device(hostname="SW", ip_address="10.0.0.1", device_type="switch", site_id=s.id)
    db.session.add(d)
    db.session.commit()
    c = app.test_client()
    c.post("/login", data={"login": "root", "password": "secret123"})
    html = c.get(f"/devices/{d.id}").get_data(as_text=True)
    assert 'data-confirm="Supprimer cet équipement et son historique ?"' in html
