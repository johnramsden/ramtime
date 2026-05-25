from datetime import datetime, timedelta
import pytest
from app.models import TimeEntry, User


class TestTimeEntryActualHours:
    def test_complete_entry(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 11, 30),
        )
        assert entry.actual_hours() == pytest.approx(2.5)

    def test_active_entry_returns_none(self):
        entry = TimeEntry(user_id=1, start_time=datetime(2024, 1, 15, 9, 0))
        assert entry.actual_hours() is None

    def test_one_hour(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 8, 0),
            end_time=datetime(2024, 1, 15, 9, 0),
        )
        assert entry.actual_hours() == pytest.approx(1.0)


class TestTimeEntryBilledHours:
    def test_above_minimum_billed_at_actual(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 13, 0),  # 4h actual
        )
        assert entry.billed_hours(3.0) == pytest.approx(4.0)

    def test_below_minimum_billed_at_minimum(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 10, 30),  # 1.5h actual
        )
        assert entry.billed_hours(3.0) == pytest.approx(3.0)

    def test_equal_to_minimum(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 12, 0),  # 3h actual
        )
        assert entry.billed_hours(3.0) == pytest.approx(3.0)

    def test_uses_global_when_no_override(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 10, 0),  # 1h actual
            minimum_hours=None,
        )
        assert entry.billed_hours(2.5) == pytest.approx(2.5)

    def test_uses_per_entry_override(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 10, 0),  # 1h actual
            minimum_hours=4.0,
        )
        # Per-entry override (4h) overrides global (2h)
        assert entry.billed_hours(2.0) == pytest.approx(4.0)

    def test_zero_global_minimum(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 10, 30),  # 1.5h actual
        )
        assert entry.billed_hours(0.0) == pytest.approx(1.5)

    def test_active_entry_returns_zero(self):
        entry = TimeEntry(user_id=1, start_time=datetime(2024, 1, 15, 9, 0))
        assert entry.billed_hours(3.0) == pytest.approx(0.0)


class TestTimeEntryIsActive:
    def test_active_when_no_end_time(self):
        entry = TimeEntry(user_id=1, start_time=datetime.now())
        assert entry.is_active_entry is True

    def test_not_active_when_end_time_set(self):
        entry = TimeEntry(
            user_id=1,
            start_time=datetime(2024, 1, 15, 9, 0),
            end_time=datetime(2024, 1, 15, 17, 0),
        )
        assert entry.is_active_entry is False


class TestUserIsActive:
    def test_active_when_not_archived(self):
        user = User(
            name="Test", username="test",
            password_hash="x", role="employee", is_archived=False
        )
        assert user.is_active is True

    def test_inactive_when_archived(self):
        user = User(
            name="Test", username="test",
            password_hash="x", role="employee", is_archived=True
        )
        assert user.is_active is False
