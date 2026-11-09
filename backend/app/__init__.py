from flask import Flask

from .config import Config
from .extensions import csrf, db, login_manager, migrate


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY manquante : renseigner le fichier .env")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (enregistre les modeles)
    from .auth import bp as auth_bp
    from .cli import register_cli
    from .routes.devices import bp as devices_bp
    from .routes.main import bp as main_bp
    from .routes.sites import bp as sites_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(sites_bp)
    register_cli(app)
    return app
