import click

from .extensions import db
from .models import User


def register_cli(app):
    @app.cli.command("create-admin")
    @click.option("--login", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option()
    def create_admin(login, email, password):
        """Cree un compte administrateur."""
        user = User(login=login, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Admin '{login}' cree.")
