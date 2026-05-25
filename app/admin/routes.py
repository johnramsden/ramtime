import csv
import io
from datetime import datetime

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    Response,
    stream_with_context,
)
from flask_login import login_required

from . import bp
from ..extensions import db, bcrypt
from ..models import User, TimeEntry, Setting
from ..utils import (
    admin_required,
    entries_query,
    get_global_minimum,
    current_month_str,
    parse_datetime,
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@bp.route("/")
@login_required
@admin_required
def dashboard():
    month_str = request.args.get("month", current_month_str())
    try:
        datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        month_str = current_month_str()

    half = request.args.get("half")  # None | "first" | "second"
    if half not in (None, "first", "second"):
        half = None

    user_id_str = request.args.get("user_id")
    user_id = int(user_id_str) if user_id_str and user_id_str.isdigit() else None

    global_min = get_global_minimum()
    entries = entries_query(month_str, half, user_id).all()
    employees = User.query.filter_by(is_archived=False).order_by(User.name).all()

    return render_template(
        "admin/dashboard.html",
        entries=entries,
        employees=employees,
        month_str=month_str,
        half=half,
        selected_user_id=user_id,
        global_min=global_min,
    )


# ---------------------------------------------------------------------------
# Entry editing
# ---------------------------------------------------------------------------

@bp.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_entry(entry_id: int):
    entry = TimeEntry.query.get_or_404(entry_id)
    global_min = get_global_minimum()

    if request.method == "POST":
        error = _save_entry_admin(entry)
        if error:
            flash(error, "danger")
            return render_template(
                "admin/edit_entry.html",
                entry=entry,
                global_min=global_min,
                form_data=request.form,
            )
        flash("Entry updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/edit_entry.html",
        entry=entry,
        global_min=global_min,
        form_data={},
    )


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.is_archived.asc(), User.name.asc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/users/new", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    if request.method == "POST":
        error = _create_user()
        if error:
            flash(error, "danger")
            return render_template("admin/user_form.html", user=None, form_data=request.form)
        flash("User created.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=None, form_data={})


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        error = _update_user(user)
        if error:
            flash(error, "danger")
            return render_template(
                "admin/user_form.html", user=user, form_data=request.form
            )
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=user, form_data={})


@bp.route("/users/<int:user_id>/archive", methods=["POST"])
@login_required
@admin_required
def archive_user(user_id: int):
    user = User.query.get_or_404(user_id)
    user.is_archived = not user.is_archived
    db.session.commit()
    state = "archived" if user.is_archived else "unarchived"
    flash(f"User '{user.name}' {state}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    confirm = request.form.get("confirm_name", "").strip()
    if confirm != user.username:
        flash("Confirmation did not match username. User not deleted.", "danger")
        return redirect(url_for("admin.users"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.name}' permanently deleted.", "success")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@bp.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    setting = Setting.query.get("default_minimum_hours")

    if request.method == "POST":
        val_str = request.form.get("default_minimum_hours", "").strip()
        try:
            val = float(val_str)
            if val < 0:
                raise ValueError
        except ValueError:
            flash("Minimum hours must be a non-negative number.", "danger")
            return render_template("admin/settings.html", setting=setting)

        if setting is None:
            setting = Setting(key="default_minimum_hours", value=str(val))
            db.session.add(setting)
        else:
            setting.value = str(val)
        db.session.commit()
        flash(f"Default minimum hours updated to {val:.2f}h.", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", setting=setting)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@bp.route("/export")
@login_required
@admin_required
def export_csv():
    month_str = request.args.get("month", current_month_str())
    try:
        datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        month_str = current_month_str()

    global_min = get_global_minimum()
    all_entries = entries_query(month_str, half=None, user_id=None).all()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["Employee Name", "Date", "Start Time", "End Time",
             "Actual Hours", "Billed Hours", "Note"]
        )
        yield buf.getvalue()

        for e in all_entries:
            buf.truncate(0)
            buf.seek(0)
            actual = e.actual_hours()
            billed = e.billed_hours(global_min)
            writer.writerow([
                e.user.name,
                e.start_time.strftime("%Y-%m-%d"),
                e.start_time.strftime("%H:%M"),
                e.end_time.strftime("%H:%M") if e.end_time else "",
                f"{actual:.2f}" if actual is not None else "",
                f"{billed:.2f}",
                e.note or "",
            ])
            yield buf.getvalue()

    filename = f"ramtime_{month_str}.csv"
    return Response(
        stream_with_context(generate()),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _save_entry_admin(entry: TimeEntry) -> str | None:
    date_str = request.form.get("date", "").strip()
    start_str = request.form.get("start_time", "").strip()
    end_str = request.form.get("end_time", "").strip()
    note = request.form.get("note", "").strip() or None
    min_str = request.form.get("minimum_hours", "").strip()

    if not date_str or not start_str or not end_str:
        return "Date, start time, and end time are required."

    try:
        start_dt = parse_datetime(date_str, start_str)
        end_dt = parse_datetime(date_str, end_str)
    except ValueError:
        return "Invalid date or time format."

    if end_dt <= start_dt:
        return "End time must be after start time."

    minimum_hours = None
    if min_str:
        try:
            minimum_hours = float(min_str)
            if minimum_hours < 0:
                return "Minimum hours cannot be negative."
        except ValueError:
            return "Minimum hours must be a number."

    entry.start_time = start_dt
    entry.end_time = end_dt
    entry.note = note
    entry.minimum_hours = minimum_hours
    entry.updated_at = datetime.now()
    db.session.commit()
    return None


def _create_user() -> str | None:
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "employee")

    if not name or not username or not password:
        return "Name, username, and password are required."
    if role not in ("employee", "admin"):
        return "Invalid role."
    if User.query.filter_by(username=username).first():
        return f"Username '{username}' is already taken."

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(name=name, username=username, password_hash=pw_hash, role=role)
    db.session.add(user)
    db.session.commit()
    return None


def _update_user(user: User) -> str | None:
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "employee")

    if not name or not username:
        return "Name and username are required."
    if role not in ("employee", "admin"):
        return "Invalid role."

    conflict = User.query.filter(
        User.username == username, User.id != user.id
    ).first()
    if conflict:
        return f"Username '{username}' is already taken."

    user.name = name
    user.username = username
    user.role = role
    if password:
        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    db.session.commit()
    return None
