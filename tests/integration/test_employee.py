from datetime import datetime, timedelta
import pytest
from app.extensions import db as _db
from app.models import TimeEntry
from tests.conftest import make_entry


class TestClockIn:
    def test_clock_in_creates_active_entry(self, employee_client, employee_user):
        resp = employee_client.post("/employee/clock-in", follow_redirects=True)
        assert resp.status_code == 200
        entry = TimeEntry.query.filter_by(user_id=employee_user.id).first()
        assert entry is not None
        assert entry.end_time is None

    def test_clock_in_when_already_active_shows_warning(self, employee_client, employee_user):
        make_entry(employee_user.id, start=datetime.now())
        resp = employee_client.post("/employee/clock-in", follow_redirects=True)
        assert b"already clocked in" in resp.data

    def test_clock_in_sets_start_time_close_to_now(self, employee_client, employee_user):
        before = datetime.now().replace(microsecond=0)
        employee_client.post("/employee/clock-in")
        entry = TimeEntry.query.filter_by(user_id=employee_user.id).first()
        assert entry.start_time >= before


class TestClockOut:
    def test_clock_out_sets_end_time(self, employee_client, employee_user):
        make_entry(employee_user.id, start=datetime.now() - timedelta(hours=1))
        resp = employee_client.post("/employee/clock-out", follow_redirects=True)
        assert resp.status_code == 200
        entry = TimeEntry.query.filter_by(user_id=employee_user.id).first()
        assert entry.end_time is not None

    def test_clock_out_without_active_entry_shows_warning(self, employee_client):
        resp = employee_client.post("/employee/clock-out", follow_redirects=True)
        assert b"not currently clocked in" in resp.data

    def test_clock_out_applies_minimum_flash(self, employee_client, employee_user, default_setting):
        # Entry: 1.5h actual, minimum 3h → flash should mention minimum
        start = datetime.now() - timedelta(hours=1, minutes=30)
        make_entry(employee_user.id, start=start)
        resp = employee_client.post("/employee/clock-out", follow_redirects=True)
        assert b"minimum" in resp.data.lower() or b"3.00" in resp.data


class TestManualEntry:
    def test_manual_entry_saved(self, employee_client, employee_user):
        resp = employee_client.post(
            "/employee/entry/new",
            data={
                "date": "2024-03-10",
                "start_time": "09:00",
                "end_time": "11:30",
                "note": "Test work",
                "minimum_hours": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        entry = TimeEntry.query.filter_by(user_id=employee_user.id).first()
        assert entry is not None
        assert entry.note == "Test work"

    def test_manual_entry_validates_end_after_start(self, employee_client):
        resp = employee_client.post(
            "/employee/entry/new",
            data={
                "date": "2024-03-10",
                "start_time": "11:00",
                "end_time": "09:00",
                "note": "",
                "minimum_hours": "",
            },
        )
        assert b"after start time" in resp.data

    def test_manual_entry_minimum_applied(self, employee_client, employee_user, default_setting):
        # 1h actual, global minimum 3h → billed = 3h
        resp = employee_client.post(
            "/employee/entry/new",
            data={
                "date": "2024-01-10",
                "start_time": "09:00",
                "end_time": "10:00",
                "note": "",
                "minimum_hours": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        entry = TimeEntry.query.filter_by(user_id=employee_user.id).first()
        from app.utils import get_global_minimum
        assert entry.billed_hours(get_global_minimum()) == pytest.approx(3.0)

    def test_manual_entry_per_entry_override(self, employee_client, employee_user):
        employee_client.post(
            "/employee/entry/new",
            data={
                "date": "2024-01-10",
                "start_time": "09:00",
                "end_time": "10:00",
                "note": "",
                "minimum_hours": "4.0",
            },
        )
        entry = TimeEntry.query.filter_by(user_id=employee_user.id).first()
        assert entry.minimum_hours == pytest.approx(4.0)
        assert entry.billed_hours(0.0) == pytest.approx(4.0)

    def test_manual_entry_future_end_rejected(self, employee_client):
        future = (datetime.now() + timedelta(hours=2)).strftime("%H:%M")
        resp = employee_client.post(
            "/employee/entry/new",
            data={
                "date": datetime.now().strftime("%Y-%m-%d"),
                "start_time": "00:01",
                "end_time": future,
                "note": "",
                "minimum_hours": "",
            },
        )
        assert b"future" in resp.data


class TestEditEntry:
    def test_edit_own_entry(self, employee_client, employee_user):
        entry = make_entry(
            employee_user.id,
            start=datetime(2024, 3, 10, 9, 0),
            end=datetime(2024, 3, 10, 11, 0),
        )
        resp = employee_client.post(
            f"/employee/entry/{entry.id}/edit",
            data={
                "date": "2024-03-10",
                "start_time": "09:00",
                "end_time": "13:00",
                "note": "Updated",
                "minimum_hours": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        _db.session.refresh(entry)
        assert entry.note == "Updated"
        assert entry.end_time.hour == 13

    def test_cannot_edit_other_users_entry(self, employee_client, admin_user):
        entry = make_entry(
            admin_user.id,
            start=datetime(2024, 3, 10, 9, 0),
            end=datetime(2024, 3, 10, 11, 0),
        )
        resp = employee_client.post(
            f"/employee/entry/{entry.id}/edit",
            data={
                "date": "2024-03-10",
                "start_time": "09:00",
                "end_time": "13:00",
                "note": "",
                "minimum_hours": "",
            },
        )
        # Redirected or forbidden
        assert resp.status_code in (302, 403)


class TestDeleteEntry:
    def test_delete_current_month_entry(self, employee_client, employee_user):
        entry = make_entry(
            employee_user.id,
            start=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
            end=datetime.now().replace(hour=11, minute=0, second=0, microsecond=0),
        )
        resp = employee_client.post(
            f"/employee/entry/{entry.id}/delete", follow_redirects=True
        )
        assert resp.status_code == 200
        assert TimeEntry.query.get(entry.id) is None

    def test_cannot_delete_past_month_entry(self, employee_client, employee_user):
        entry = make_entry(
            employee_user.id,
            start=datetime(2024, 3, 10, 9, 0),
            end=datetime(2024, 3, 10, 11, 0),
        )
        resp = employee_client.post(
            f"/employee/entry/{entry.id}/delete", follow_redirects=True
        )
        assert b"current month" in resp.data
        assert TimeEntry.query.get(entry.id) is not None

    def test_cannot_delete_other_users_entry(self, employee_client, admin_user):
        entry = make_entry(
            admin_user.id,
            start=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
            end=datetime.now().replace(hour=11, minute=0, second=0, microsecond=0),
        )
        resp = employee_client.post(
            f"/employee/entry/{entry.id}/delete", follow_redirects=True
        )
        assert TimeEntry.query.get(entry.id) is not None


class TestChangePassword:
    def test_change_password_success(self, employee_client, employee_user):
        resp = employee_client.post(
            "/employee/change-password",
            data={
                "current_password": "password",
                "new_password": "newpassword1",
                "confirm_password": "newpassword1",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"updated successfully" in resp.data
        # Verify new password works
        from app.extensions import bcrypt
        _db.session.refresh(employee_user)
        assert bcrypt.check_password_hash(employee_user.password_hash, "newpassword1")

    def test_wrong_current_password_rejected(self, employee_client):
        resp = employee_client.post(
            "/employee/change-password",
            data={
                "current_password": "wrongpassword",
                "new_password": "newpassword1",
                "confirm_password": "newpassword1",
            },
        )
        assert b"incorrect" in resp.data

    def test_mismatched_new_passwords_rejected(self, employee_client):
        resp = employee_client.post(
            "/employee/change-password",
            data={
                "current_password": "password",
                "new_password": "newpassword1",
                "confirm_password": "differentpassword",
            },
        )
        assert b"do not match" in resp.data

    def test_short_password_rejected(self, employee_client):
        resp = employee_client.post(
            "/employee/change-password",
            data={
                "current_password": "password",
                "new_password": "short",
                "confirm_password": "short",
            },
        )
        assert b"8 characters" in resp.data


class TestMonthlyLog:
    def test_log_shows_entries_for_month(self, employee_client, employee_user):
        make_entry(
            employee_user.id,
            start=datetime(2024, 3, 10, 9, 0),
            end=datetime(2024, 3, 10, 11, 0),
            note="March work",
        )
        resp = employee_client.get("/employee/log?month=2024-03")
        assert b"March work" in resp.data

    def test_log_excludes_other_month(self, employee_client, employee_user):
        make_entry(
            employee_user.id,
            start=datetime(2024, 4, 1, 9, 0),
            end=datetime(2024, 4, 1, 11, 0),
            note="April work",
        )
        resp = employee_client.get("/employee/log?month=2024-03")
        assert b"April work" not in resp.data

    def test_log_excludes_other_users_entries(
        self, employee_client, employee_user, admin_user
    ):
        make_entry(
            admin_user.id,
            start=datetime(2024, 3, 5, 9, 0),
            end=datetime(2024, 3, 5, 11, 0),
            note="Admin secret",
        )
        resp = employee_client.get("/employee/log?month=2024-03")
        assert b"Admin secret" not in resp.data
