from src.domain.models import Goal, GoalDirection, ProgressSnapshot


def test_at_least_goal_on_track_when_current_meets_target():
    goal = Goal(name="steps", target=10000, direction=GoalDirection.AT_LEAST, unit="steps")
    snapshot = ProgressSnapshot(goal, current=12000)

    assert snapshot.on_track is True
    assert snapshot.delta == 2000
    assert snapshot.progress_ratio == 1.2


def test_at_least_goal_not_on_track_when_below_target():
    goal = Goal(name="weekly_distance", target=20, direction=GoalDirection.AT_LEAST, unit="km")
    snapshot = ProgressSnapshot(goal, current=15)

    assert snapshot.on_track is False
    assert snapshot.delta == -5
    assert snapshot.progress_ratio == 0.75


def test_at_most_goal_on_track_when_current_below_target():
    goal = Goal(name="weight", target=75, direction=GoalDirection.AT_MOST, unit="kg", baseline=80)
    snapshot = ProgressSnapshot(goal, current=77)

    assert snapshot.on_track is False  # 77 > 75, aún no llegó
    assert snapshot.delta == 2
    # de 80 a 75 son 5kg de objetivo; bajó 3kg (80->77) => 3/5
    assert snapshot.progress_ratio == 0.6


def test_at_most_goal_progress_ratio_none_without_baseline():
    goal = Goal(name="weight", target=75, direction=GoalDirection.AT_MOST, unit="kg")
    snapshot = ProgressSnapshot(goal, current=77)

    assert snapshot.progress_ratio is None


def test_snapshot_without_current_value_is_unknown():
    goal = Goal(name="sleep", target=8, direction=GoalDirection.AT_LEAST, unit="h")
    snapshot = ProgressSnapshot(goal, current=None)

    assert snapshot.on_track is None
    assert snapshot.delta is None
    assert snapshot.progress_ratio is None
