from flask import Flask

from app.config import Config
from app.extensions import csrf, db, migrate, oauth


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.testing:
        missing = [
            key for key in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not app.config.get(key)
        ]
        if missing:
            raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    oauth.init_app(app)

    if app.config.get("OIDC_ISSUER"):
        oauth.register(
            name="pocketid",
            server_metadata_url=f"{app.config['OIDC_ISSUER'].rstrip('/')}/.well-known/openid-configuration",
            client_id=app.config["OIDC_CLIENT_ID"],
            client_secret=app.config["OIDC_CLIENT_SECRET"],
            client_kwargs={
                "scope": "openid email profile",
                "code_challenge_method": "S256",
            },
        )

    from app.admin import admin_bp
    from app.guest import guest_bp

    app.register_blueprint(guest_bp)
    app.register_blueprint(admin_bp)

    from app import models  # noqa: F401 -- ensure models are registered with SQLAlchemy

    return app
