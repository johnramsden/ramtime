from urllib.parse import urlparse

from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required

from . import bp
from ..extensions import bcrypt
from ..models import User


@bp.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user is None or user.is_archived or not bcrypt.check_password_hash(
            user.password_hash, password
        ):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html"), 401

        login_user(user)
        next_url = request.args.get("next", "")
        # Only allow relative redirects to prevent open redirect attacks
        if next_url and urlparse(next_url).netloc == "":
            return redirect(next_url)
        return redirect(_redirect_url_by_role(user))

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login_page"))


def _redirect_by_role(user):
    return redirect(_redirect_url_by_role(user))


def _redirect_url_by_role(user):
    if user.role == "admin":
        return url_for("admin.dashboard")
    return url_for("employee.dashboard")
