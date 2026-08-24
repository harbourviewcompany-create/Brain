from brain.goals import GoalKind, GoalPressureSystem, GoalStateName


def test_goal_pressure_competes_and_selects_dominant_goal():
    goals = GoalPressureSystem()
    goals.update_pressure(GoalKind.PROTECT, current=0.45, priority=1.0)
    goals.update_pressure(GoalKind.EXPLOIT, current=0.4, priority=0.5)

    report = goals.tension_report()

    assert report["dominant_goal"] in report["active_goals"]
    assert report["protect_overrides_exploit"] is True
    exploit = next(goal for goal in goals.goals.values() if goal.goal_type == GoalKind.EXPLOIT)
    assert exploit.state == GoalStateName.SUPPRESSED
