from agent_loop import TOOL_HANDLERS, run_agent_step

result = run_agent_step(
    "inspect_lambda_metrics",
    incident_accepted=True,
    action_evidence_complete=False,
    human_approved=False,
)

assert result["status"] == "executed"
assert result["tool"] == "inspect_lambda_metrics"
assert result["result"]["mode"] == "simulation"
assert result["result"]["duration_seconds"] == 14.8

print("PASS accepted inspection executes the simulated handler")
print(result)


rollback_result = run_agent_step(
    "rollback_lambda_deployment",
    incident_accepted=True,
    action_evidence_complete=True,
    human_approved=True,
)

assert rollback_result["status"] == "blocked"
assert rollback_result["reason"] == "No executable handler is registered."
assert "result" not in rollback_result

print("PASS authorized rollback cannot execute without a registered handler")
print(rollback_result)

calls = {"count": 0}


def fake_rollback():
    calls["count"] += 1
    return {"rolled_back": True}


TOOL_HANDLERS["rollback_lambda_deployment"] = fake_rollback

try:
    blocked_rollback = run_agent_step(
        "rollback_lambda_deployment",
        incident_accepted=True,
        action_evidence_complete=True,
        human_approved=False,
    )

    assert blocked_rollback["status"] == "blocked"
    assert blocked_rollback["reason"] == "Human approval is required."
    assert calls["count"] == 0

    print("PASS blocked rollback caused zero handler calls")
finally:
    TOOL_HANDLERS.pop("rollback_lambda_deployment", None)