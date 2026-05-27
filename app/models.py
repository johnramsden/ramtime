from datetime import datetime
from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="employee")
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    entries = db.relationship(
        "TimeEntry",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # --- Flask-Login interface ---

    @property
    def is_active(self):
        return not self.is_archived

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User {self.username!r}>"


class TimeEntry(db.Model):
    __tablename__ = "time_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)  # NULL = actively clocked in
    note = db.Column(db.Text, nullable=True)
    minimum_hours = db.Column(db.Float, nullable=True)  # NULL = use global default
    overtime_hours = db.Column(db.Float, nullable=True)  # NULL = no overtime marked
    is_holiday = db.Column(
        db.Boolean, nullable=False, default=False, server_default="0"
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    user = db.relationship("User", back_populates="entries")

    @property
    def is_active_entry(self):
        """True when the employee is currently clocked in (no end time)."""
        return self.end_time is None

    def actual_hours(self):
        """Elapsed hours between start and end. None if still clocked in."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    def effective_minimum(self, global_default: float) -> float:
        """Per-entry override if set, otherwise the global default."""
        if self.minimum_hours is not None:
            return self.minimum_hours
        return global_default

    def billed_hours(self, global_default: float) -> float:
        """Regular billed time = max(actual, effective_minimum) - overtime. 0 if clocked in."""
        actual = self.actual_hours()
        if actual is None:
            return 0.0
        ot = self.overtime_hours or 0.0
        return max(max(actual, self.effective_minimum(global_default)) - ot, 0.0)

    def __repr__(self):
        return f"<TimeEntry user={self.user_id} start={self.start_time}>"


class Setting(db.Model):
    __tablename__ = "settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Setting {self.key}={self.value!r}>"
