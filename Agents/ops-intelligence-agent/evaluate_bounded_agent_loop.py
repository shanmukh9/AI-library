import agent_loop
from agent_loop import run_bounded_agent_loop


def build_proposal(function_name: str) -> dict:
    return {
        "tool_name": "inspect_lambda_metrics",
        "tool_arguments": {
            "function_name": function_name,
        },
        "rationale": "Inspect whether duration approaches the timeout.",
        "evidence_refs": ["lambda-timeout.md"],
    }


def build_pipeline_result(function_name: str = "payment-processor") -> dict:
    return {
        "status": "analysis_ready",
        "retrieval": {
            "decision": "accept",
            "accepted_sources": ["lambda-timeout.md"],
        },
        "analysis": {
            "tool_proposal": build_proposal(function_name),
        },
    }


provider_calls = 0


def provider_must_not_run(history: list[dict]) -> dict:
    global provider_calls
    provider_calls += 1
    return build_proposal("unexpected-function")


not_applicable = run_bounded_agent_loop(
    {"status": "no_incident"},
    next_proposal_provider=provider_must_not_run,
)

assert not_applicable["status"] == "not_applicable"
assert not_applicable["steps_used"] == 0
assert provider_calls == 0

print("PASS no incident stops before planning or tool execution")


escalated = run_bounded_agent_loop(
    build_pipeline_result(),
    next_proposal_provider=provider_must_not_run,
)

assert escalated["status"] == "escalation_required"
assert escalated["steps_used"] == 1
assert len(escalated["history"]) == 1
assert escalated["history"][0]["status"] == "executed"
assert provider_calls == 0

print("PASS near-timeout observation stops and escalates after one step")


original_follow_up = agent_loop.decide_lambda_tool_follow_up
original_handler = agent_loop.TOOL_HANDLERS["inspect_lambda_metrics"]
handler_calls = 0


def continue_after_observation(derived_facts: dict) -> dict:
    return {
        "decision": "continue",
        "reason": "Another bounded inspection is required.",
        "automatic_action": None,
    }


def counting_handler(*, function_name: str) -> dict:
    global handler_calls
    handler_calls += 1
    return original_handler(function_name=function_name)


agent_loop.decide_lambda_tool_follow_up = continue_after_observation
agent_loop.TOOL_HANDLERS["inspect_lambda_metrics"] = counting_handler

try:
    next_targets = iter(["checkout-processor", "must-not-be-requested"])
    continuation_requests = 0

    def provide_distinct_proposal(history: list[dict]) -> dict:
        global continuation_requests
        continuation_requests += 1
        return build_proposal(next(next_targets))

    bounded = run_bounded_agent_loop(
        build_pipeline_result(),
        next_proposal_provider=provide_distinct_proposal,
        max_steps=2,
    )

    assert bounded["status"] == "step_limit_reached"
    assert bounded["steps_used"] == 2
    assert len(bounded["history"]) == 2
    assert handler_calls == 2
    assert continuation_requests == 1

    print("PASS shared step budget stops continuation after two executions")

    handler_calls = 0
    duplicate_requests = 0

    def provide_duplicate_proposal(history: list[dict]) -> dict:
        global duplicate_requests
        duplicate_requests += 1
        return build_proposal("payment-processor")

    duplicate = run_bounded_agent_loop(
        build_pipeline_result(),
        next_proposal_provider=provide_duplicate_proposal,
        max_steps=2,
    )

    assert duplicate["status"] == "duplicate_rejected"
    assert duplicate["steps_used"] == 2
    assert len(duplicate["history"]) == 2
    assert duplicate["history"][1]["tool_executed"] is False
    assert handler_calls == 1
    assert duplicate_requests == 1

    print("PASS repeated proposal is rejected without duplicate execution")
finally:
    agent_loop.decide_lambda_tool_follow_up = original_follow_up
    agent_loop.TOOL_HANDLERS["inspect_lambda_metrics"] = original_handler
