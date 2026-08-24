from brain.global_workspace import GlobalWorkspace, GlobalWorkspaceItem, WorkspaceState


def test_workspace_admits_only_high_salience_items():
    workspace = GlobalWorkspace(capacity=2)
    low = GlobalWorkspaceItem("note", "low", "background", [], salience=0.1)
    high = GlobalWorkspaceItem(
        "signal",
        "high",
        "urgent original opportunity",
        ["signal:one"],
        salience=0.8,
        novelty=0.8,
        urgency=0.7,
        goal_pressure=0.7,
    )

    assert workspace.consider(low) is False
    assert workspace.consider(high) is True
    assert high.state == WorkspaceState.ACTIVE_FOCUS
    assert workspace.active_focus()[0].title == "high"
