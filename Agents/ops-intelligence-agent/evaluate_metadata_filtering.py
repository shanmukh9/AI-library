from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "correct_lambda_platform",
        "query": "payment processor timeout failure",
        "metadata_filters": {"platform": "aws-lambda"},
        "strict_expected": "lambda-timeout.md",
        "fallback_expected": "lambda-timeout.md",
        "fallback_should_activate": False,
    },
    {
        "name": "incorrect_kubernetes_platform",
        "query": "payment processor timeout failure",
        "metadata_filters": {"platform": "kubernetes"},
        "strict_expected": None,
        "fallback_expected": "lambda-timeout.md",
        "fallback_should_activate": True,
    },
    {
        "name": "unknown_platform",
        "query": "payment processor timeout failure",
        "metadata_filters": {"platform": "aws-ecs"},
        "strict_expected": None,
        "fallback_expected": "lambda-timeout.md",
        "fallback_should_activate": True,
    },
]


def evaluate_mode(mode):
    fallback_enabled = mode == "fallback"
    passed_cases = 0

    print(f"\nMetadata mode: {mode}")
    for case in TEST_CASES:
        results = search_runbooks(
            case["query"],
            top_k=3,
            min_score=DEFAULT_MIN_SCORE,
            metadata_filters=case["metadata_filters"],
            metadata_fallback=fallback_enabled,
        )
        actual_source = results[0]["source"] if results else None
        fallback_used = bool(
            results and results[0].get("metadata_fallback_used")
        )
        expected_source = case[f"{mode}_expected"]
        expected_fallback = (
            case["fallback_should_activate"] if fallback_enabled else False
        )
        passed = (
            actual_source == expected_source
            and fallback_used == expected_fallback
        )
        if passed:
            passed_cases += 1

        print(f"\n{'PASS' if passed else 'FAIL'} {case['name']}")
        print(f"Filters: {case['metadata_filters']}")
        print(f"Expected source: {expected_source or 'no evidence'}")
        print(f"Actual source: {actual_source or 'no evidence'}")
        print(f"Fallback used: {'yes' if fallback_used else 'no'}")

    print(f"\n{mode.title()} result: {passed_cases}/{len(TEST_CASES)} passed")
    return passed_cases


strict_passes = evaluate_mode("strict")
fallback_passes = evaluate_mode("fallback")

print("\nSummary")
print(f"Strict policy: {strict_passes}/{len(TEST_CASES)}")
print(f"Fallback policy: {fallback_passes}/{len(TEST_CASES)}")
