import calendar
from datetime import datetime
from functools import wraps

from flask import abort
from flask_login import current_user

from .models import Setting, TimeEntry


# ---------------------------------------------------------------------------
# Role-enforcement decorators
# ---------------------------------------------------------------------------

def admin_required(f):
    """Restrict a route to admin users. Returns 403 for non-admins."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def get_global_minimum() -> float:
    """Return the admin-configured default minimum hours (0.0 if not set)."""
    setting = Setting.query.get("default_minimum_hours")
    if setting is None:
        return 0.0
    try:
        return float(setting.value)
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def entries_query(month_str: str, half: str | None, user_id: int | None):
    """
    Build a TimeEntry query for the given period.

    Args:
        month_str:  "YYYY-MM"
        half:       None (full month) | "first" (days 1-15) | "second" (16-end)
        user_id:    None (all users) | int (single user)

    Returns completed entries only (end_time IS NOT NULL).
    """
    year, month = map(int, month_str.split("-"))
    _, last_day = calendar.monthrange(year, month)

    if half == "first":
        range_start = datetime(year, month, 1, 0, 0, 0)
        range_end = datetime(year, month, 15, 23, 59, 59)
    elif half == "second":
        range_start = datetime(year, month, 16, 0, 0, 0)
        range_end = datetime(year, month, last_day, 23, 59, 59)
    else:
        range_start = datetime(year, month, 1, 0, 0, 0)
        range_end = datetime(year, month, last_day, 23, 59, 59)

    q = TimeEntry.query.filter(
        TimeEntry.start_time >= range_start,
        TimeEntry.start_time <= range_end,
        TimeEntry.end_time.isnot(None),
    )
    if user_id:
        q = q.filter(TimeEntry.user_id == user_id)

    return q.order_by(TimeEntry.start_time.asc())


def current_month_str() -> str:
    """Return today's month as 'YYYY-MM'."""
    return datetime.now().strftime("%Y-%m")


def is_current_month(entry: "TimeEntry") -> bool:
    """Return True if the entry's start_time falls in the current calendar month."""
    now = datetime.now()
    return (
        entry.start_time.year == now.year
        and entry.start_time.month == now.month
    )


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """
    Combine a date string ('YYYY-MM-DD') and time string ('HH:MM') into a
    naive datetime representing local time.
    """
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
