from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "cause_intent",
        "query": "What caused the Lambda timeout failure?",
        "expected_section": "Probable Causes",
    },
    {
        "name": "action_intent",
        "query": "What should I do immediately for the Lambda timeout failure?",
        "expected_section": "Immediate Actions",
    },
    {
        "name": "symptom_intent",
        "query": "What symptoms confirm the Lambda timeout failure?",
        "expected_section": "Symptoms",
    },
]


def evaluate_mode(use_reranking):
    mode = "reranked" if use_reranking else "vector"
    top_1_hits = 0

    print(f"\nRanking mode: {mode}")
    for case in TEST_CASES:
        results = search_runbooks(
            case["query"],
            top_k=3,
            min_score=DEFAULT_MIN_SCORE,
            metadata_filters={"platform": "aws-lambda"},
            metadata_fallback=False,
            use_reranking=use_reranking,
        )
        top_result = results[0] if results else None
        actual_section = top_result["section"] if top_result else None
        passed = actual_section == case["expected_section"]
        if passed:
            top_1_hits += 1

        print(f"\n{'PASS' if passed else 'FAIL'} {case['name']}")
        print(f"Expected section: {case['expected_section']}")
        print(f"Actual section: {actual_section or 'no evidence'}")
        if top_result:
            print(f"Vector score: {top_result['similarity_score']:.4f}")
            print(f"Rerank bonus: {top_result['rerank_bonus']:.2f}")
            print(f"Final score: {top_result['score']:.4f}")

    print(f"\n{mode.title()} Top-1: {top_1_hits}/{len(TEST_CASES)}")
    return top_1_hits


vector_hits = evaluate_mode(use_reranking=False)
reranked_hits = evaluate_mode(use_reranking=True)

print("\nSummary")
print(f"Vector-only Top-1: {vector_hits}/{len(TEST_CASES)}")
print(f"Reranked Top-1: {reranked_hits}/{len(TEST_CASES)}")
