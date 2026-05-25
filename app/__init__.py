import os
import click
from flask import Flask, session

from .extensions import db, migrate, login_manager, bcrypt
from config import config_map


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    from .auth import bp as auth_bp
    from .employee import bp as employee_bp
    from .admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp, url_prefix="/employee")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.before_request
    def make_session_permanent():
        session.permanent = True

    @app.route("/")
    def index():
        from flask_login import current_user
        from flask import redirect, url_for
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("employee.dashboard"))
        return redirect(url_for("auth.login_page"))

    # Register user_loader after models are importable
    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        user = db.session.get(User, int(user_id))
        if user is None or user.is_archived:
            return None
        return user

    _register_cli(app)

    return app


def _register_cli(app: Flask) -> None:
    @app.cli.command("seed-admin")
    @click.option("--username", prompt=True, help="Admin username")
    @click.option("--name", prompt=True, help="Admin display name")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Admin password",
    )
    def seed_admin(username: str, name: str, password: str) -> None:
        """Create the initial admin user and default settings."""
        from .models import User, Setting

        existing = User.query.filter_by(username=username).first()
        if existing:
            click.echo(f"User '{username}' already exists.")
        else:
            password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            admin = User(
                name=name,
                username=username,
                password_hash=password_hash,
                role="admin",
            )
            db.session.add(admin)
            click.echo(f"Created admin user '{username}'.")

        if not Setting.query.get("default_minimum_hours"):
            db.session.add(Setting(key="default_minimum_hours", value="0.0"))
            click.echo("Seeded default_minimum_hours = 0.0")

        db.session.commit()
        click.echo("Done.")

    @app.cli.command("seed-defaults")
    def seed_defaults() -> None:
        """Non-interactive seed: creates admin/admin if no admin exists."""
        from .models import User, Setting

        if not User.query.filter_by(role="admin").first():
            password_hash = bcrypt.generate_password_hash("admin").decode("utf-8")
            admin = User(
                name="Administrator",
                username="admin",
                password_hash=password_hash,
                role="admin",
            )
            db.session.add(admin)
            click.echo("Created default admin user (username: admin, password: admin).")
        else:
            click.echo("Admin user already exists, skipping.")

        if not Setting.query.get("default_minimum_hours"):
            db.session.add(Setting(key="default_minimum_hours", value="0.0"))

        db.session.commit()
        click.echo("Done.")
