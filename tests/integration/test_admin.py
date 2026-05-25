import csv
import io
from datetime import datetime, timedelta

import pytest
from app.extensions import db as _db
from app.models import User, TimeEntry, Setting
from tests.conftest import make_entry


class TestAdminDashboard:
    def test_shows_all_employees_entries(self, admin_client, employee_user, admin_user):
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 5, 9, 0),
                   end=datetime(2024, 3, 5, 11, 0))
        make_entry(admin_user.id,
                   start=datetime(2024, 3, 6, 9, 0),
                   end=datetime(2024, 3, 6, 11, 0))

        resp = admin_client.get("/admin/?month=2024-03")
        assert resp.status_code == 200
        assert b"Alice Employee" in resp.data
        assert b"Bob Admin" in resp.data

    def test_filter_first_half(self, admin_client, employee_user):
        e1 = make_entry(employee_user.id,
                        start=datetime(2024, 3, 5, 9, 0),
                        end=datetime(2024, 3, 5, 11, 0))
        e2 = make_entry(employee_user.id,
                        start=datetime(2024, 3, 20, 9, 0),
                        end=datetime(2024, 3, 20, 11, 0))

        resp = admin_client.get("/admin/?month=2024-03&half=first")
        assert b"2024-03-05" in resp.data
        assert b"2024-03-20" not in resp.data

    def test_filter_second_half(self, admin_client, employee_user):
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 5, 9, 0),
                   end=datetime(2024, 3, 5, 11, 0))
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 20, 9, 0),
                   end=datetime(2024, 3, 20, 11, 0))

        resp = admin_client.get("/admin/?month=2024-03&half=second")
        assert b"2024-03-20" in resp.data
        assert b"2024-03-05" not in resp.data

    def test_filter_by_employee(self, admin_client, employee_user, admin_user):
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 5, 9, 0),
                   end=datetime(2024, 3, 5, 11, 0))
        make_entry(admin_user.id,
                   start=datetime(2024, 3, 6, 9, 0),
                   end=datetime(2024, 3, 6, 11, 0))

        resp = admin_client.get(f"/admin/?month=2024-03&user_id={employee_user.id}")
        # Alice's entry date should appear; Bob's entry date should not
        assert b"2024-03-05" in resp.data
        assert b"2024-03-06" not in resp.data

    def test_excludes_active_entries(self, admin_client, employee_user):
        make_entry(employee_user.id, start=datetime(2024, 3, 5, 9, 0), end=None)
        resp = admin_client.get("/admin/?month=2024-03")
        assert b"Active" not in resp.data or b"2024-03-05" not in resp.data


class TestAdminEditEntry:
    def test_admin_can_edit_any_entry(self, admin_client, employee_user):
        entry = make_entry(employee_user.id,
                           start=datetime(2024, 3, 10, 9, 0),
                           end=datetime(2024, 3, 10, 11, 0))
        resp = admin_client.post(
            f"/admin/entry/{entry.id}/edit",
            data={
                "date": "2024-03-10",
                "start_time": "09:00",
                "end_time": "14:00",
                "note": "Admin corrected",
                "minimum_hours": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        _db.session.refresh(entry)
        assert entry.note == "Admin corrected"
        assert entry.end_time.hour == 14


class TestAdminDeleteEntry:
    def test_admin_can_delete_current_month_entry(self, admin_client, employee_user):
        entry = make_entry(
            employee_user.id,
            start=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
            end=datetime.now().replace(hour=11, minute=0, second=0, microsecond=0),
        )
        resp = admin_client.post(
            f"/admin/entry/{entry.id}/delete", follow_redirects=True
        )
        assert resp.status_code == 200
        assert TimeEntry.query.get(entry.id) is None

    def test_admin_can_delete_past_month_entry(self, admin_client, employee_user):
        entry = make_entry(
            employee_user.id,
            start=datetime(2024, 3, 10, 9, 0),
            end=datetime(2024, 3, 10, 11, 0),
        )
        resp = admin_client.post(
            f"/admin/entry/{entry.id}/delete", follow_redirects=True
        )
        assert resp.status_code == 200
        assert TimeEntry.query.get(entry.id) is None


class TestUserManagement:
    def test_create_user(self, admin_client, db):
        resp = admin_client.post(
            "/admin/users/new",
            data={
                "name": "Carol New",
                "username": "carol",
                "password": "secret123",
                "role": "employee",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        user = User.query.filter_by(username="carol").first()
        assert user is not None
        assert user.name == "Carol New"

    def test_create_user_duplicate_username_rejected(self, admin_client, employee_user):
        resp = admin_client.post(
            "/admin/users/new",
            data={
                "name": "Duplicate",
                "username": "alice",
                "password": "abc123",
                "role": "employee",
            },
        )
        assert b"already taken" in resp.data

    def test_archive_user_prevents_login(self, admin_client, employee_user):
        # Verify the archive route toggles is_archived
        resp = admin_client.post(
            f"/admin/users/{employee_user.id}/archive", follow_redirects=True
        )
        assert resp.status_code == 200
        _db.session.refresh(employee_user)
        assert employee_user.is_archived is True

    def test_archived_user_cannot_login(self, client, employee_user):
        # Set archived directly so we can test login in a clean request
        employee_user.is_archived = True
        _db.session.commit()
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "password"},
        )
        assert resp.status_code == 401

    def test_archive_preserves_entries(self, admin_client, employee_user):
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 5, 9, 0),
                   end=datetime(2024, 3, 5, 11, 0))
        admin_client.post(f"/admin/users/{employee_user.id}/archive")
        count = TimeEntry.query.filter_by(user_id=employee_user.id).count()
        assert count == 1

    def test_unarchive_restores_login(self, admin_client, client, employee_user, db):
        employee_user.is_archived = True
        _db.session.commit()
        admin_client.post(f"/admin/users/{employee_user.id}/archive")
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "password"},
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_delete_user_requires_username_confirm(self, admin_client, employee_user):
        resp = admin_client.post(
            f"/admin/users/{employee_user.id}/delete",
            data={"confirm_name": "wrong"},
            follow_redirects=True,
        )
        assert User.query.get(employee_user.id) is not None

    def test_delete_user_removes_entries(self, admin_client, employee_user):
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 5, 9, 0),
                   end=datetime(2024, 3, 5, 11, 0))
        admin_client.post(
            f"/admin/users/{employee_user.id}/delete",
            data={"confirm_name": "alice"},
        )
        assert User.query.get(employee_user.id) is None
        assert TimeEntry.query.filter_by(user_id=employee_user.id).count() == 0


class TestSettings:
    def test_save_minimum_hours(self, admin_client, db):
        resp = admin_client.post(
            "/admin/settings",
            data={"default_minimum_hours": "2.5"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        setting = Setting.query.get("default_minimum_hours")
        assert setting is not None
        assert float(setting.value) == pytest.approx(2.5)

    def test_invalid_minimum_rejected(self, admin_client, db):
        resp = admin_client.post(
            "/admin/settings",
            data={"default_minimum_hours": "abc"},
        )
        assert b"non-negative number" in resp.data


class TestCSVExport:
    def test_export_returns_csv_content_type(self, admin_client):
        resp = admin_client.get("/admin/export?month=2024-03")
        assert "text/csv" in resp.content_type

    def test_export_filename_contains_month(self, admin_client):
        resp = admin_client.get("/admin/export?month=2024-03")
        assert "ramtime_2024-03.csv" in resp.headers.get("Content-Disposition", "")

    def test_export_has_correct_columns(self, admin_client):
        resp = admin_client.get("/admin/export?month=2024-03")
        reader = csv.reader(io.StringIO(resp.data.decode()))
        header = next(reader)
        assert header == [
            "Employee Name", "Date", "Start Time", "End Time",
            "Actual Hours", "Billed Hours", "Note"
        ]

    def test_export_billed_hours_correct(self, admin_client, employee_user, default_setting):
        # Actual: 1h, minimum: 3h → billed: 3h
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 10, 9, 0),
                   end=datetime(2024, 3, 10, 10, 0))

        resp = admin_client.get("/admin/export?month=2024-03")
        reader = csv.reader(io.StringIO(resp.data.decode()))
        next(reader)  # skip header
        row = next(reader)
        assert row[5] == "3.00"  # Billed Hours

    def test_export_includes_note(self, admin_client, employee_user):
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 10, 9, 0),
                   end=datetime(2024, 3, 10, 11, 0),
                   note="Payroll note")
        resp = admin_client.get("/admin/export?month=2024-03")
        assert b"Payroll note" in resp.data

    def test_export_empty_month_returns_header_only(self, admin_client):
        resp = admin_client.get("/admin/export?month=2000-01")
        reader = csv.reader(io.StringIO(resp.data.decode()))
        rows = list(reader)
        assert len(rows) == 1  # just the header
