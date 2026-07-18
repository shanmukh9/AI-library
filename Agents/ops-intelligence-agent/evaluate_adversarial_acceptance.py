from evidence_acceptance import assess_evidence
from hybrid_retriever import should_run_hybrid_retrieval
from runbook_rag import has_operational_problem_signal


ADVERSARIAL_CASES = [
    {
        "name": "negated_oomkilled",
        "query": "The pod restarted with exit code 1; it was not OOMKilled.",
        "retrieval_should_run": True,
        "expected_candidate_sources": ["kubernetes-oomkill.md"],
        "expected_decision": "clarify",
        "expected_accepted_source": None,
    },
    {
        "name": "negated_expansion_trigger",
        "query": "The pod was not memory killed.",
        "retrieval_should_run": False,
        "expected_candidate_sources": [],
        "expected_decision": "no_incident",
        "expected_accepted_source": None,
    },
    {
        "name": "healthy_database",
        "query": "Database connections are healthy and not exhausted.",
        "retrieval_should_run": False,
        "expected_candidate_sources": [],
        "expected_decision": "no_incident",
        "expected_accepted_source": None,
    },
    {
        "name": "conflicting_lambda_iam",
        "query": "Lambda timed out and logs show AccessDenied.",
        "retrieval_should_run": True,
        "expected_candidate_sources": [
            "lambda-timeout.md",
            "iam-accessdenied.md",
        ],
        "expected_decision": "clarify",
        "expected_accepted_source": None,
    },
    {
        "name": "conflicting_iam_lambda_reversed",
        "query": "Lambda timed out and logs show AccessDenied.",
        "retrieval_should_run": True,
        "expected_candidate_sources": [
            "iam-accessdenied.md",
            "lambda-timeout.md",
        ],
        "expected_decision": "clarify",
        "expected_accepted_source": None,
    },
    {
        "name": "unsupported_kafka",
        "query": "Kafka consumer lag is rising after deployment.",
        "retrieval_should_run": True,
        "expected_candidate_sources": [],
        "expected_decision": "no_coverage",
        "expected_accepted_source": None,
    },
]


def evaluate_signal_gate():
    passed = 0

    for case in ADVERSARIAL_CASES:
        actual = has_operational_problem_signal(case["query"])
        expected = case["retrieval_should_run"]
        matched = actual == expected
        passed += int(matched)

        print(f"{'PASS' if matched else 'FAIL'} {case['name']}")
        print(f"Expected retrieval: {expected}")
        print(f"Actual gate result: {actual}")
        print()

    print(f"Signal gate: {passed}/{len(ADVERSARIAL_CASES)}")


def evaluate_hybrid_entry_gate():
    passed = 0

    for case in ADVERSARIAL_CASES:
        actual = should_run_hybrid_retrieval(case["query"])
        expected = case["retrieval_should_run"]
        matched = actual == expected
        passed += int(matched)

        print(f"{'PASS' if matched else 'FAIL'} {case['name']}")
        print(f"Expected retrieval: {expected}")
        print(f"Actual hybrid entry result: {actual}")
        print()

    print(f"Hybrid entry gate: {passed}/{len(ADVERSARIAL_CASES)}")


def build_synthetic_candidates(sources):
    return [{"source": source} for source in sources]


def evaluate_acceptance_gate():
    passed = 0
    evaluated = 0

    for case in ADVERSARIAL_CASES:
        if not case["retrieval_should_run"]:
            continue

        candidates = build_synthetic_candidates(
            case["expected_candidate_sources"]
        )
        assessment = assess_evidence(case["query"], candidates)

        actual_decision = assessment["decision"]
        expected_decision = case["expected_decision"]

        accepted_source = (
            assessment["evidence"][0]["source"]
            if assessment["evidence"]
            else None
        )
        expected_source = case["expected_accepted_source"]

        decision_correct = actual_decision == expected_decision
        source_correct = accepted_source == expected_source
        matched = decision_correct and source_correct

        evaluated += 1
        passed += int(matched)

        print(f"{'PASS' if matched else 'FAIL'} {case['name']}")
        print(f"Expected decision: {expected_decision}")
        print(f"Actual decision: {actual_decision}")
        print(f"Expected accepted source: {expected_source}")
        print(f"Actual accepted source: {accepted_source}")
        print(f"Reason: {assessment['reason']}")
        print()

    print(f"Acceptance gate: {passed}/{evaluated}")


if __name__ == "__main__":
    print("Signal Gate")
    evaluate_signal_gate()

    print("\nHybrid Entry Gate")
    evaluate_hybrid_entry_gate()

    print("\nAcceptance Gate")
    evaluate_acceptance_gate()
