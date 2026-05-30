from datetime import datetime
import pytest

from app.utils import entries_query, get_global_minimum, parse_datetime


class TestParseDateTime:
    def test_valid(self):
        dt = parse_datetime("2024-03-15", "09:30")
        assert dt == datetime(2024, 3, 15, 9, 30)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_datetime("not-a-date", "09:30")


class TestGetGlobalMinimum:
    def test_returns_zero_when_no_setting(self, db):
        assert get_global_minimum() == 0.0

    def test_returns_setting_value(self, db, default_setting):
        assert get_global_minimum() == pytest.approx(3.0)

    def test_returns_zero_when_value_malformed(self, db):
        from app.models import Setting
        from app.extensions import db as _db
        _db.session.add(Setting(key="default_minimum_hours", value="not-a-number"))
        _db.session.commit()
        assert get_global_minimum() == 0.0


class TestEntriesQuery:
    """Tests require a db fixture for SQLAlchemy context."""

    def test_full_month_range(self, db, employee_user):
        from tests.conftest import make_entry
        # Entry in target month
        e1 = make_entry(employee_user.id,
                        start=datetime(2024, 3, 10, 9, 0),
                        end=datetime(2024, 3, 10, 17, 0))
        # Entry in different month (should be excluded)
        make_entry(employee_user.id,
                   start=datetime(2024, 4, 1, 9, 0),
                   end=datetime(2024, 4, 1, 17, 0))

        results = entries_query("2024-03", half=None, user_id=None).all()
        ids = [e.id for e in results]
        assert e1.id in ids
        assert len(results) == 1

    def test_first_half(self, db, employee_user):
        from tests.conftest import make_entry
        e_first = make_entry(employee_user.id,
                             start=datetime(2024, 3, 5, 9, 0),
                             end=datetime(2024, 3, 5, 17, 0))
        e_second = make_entry(employee_user.id,
                              start=datetime(2024, 3, 20, 9, 0),
                              end=datetime(2024, 3, 20, 17, 0))

        results = entries_query("2024-03", half="first", user_id=None).all()
        ids = [e.id for e in results]
        assert e_first.id in ids
        assert e_second.id not in ids

    def test_second_half(self, db, employee_user):
        from tests.conftest import make_entry
        e_first = make_entry(employee_user.id,
                             start=datetime(2024, 3, 5, 9, 0),
                             end=datetime(2024, 3, 5, 17, 0))
        e_second = make_entry(employee_user.id,
                              start=datetime(2024, 3, 20, 9, 0),
                              end=datetime(2024, 3, 20, 17, 0))

        results = entries_query("2024-03", half="second", user_id=None).all()
        ids = [e.id for e in results]
        assert e_second.id in ids
        assert e_first.id not in ids

    def test_filter_by_user(self, db, employee_user, admin_user):
        from tests.conftest import make_entry
        e_alice = make_entry(employee_user.id,
                             start=datetime(2024, 3, 5, 9, 0),
                             end=datetime(2024, 3, 5, 17, 0))
        e_bob = make_entry(admin_user.id,
                           start=datetime(2024, 3, 6, 9, 0),
                           end=datetime(2024, 3, 6, 17, 0))

        results = entries_query("2024-03", half=None, user_id=employee_user.id).all()
        ids = [e.id for e in results]
        assert e_alice.id in ids
        assert e_bob.id not in ids

    def test_excludes_active_entries(self, db, employee_user):
        from tests.conftest import make_entry
        # Active entry (no end_time) — should be excluded
        make_entry(employee_user.id,
                   start=datetime(2024, 3, 10, 9, 0),
                   end=None)

        results = entries_query("2024-03", half=None, user_id=None).all()
        assert len(results) == 0

    def test_second_half_february_leap_year(self, db, employee_user):
        from tests.conftest import make_entry
        e = make_entry(employee_user.id,
                       start=datetime(2024, 2, 29, 9, 0),
                       end=datetime(2024, 2, 29, 17, 0))
        results = entries_query("2024-02", half="second", user_id=None).all()
        assert e.id in [r.id for r in results]
