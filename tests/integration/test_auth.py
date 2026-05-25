import pytest
from app.models import User
from app.extensions import db as _db


class TestLogin:
    def test_login_employee_redirects_to_employee_dashboard(self, client, employee_user):
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "password"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Clock in" in resp.data or b"Hello" in resp.data

    def test_login_admin_redirects_to_admin_dashboard(self, client, admin_user):
        resp = client.post(
            "/login",
            data={"username": "bobadmin", "password": "adminpass"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Time entries" in resp.data or b"Dashboard" in resp.data

    def test_login_wrong_password(self, client, employee_user):
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert b"Invalid" in resp.data

    def test_login_unknown_username(self, client, db):
        resp = client.post(
            "/login",
            data={"username": "nobody", "password": "x"},
        )
        assert resp.status_code == 401

    def test_login_archived_user_rejected(self, client, employee_user, db):
        employee_user.is_archived = True
        _db.session.commit()
        resp = client.post(
            "/login",
            data={"username": "alice", "password": "password"},
        )
        assert resp.status_code == 401


class TestLogout:
    def test_logout_redirects_to_login(self, employee_client):
        resp = employee_client.post("/logout", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Sign in" in resp.data


class TestOpenRedirect:
    def test_relative_next_param_is_followed(self, client, employee_user):
        resp = client.post(
            "/login?next=/employee/log",
            data={"username": "alice", "password": "password"},
        )
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/employee/log")

    def test_absolute_external_next_param_is_rejected(self, client, employee_user):
        resp = client.post(
            "/login?next=http://evil.example.com/steal",
            data={"username": "alice", "password": "password"},
        )
        assert resp.status_code == 302
        # Must not redirect to external host
        assert "evil.example.com" not in resp.headers["Location"]

    def test_protocol_relative_next_param_is_rejected(self, client, employee_user):
        resp = client.post(
            "/login?next=//evil.example.com/steal",
            data={"username": "alice", "password": "password"},
        )
        assert resp.status_code == 302
        assert "evil.example.com" not in resp.headers["Location"]


class TestRoleEnforcement:
    def test_employee_cannot_access_admin_dashboard(self, employee_client):
        resp = employee_client.get("/admin/")
        assert resp.status_code == 403

    def test_employee_cannot_access_admin_users(self, employee_client):
        resp = employee_client.get("/admin/users")
        assert resp.status_code == 403

    def test_unauthenticated_redirected_to_login(self, client):
        resp = client.get("/employee/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_admin_can_access_employee_routes(self, admin_client):
        # Admins should not be blocked from /employee/ (they just see employee UI)
        resp = admin_client.get("/employee/", follow_redirects=False)
        # 200 or redirect — not 403
        assert resp.status_code in (200, 302)
        assert resp.status_code != 403
