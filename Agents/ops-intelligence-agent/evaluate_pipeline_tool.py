from agent_loop import run_pipeline_tool




result = run_pipeline_tool(
    {"status": "no_incident"},
    action_evidence_complete=False,
    human_approved=False,
)

assert result["status"] == "not_applicable"
assert result["tool"] is None
assert "result" not in result

print("PASS no incident never enters the action stage")


accepted_result = {
    "status": "analysis_ready",
    "retrieval": {
        "decision": "accept",
        "accepted_sources": ["lambda-timeout.md"],
    },
    "analysis": {
        "tool_proposal": None,
    },
}

no_action = run_pipeline_tool(
    accepted_result,
    action_evidence_complete=False,
    human_approved=False,
)

assert no_action["status"] == "no_action"
assert no_action["tool"] is None
assert "result" not in no_action

print("PASS accepted analysis may intentionally propose no tool")


mismatched_result = {
    "status": "analysis_ready",
    "retrieval": {
        "decision": "accept",
        "accepted_sources": ["lambda-timeout.md"],
    },
    "analysis": {
        "tool_proposal": {
            "tool_name": "inspect_lambda_metrics",
            "tool_arguments": {
                "function_name": "payment-processor",
            },
            "rationale": "Investigate permission failures.",
            "evidence_refs": ["iam-accessdenied.md"],
        },
    },
}

mismatched = run_pipeline_tool(
    mismatched_result,
    action_evidence_complete=False,
    human_approved=False,
)

assert mismatched["status"] == "blocked"
assert mismatched["reason"] == (
    "Tool proposal references evidence that was not accepted."
)
assert "result" not in mismatched

print("PASS proposal citing unaccepted evidence is blocked")


matching_result = {
    "status": "analysis_ready",
    "retrieval": {
        "decision": "accept",
        "accepted_sources": ["lambda-timeout.md"],
    },
    "analysis": {
        "tool_proposal": {
            "tool_name": "inspect_lambda_metrics",
            "tool_arguments": {
                "function_name": "payment-processor",
            },
            "rationale": "Inspect whether duration approaches the timeout.",
            "evidence_refs": ["lambda-timeout.md"],
        },
    },
}

executed = run_pipeline_tool(
    matching_result,
    action_evidence_complete=False,
    human_approved=False,
)

assert executed["status"] == "executed"
assert executed["tool"] == "inspect_lambda_metrics"
assert executed["result"]["mode"] == "simulation"
assert executed["result"]["function"] == "payment-processor"

print("PASS grounded inspection reaches the simulated handler")
