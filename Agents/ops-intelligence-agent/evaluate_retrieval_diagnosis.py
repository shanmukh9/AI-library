from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "missing_504_runbook",
        "query": "checkout HTTP 504",
        "expected_source": None,
        "expected_section": None,
        "diagnosis": "missing_knowledge",
        "best_fix": "Add a 504 gateway timeout runbook and an eval case.",
        "why": "504 is not the same incident pattern as the existing 502 runbook.",
        "search_kwargs": {},
    },
    {
        "name": "vague_certificate_error",
        "query": "certificate error",
        "expected_source": "ssl-certificate-expiry.md",
        "expected_section": None,
        "diagnosis": "vague_alert",
        "best_fix": "Clarify the alert or add a broader certificate troubleshooting runbook.",
        "why": "The phrase could mean expiry, trust chain, hostname mismatch, TLS, or renewal failure.",
        "search_kwargs": {},
        "review_required": True,
        "review_note": "Retrieval may return evidence, but the query is still ambiguous.",
    },
    {
        "name": "broad_crashloop_symptom",
        "query": "pod CrashLoopBackOff",
        "expected_source": "kubernetes-oomkill.md",
        "expected_section": None,
        "diagnosis": "broad_symptom",
        "best_fix": "Add a general CrashLoopBackOff runbook or require stronger cause signals.",
        "why": "CrashLoopBackOff is a Kubernetes state, not a single root cause.",
        "search_kwargs": {},
        "review_required": True,
        "review_note": "Retrieval may return OOM evidence, but CrashLoopBackOff alone is not enough cause evidence.",
    },
    {
        "name": "terse_db_connections",
        "query": "db maxed connections",
        "expected_source": "rds-connection-pool.md",
        "expected_section": None,
        "diagnosis": "terse_shorthand",
        "best_fix": "Use controlled query expansion.",
        "why": "Expansion maps short human wording to connection pool and max-connection terminology.",
        "search_kwargs": {},
    },
    {
        "name": "lambda_short_action_intent",
        "query": "how do I fix Lambda timeout?",
        "expected_source": "lambda-timeout.md",
        "expected_section": "Immediate Actions",
        "diagnosis": "right_runbook_but_reranking_not_strong_enough",
        "best_fix": "Review reranking weight, section wording, or action-intent query handling.",
        "why": "The query asks for remediation, but the broad Overview chunk can still outrank Immediate Actions.",
        "search_kwargs": {
            "metadata_filters": {"platform": "aws-lambda"},
            "metadata_fallback": False,
            "use_reranking": True,
        },
        "review_required": True,
        "review_note": "Reranking detects action intent, but the bonus may be too small for short fix-oriented wording.",
    },
    {
        "name": "lambda_clear_action_intent",
        "query": "What should I do immediately for the Lambda timeout failure?",
        "expected_source": "lambda-timeout.md",
        "expected_section": "Immediate Actions",
        "diagnosis": "right_runbook_action_intent",
        "best_fix": "Use intent-aware reranking.",
        "why": "The query clearly asks for immediate action, so the action section should rank first.",
        "search_kwargs": {
            "metadata_filters": {"platform": "aws-lambda"},
            "metadata_fallback": False,
            "use_reranking": True,
        },
    },
]


def did_case_pass(case, top_result):
    expected_source = case["expected_source"]
    expected_section = case["expected_section"]

    if expected_source is None:
        return top_result is None

    if top_result is None or top_result["source"] != expected_source:
        return False

    if expected_section and top_result["section"] != expected_section:
        return False

    return True


passes = 0
failures = 0
review_cases = 0

for case in TEST_CASES:
    results = search_runbooks(
        case["query"],
        top_k=3,
        min_score=DEFAULT_MIN_SCORE,
        **case["search_kwargs"],
    )
    top_result = results[0] if results else None
    passed = did_case_pass(case, top_result)
    review_required = case.get("review_required", False)
    if review_required:
        status = "REVIEW"
        review_cases += 1
    elif passed:
        status = "PASS"
        passes += 1
    else:
        status = "FAIL"
        failures += 1

    print(f"\n{status} {case['name']}")
    print(f"Query: {case['query']}")
    print(f"Diagnosis: {case['diagnosis']}")
    print(f"Best fix: {case['best_fix']}")
    print(f"Why: {case['why']}")
    if review_required:
        print(f"Review note: {case['review_note']}")

    print("Top result:")
    if top_result:
        print(f"  Source: {top_result['source']}")
        print(f"  Section: {top_result['section']}")
        print(f"  Similarity: {top_result['similarity_score']:.4f}")
        print(f"  Final score: {top_result['score']:.4f}")
        print(f"  Rerank bonus: {top_result.get('rerank_bonus', 0.0):.2f}")
    else:
        print("  No evidence")

print("\nSummary")
print(f"Cases: {len(TEST_CASES)}")
print(f"Passes: {passes}")
print(f"Failures: {failures}")
print(f"Review-required cases: {review_cases}")
print(
    "Meaning: review-required cases can pass mechanically, but they should still "
    "drive runbook coverage or clarification design."
)
