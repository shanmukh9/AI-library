from oia_agent import run_oia_agent


ALERT = {
    "id": "ALT002",
    "text": "Lambda function payment-processor timed out after 15 seconds.",
    "service": "lambda",
    "severity_hint": "P1",
}


def accepted_lambda_analysis(_alert):
    return {
        "status": "analysis_ready",
        "retrieval": {
            "decision": "accept",
            "accepted_sources": ["lambda-timeout.md"],
        },
        "analysis": {
            "root_cause": "Function duration is approaching its timeout.",
            "severity": "P1",
            "model_confidence": 0.9,
            "immediate_action": "Inspect Lambda duration and timeout metrics.",
            "tool_proposal": {
                "tool_name": "inspect_lambda_metrics",
                "rationale": "Confirm whether duration is approaching the timeout.",
                "evidence_refs": ["lambda-timeout.md"],
            },
        },
    }


def no_incident_analysis(_alert):
    return {
        "status": "no_incident",
        "retrieval": {
            "decision": "no_incident",
            "accepted_sources": [],
        },
        "analysis": None,
    }


def model_error_analysis(_alert):
    return {
        "status": "model_error",
        "retrieval": {
            "decision": "accept",
            "accepted_sources": ["lambda-timeout.md"],
        },
        "analysis": None,
    }


executed = run_oia_agent(ALERT, analyzer=accepted_lambda_analysis)

assert executed["alert_id"] == "ALT002"
assert executed["analysis"]["status"] == "analysis_ready"
assert executed["action"]["status"] == "executed"
assert executed["action"]["tool"] == "inspect_lambda_metrics"
assert executed["action"]["result"]["mode"] == "simulation"

print("PASS accepted grounded analysis executes the diagnostic tool")


not_applicable = run_oia_agent(ALERT, analyzer=no_incident_analysis)

assert not_applicable["analysis"]["status"] == "no_incident"
assert not_applicable["action"]["status"] == "not_applicable"
assert "result" not in not_applicable["action"]

print("PASS no incident never enters tool execution")


model_failure = run_oia_agent(ALERT, analyzer=model_error_analysis)

assert model_failure["analysis"]["status"] == "model_error"
assert model_failure["action"]["status"] == "blocked"
assert model_failure["action"]["reason"] == (
    "Analysis did not complete successfully."
)
assert "result" not in model_failure["action"]

print("PASS model failure blocks tool execution")
