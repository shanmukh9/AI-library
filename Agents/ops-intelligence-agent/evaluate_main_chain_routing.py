import json

import basic_chain


CASES = [
    {
        "id": "accepted_alb_502",
        "text": (
            "ALB target health checks for checkout-service failed after "
            "deployment, and clients receive HTTP 502."
        ),
        "expected_status": "analysis_ready",
        "expected_llm_call": True,
        "expected_retry": False,
    },
    {
        "id": "conflicting_rds_504",
        "text": (
            "Checkout requests return HTTP 504 while RDS connections are "
            "exhausted."
        ),
        "expected_status": "clarification_required",
        "expected_llm_call": False,
        "expected_retry": False,
    },
    {
        "id": "unsupported_ec2_disk",
        "text": (
            "EC2 instance disk usage exceeded 95%, and application writes "
            "are failing after deployment."
        ),
        "expected_status": "no_coverage",
        "expected_llm_call": False,
        "expected_retry": False,
    },
    {
        "id": "healthy_lambda_metrics",
        "text": (
            "Lambda timeout rate is normal, no invocations failed, and CPU "
            "usage remains stable after deployment."
        ),
        "expected_status": "no_incident",
        "expected_llm_call": False,
        "expected_retry": False,
    },
    {
        "id": "adaptive_lambda_iam_conflict",
        "text": "Lambda timed out and logs show AccessDenied.",
        "expected_status": "clarification_required",
        "expected_llm_call": False,
        "expected_retry": True,
    },
]


def main():
    model_calls = 0

    def fake_chat_model(_messages):
        nonlocal model_calls
        model_calls += 1
        return json.dumps(
            {
                "root_cause": "Synthetic grounded smoke-test response.",
                "severity": "P1",
                "model_confidence": 0.9,
                "immediate_action": "Follow the accepted runbook evidence.",
            }
        )

    original_chat_model = basic_chain.call_chat_model
    basic_chain.call_chat_model = fake_chat_model
    passed = 0

    try:
        for case in CASES:
            calls_before = model_calls
            result = basic_chain.analyze_alert(
                {
                    "text": case["text"],
                    "service": "smoke-test",
                    "severity_hint": "P1",
                }
            )
            llm_called = model_calls > calls_before
            retry_used = result["retrieval"]["adaptive_retry_used"]
            case_passed = (
                result["status"] == case["expected_status"]
                and llm_called == case["expected_llm_call"]
                and retry_used == case["expected_retry"]
            )
            passed += int(case_passed)

            print(f"\n{'PASS' if case_passed else 'FAIL'} {case['id']}")
            print(
                f"Status: expected={case['expected_status']}, "
                f"actual={result['status']}"
            )
            print(
                f"LLM called: expected={case['expected_llm_call']}, "
                f"actual={llm_called}"
            )
            print(
                f"Adaptive retry: expected={case['expected_retry']}, "
                f"actual={retry_used}"
            )
            print(f"Decision: {result['retrieval']['decision']}")
    finally:
        basic_chain.call_chat_model = original_chat_model

    print("\nSummary")
    print(f"Cases passed: {passed}/{len(CASES)}")
    print(f"LLM calls: {model_calls}")
    print("Expected LLM calls: 1")
    raise SystemExit(0 if passed == len(CASES) and model_calls == 1 else 1)


if __name__ == "__main__":
    main()
