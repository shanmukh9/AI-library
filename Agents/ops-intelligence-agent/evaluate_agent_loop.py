from agent_loop import (
    TOOL_HANDLERS,
    run_agent_step,
    validate_tool_arguments,
    validate_tool_observation,
)

mismatched_observation = {
    "mode": "simulation",
    "function": "notification-worker",
    "duration_seconds": 14.8,
    "configured_timeout_seconds": 15,
    "downstream_latency": "normal",
    "recent_deployment": True,
}

valid, reason = validate_tool_observation(
    "inspect_lambda_metrics",
    {"function_name": "payment-processor"},
    mismatched_observation,
)

assert valid is False
assert reason == "Observed function does not match requested function."

print("PASS mismatched observation target is rejected")


malformed_observation = {
    "mode": "simulation",
    "function": "payment-processor",
    "duration_seconds": "14.8",
    "configured_timeout_seconds": 15,
    "downstream_latency": "normal",
    "recent_deployment": True,
}

valid, reason = validate_tool_observation(
    "inspect_lambda_metrics",
    {"function_name": "payment-processor"},
    malformed_observation,
)

assert valid is False
assert reason == "duration_seconds must be a non-negative number."

print("PASS malformed duration observation is rejected")

result = run_agent_step(
    "inspect_lambda_metrics",
    tool_arguments={
        "function_name": "payment-processor",
    },
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

invalid_arguments = {
    "function_name": 123,
}

valid, reason = validate_tool_arguments(
    "inspect_lambda_metrics",
    invalid_arguments,
)

assert valid is False
assert reason == "function_name must be a non-empty string."

print("PASS invalid tool arguments are rejected before authorization")

invalid_execution = run_agent_step(
    "inspect_lambda_metrics",
    tool_arguments={
        "function_name": 123,
    },
    incident_accepted=True,
    action_evidence_complete=False,
    human_approved=False,
)

assert invalid_execution["status"] == "blocked"
assert invalid_execution["reason"] == (
    "function_name must be a non-empty string."
)

print("PASS agent step blocks invalid arguments before execution")


observation_calls = {"count": 0}
original_inspection_handler = TOOL_HANDLERS["inspect_lambda_metrics"]


def malformed_inspection(*, function_name: str):
    observation_calls["count"] += 1
    return {
        "mode": "simulation",
        "function": function_name,
        "duration_seconds": "14.8",
        "configured_timeout_seconds": 15,
        "downstream_latency": "normal",
        "recent_deployment": True,
    }


TOOL_HANDLERS["inspect_lambda_metrics"] = malformed_inspection

try:
    rejected_observation = run_agent_step(
        "inspect_lambda_metrics",
        tool_arguments={
            "function_name": "payment-processor",
        },
        incident_accepted=True,
        action_evidence_complete=False,
        human_approved=False,
    )

    assert rejected_observation["status"] == "observation_rejected"
    assert rejected_observation["tool_executed"] is True
    assert rejected_observation["result_trusted"] is False
    assert observation_calls["count"] == 1
    assert "result" not in rejected_observation

    print("PASS malformed executed observation is not trusted")
finally:
    TOOL_HANDLERS["inspect_lambda_metrics"] = original_inspection_handler


rollback_result = run_agent_step(
    "rollback_lambda_deployment",
    tool_arguments={
        "function_name": "payment-processor",
    },
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


def fake_rollback(*, function_name: str):
    calls["count"] += 1
    return {
        "rolled_back": True,
        "function": function_name,
    }

TOOL_HANDLERS["rollback_lambda_deployment"] = fake_rollback

try:
    blocked_rollback = run_agent_step( "rollback_lambda_deployment",
        tool_arguments={
            "function_name": "payment-processor",
        },
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
