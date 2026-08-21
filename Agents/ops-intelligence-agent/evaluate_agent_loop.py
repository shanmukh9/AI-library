from agent_loop import (
    AgentRunState,
    TOOL_HANDLERS,
    build_tool_call_fingerprint,
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
assert result["derived_facts"] == {
    "timeout_headroom_seconds": 0.2,
    "timeout_utilization_percent": 98.7,
    "near_timeout": True,
    "timed_out": False,
}
assert result["follow_up"] == {
    "decision": "stop_and_escalate",
    "reason": "Execution is within five percent of its timeout.",
    "automatic_action": None,
}


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


duplicate_calls = {"count": 0}
original_inspection_handler = TOOL_HANDLERS["inspect_lambda_metrics"]


def counting_inspection(*, function_name: str):
    duplicate_calls["count"] += 1
    return {
        "mode": "simulation",
        "function": function_name,
        "duration_seconds": 14.8,
        "configured_timeout_seconds": 15,
        "downstream_latency": "normal",
        "recent_deployment": True,
    }


TOOL_HANDLERS["inspect_lambda_metrics"] = counting_inspection
duplicate_run_state = AgentRunState()

try:
    first_call = run_agent_step(
        "inspect_lambda_metrics",
        tool_arguments={
            "function_name": "payment-processor",
        },
        incident_accepted=True,
        action_evidence_complete=False,
        human_approved=False,
        run_state=duplicate_run_state,
    )
    duplicate_call = run_agent_step(
        "inspect_lambda_metrics",
        tool_arguments={
            "function_name": "payment-processor",
        },
        incident_accepted=True,
        action_evidence_complete=False,
        human_approved=False,
        run_state=duplicate_run_state,
    )

    assert first_call["status"] == "executed"
    assert duplicate_call["status"] == "duplicate_rejected"
    assert duplicate_call["tool_executed"] is False
    assert duplicate_calls["count"] == 1

    print("PASS duplicate tool call executes only once per agent run")
finally:
    TOOL_HANDLERS["inspect_lambda_metrics"] = original_inspection_handler


budget_run_state = AgentRunState(max_steps=2)

first_invalid_step = run_agent_step(
    "inspect_lambda_metrics",
    tool_arguments={"function_name": 123},
    incident_accepted=True,
    action_evidence_complete=False,
    human_approved=False,
    run_state=budget_run_state,
)
second_invalid_step = run_agent_step(
    "inspect_lambda_metrics",
    tool_arguments={"function_name": ""},
    incident_accepted=True,
    action_evidence_complete=False,
    human_approved=False,
    run_state=budget_run_state,
)
third_valid_step = run_agent_step(
    "inspect_lambda_metrics",
    tool_arguments={"function_name": "payment-processor"},
    incident_accepted=True,
    action_evidence_complete=False,
    human_approved=False,
    run_state=budget_run_state,
)

assert first_invalid_step["status"] == "blocked"
assert second_invalid_step["status"] == "blocked"
assert third_valid_step["status"] == "step_limit_reached"
assert third_valid_step["tool_executed"] is False
assert budget_run_state.steps_used == 2

print("PASS invalid iterations consume the per-run step budget")


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




invalid_timeout_observation = {
    "mode": "simulation",
    "function": "payment-processor",
    "duration_seconds": 14.8,
    "configured_timeout_seconds": 0,
    "downstream_latency": "normal",
    "recent_deployment": True,
}

valid, reason = validate_tool_observation(
    "inspect_lambda_metrics",
    {"function_name": "payment-processor"},
    invalid_timeout_observation,
)


first_fingerprint = build_tool_call_fingerprint(
    "inspect_lambda_metrics",
    {
        "function_name": "payment-processor",
        "region": "ap-south-1",
    },
)
reordered_fingerprint = build_tool_call_fingerprint(
    "inspect_lambda_metrics",
    {
        "region": "ap-south-1",
        "function_name": "payment-processor",
    },
)
different_target_fingerprint = build_tool_call_fingerprint(
    "inspect_lambda_metrics",
    {
        "function_name": "notification-worker",
        "region": "ap-south-1",
    },
)

assert first_fingerprint == reordered_fingerprint
assert first_fingerprint != different_target_fingerprint

print("PASS tool-call fingerprint ignores argument ordering")

assert valid is False
assert reason == (
    "configured_timeout_seconds must be a positive number."
)

print("PASS invalid configured timeout is rejected")
