from datetime import datetime

from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from . import bp
from ..extensions import db, bcrypt
from ..models import TimeEntry
from ..utils import get_global_minimum, current_month_str, parse_datetime, is_current_month


def _active_entry():
    """Return the current user's open (clocked-in) entry, or None."""
    return TimeEntry.query.filter_by(
        user_id=current_user.id, end_time=None
    ).first()


@bp.route("/")
@login_required
def dashboard():
    active = _active_entry()
    global_min = get_global_minimum()
    return render_template(
        "employee/dashboard.html",
        active=active,
        global_min=global_min,
    )


@bp.route("/clock-in", methods=["POST"])
@login_required
def clock_in():
    if _active_entry():
        flash("You are already clocked in.", "warning")
        return redirect(url_for("employee.dashboard"))

    entry = TimeEntry(user_id=current_user.id, start_time=datetime.now())
    db.session.add(entry)
    db.session.commit()
    flash("Clocked in.", "success")
    return redirect(url_for("employee.dashboard"))


@bp.route("/clock-out", methods=["POST"])
@login_required
def clock_out():
    active = _active_entry()
    if not active:
        flash("You are not currently clocked in.", "warning")
        return redirect(url_for("employee.dashboard"))

    active.end_time = datetime.now()
    active.updated_at = datetime.now()
    db.session.commit()

    global_min = get_global_minimum()
    billed = active.billed_hours(global_min)
    actual = active.actual_hours()
    if billed > actual:
        flash(
            f"Clocked out. Actual: {actual:.2f}h — billed at minimum: {billed:.2f}h.",
            "success",
        )
    else:
        flash(f"Clocked out. Time logged: {billed:.2f}h.", "success")
    return redirect(url_for("employee.dashboard"))


@bp.route("/entry/new", methods=["GET", "POST"])
@login_required
def new_entry():
    global_min = get_global_minimum()

    if request.method == "POST":
        error = _save_entry(None)
        if error:
            flash(error, "danger")
            return render_template(
                "employee/entry_form.html",
                entry=None,
                global_min=global_min,
                form_data=request.form,
            )
        flash("Entry saved.", "success")
        return redirect(url_for("employee.log"))

    return render_template(
        "employee/entry_form.html",
        entry=None,
        global_min=global_min,
        form_data={},
    )


@bp.route("/entry/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_entry(entry_id: int):
    entry = TimeEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for("employee.dashboard"))

    global_min = get_global_minimum()

    if request.method == "POST":
        error = _save_entry(entry)
        if error:
            flash(error, "danger")
            return render_template(
                "employee/entry_form.html",
                entry=entry,
                global_min=global_min,
                form_data=request.form,
            )
        flash("Entry updated.", "success")
        # After correcting a forgotten clock-out, go back to dashboard if it
        # was an active entry; otherwise go to the log.
        return redirect(url_for("employee.dashboard"))

    return render_template(
        "employee/entry_form.html",
        entry=entry,
        global_min=global_min,
        form_data={},
    )


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
            flash("Current password is incorrect.", "danger")
            return render_template("employee/change_password.html")

        if len(new_pw) < 8:
            flash("New password must be at least 8 characters.", "danger")
            return render_template("employee/change_password.html")

        if new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
            return render_template("employee/change_password.html")

        current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
        db.session.commit()
        flash("Password updated successfully.", "success")
        return redirect(url_for("employee.dashboard"))

    return render_template("employee/change_password.html")


@bp.route("/entry/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id: int):
    entry = TimeEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for("employee.log"))
    if not is_current_month(entry):
        flash("Only entries from the current month can be deleted.", "danger")
        return redirect(url_for("employee.log"))
    db.session.delete(entry)
    db.session.commit()
    flash("Entry deleted.", "success")
    return redirect(url_for("employee.log"))


@bp.route("/log")
@login_required
def log():
    month_str = request.args.get("month", current_month_str())
    # Validate format
    try:
        datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        month_str = current_month_str()

    global_min = get_global_minimum()

    entries = (
        TimeEntry.query.filter(
            TimeEntry.user_id == current_user.id,
            TimeEntry.start_time >= _month_start(month_str),
            TimeEntry.start_time <= _month_end(month_str),
        )
        .order_by(TimeEntry.start_time.asc())
        .all()
    )

    return render_template(
        "employee/log.html",
        entries=entries,
        month_str=month_str,
        global_min=global_min,
        now_month=current_month_str(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_entry(existing: TimeEntry | None) -> str | None:
    """
    Validate and persist a time entry from request.form.
    If existing is None, creates a new entry. Otherwise updates it.
    Returns an error string or None on success.
    """
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

    if end_dt > datetime.now():
        return "End time cannot be in the future."

    minimum_hours = None
    if min_str:
        try:
            minimum_hours = float(min_str)
            if minimum_hours < 0:
                return "Minimum hours cannot be negative."
        except ValueError:
            return "Minimum hours must be a number."

    if existing is None:
        entry = TimeEntry(
            user_id=current_user.id,
            start_time=start_dt,
            end_time=end_dt,
            note=note,
            minimum_hours=minimum_hours,
        )
        db.session.add(entry)
    else:
        existing.start_time = start_dt
        existing.end_time = end_dt
        existing.note = note
        existing.minimum_hours = minimum_hours
        existing.updated_at = datetime.now()

    db.session.commit()
    return None


def _month_start(month_str: str) -> datetime:
    year, month = map(int, month_str.split("-"))
    return datetime(year, month, 1, 0, 0, 0)


def _month_end(month_str: str) -> datetime:
    import calendar
    year, month = map(int, month_str.split("-"))
    _, last_day = calendar.monthrange(year, month)
    return datetime(year, month, last_day, 23, 59, 59)
