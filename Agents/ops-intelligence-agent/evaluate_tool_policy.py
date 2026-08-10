from tool_policy import TOOL_POLICIES, evaluate_tool_request


CASES = [
    {
        "name": "inspect_after_incident_acceptance",
        "tool": "inspect_lambda_metrics",
        "incident_accepted": True,
        "action_evidence_complete": False,
        "human_approved": False,
        "expected_allowed": True,
        "expected_reason": "Tool request satisfies policy.",
    },
    {
        "name": "inspect_without_incident_acceptance",
        "tool": "inspect_lambda_metrics",
        "incident_accepted": False,
        "action_evidence_complete": False,
        "human_approved": False,
        "expected_allowed": False,
        "expected_reason": "Accepted incident evidence is required.",
    },
    {
        "name": "rollback_without_action_evidence",
        "tool": "rollback_lambda_deployment",
        "incident_accepted": True,
        "action_evidence_complete": False,
        "human_approved": True,
        "expected_allowed": False,
        "expected_reason": "Action-specific evidence is required.",
    },
    {
        "name": "rollback_without_human_approval",
        "tool": "rollback_lambda_deployment",
        "incident_accepted": True,
        "action_evidence_complete": True,
        "human_approved": False,
        "expected_allowed": False,
        "expected_reason": "Human approval is required.",
    },
    {
        "name": "rollback_fully_authorized",
        "tool": "rollback_lambda_deployment",
        "incident_accepted": True,
        "action_evidence_complete": True,
        "human_approved": True,
        "expected_allowed": True,
        "expected_reason": "Tool request satisfies policy.",
    },
]


passed = 0

for case in CASES:
    allowed, reason = evaluate_tool_request(
        TOOL_POLICIES[case["tool"]],
        incident_accepted=case["incident_accepted"],
        action_evidence_complete=case["action_evidence_complete"],
        human_approved=case["human_approved"],
    )

    correct = (
        allowed == case["expected_allowed"]
        and reason == case["expected_reason"]
    )

    print(f"{'PASS' if correct else 'FAIL'} {case['name']}")
    print(f"Allowed: expected={case['expected_allowed']}, actual={allowed}")
    print(f"Reason: {reason}\n")

    if correct:
        passed += 1

print(f"Summary: {passed}/{len(CASES)}")
raise SystemExit(0 if passed == len(CASES) else 1)