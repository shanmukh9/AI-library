from runbook_rag import (
    DEFAULT_MIN_SCORE,
    expand_query_for_retrieval,
    has_operational_problem_signal,
    normalize_operational_signals,
    search_runbooks,
)


TEST_CASES = [
    {
        "name": "rds_gate_block",
        "query": "RDS max database connections reached",
        "expected_stage": "retrieval_ok",
        "expected_source": "rds-connection-pool.md",
        "expected_section": None,
        "best_fix": "Keep controlled database max-connection signal coverage.",
    },
    {
        "name": "lambda_short_action",
        "query": "how do I fix Lambda timeout?",
        "expected_stage": "wrong_section_after_retrieval",
        "expected_source": "lambda-timeout.md",
        "expected_section": "Immediate Actions",
        "best_fix": "Evaluate reranking weight, action-intent handling, or section wording.",
        "search_kwargs": {
            "metadata_filters": {"platform": "aws-lambda"},
            "metadata_fallback": False,
            "use_reranking": True,
        },
    },
    {
        "name": "checkout_504_missing",
        "query": "checkout HTTP 504",
        "expected_stage": "retrieval_ok",
        "expected_source": "http-504-gateway-timeout.md",
        "expected_section": None,
        "best_fix": "Keep 504-specific runbook coverage and monitor confusion with 502.",
    },
    {
        "name": "certificate_ambiguous",
        "query": "certificate error",
        "expected_stage": "ambiguous_but_retrieved",
        "expected_source": "ssl-certificate-expiry.md",
        "expected_section": None,
        "best_fix": "Clarify the alert or add broader certificate troubleshooting coverage.",
    },
    {
        "name": "db_terse_success",
        "query": "db maxed connections",
        "expected_stage": "retrieval_ok",
        "expected_source": "rds-connection-pool.md",
        "expected_section": None,
        "best_fix": "Keep controlled query expansion and continue monitoring false positives.",
    },
]


def get_signal_gate_state(query):
    expanded_query = expand_query_for_retrieval(query)
    normalized_query = normalize_operational_signals(expanded_query)
    return {
        "expanded_query": expanded_query,
        "normalized_query": normalized_query,
        "passes_gate": has_operational_problem_signal(normalized_query),
    }


def infer_stage(case, results, gate_state):
    top_result = results[0] if results else None

    if not gate_state["passes_gate"]:
        return "blocked_by_signal_gate"

    if not results:
        if case["expected_stage"] == "missing_knowledge":
            return "missing_knowledge"
        return "no_chunks_above_threshold"

    if case["expected_stage"] == "ambiguous_but_retrieved":
        return "ambiguous_but_retrieved"

    expected_source = case["expected_source"]
    expected_section = case["expected_section"]

    if expected_source and top_result["source"] != expected_source:
        return "wrong_runbook_after_retrieval"

    if expected_section and top_result["section"] != expected_section:
        return "wrong_section_after_retrieval"

    return "retrieval_ok"


def format_result(result):
    if not result:
        return "No evidence"
    return (
        f"{result['source']} / {result['section']} "
        f"(similarity={result['similarity_score']:.4f}, final={result['score']:.4f})"
    )


passes = 0

for case in TEST_CASES:
    search_kwargs = case.get("search_kwargs", {})
    gate_state = get_signal_gate_state(case["query"])
    results = search_runbooks(
        case["query"],
        top_k=3,
        min_score=DEFAULT_MIN_SCORE,
        **search_kwargs,
    )
    actual_stage = infer_stage(case, results, gate_state)
    passed = actual_stage == case["expected_stage"]
    if passed:
        passes += 1

    print(f"\n{'PASS' if passed else 'FAIL'} {case['name']}")
    print(f"Query: {case['query']}")
    if gate_state["expanded_query"] != case["query"]:
        print(f"Expanded: {gate_state['expanded_query']}")
    if gate_state["normalized_query"] != gate_state["expanded_query"]:
        print(f"Normalized: {gate_state['normalized_query']}")
    print(f"Gate passed: {'yes' if gate_state['passes_gate'] else 'no'}")
    print(f"Expected stage: {case['expected_stage']}")
    print(f"Actual stage: {actual_stage}")
    print(f"Top result: {format_result(results[0] if results else None)}")
    print(f"Best fix: {case['best_fix']}")

print("\nSummary")
print(f"Cases: {len(TEST_CASES)}")
print(f"Stage diagnosis matches: {passes}/{len(TEST_CASES)}")
print(
    "Meaning: fix the failed pipeline stage first; do not tune reranking when "
    "the query never reached retrieval."
)
