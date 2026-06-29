from runbook_rag import DEFAULT_MIN_SCORE, detect_query_intents, search_runbooks


INTENT_TO_SECTION = {
    "cause": "Probable Causes",
    "action": "Immediate Actions",
    "symptom": "Symptoms",
}

BASE_BONUSES = {
    "cause": 0.13,
    "action": 0.10,
    "symptom": 0.05,
}

ACTION_BONUS_CANDIDATES = [0.10, 0.12, 0.15, 0.20, 0.22, 0.25]

TEST_CASES = [
    {
        "name": "short_action_intent",
        "query": "how do I fix Lambda timeout?",
        "expected_section": "Immediate Actions",
    },
    {
        "name": "clear_action_intent",
        "query": "What should I do immediately for the Lambda timeout failure?",
        "expected_section": "Immediate Actions",
    },
    {
        "name": "cause_intent",
        "query": "What caused the Lambda timeout failure?",
        "expected_section": "Probable Causes",
    },
    {
        "name": "symptom_intent",
        "query": "What symptoms confirm the Lambda timeout failure?",
        "expected_section": "Symptoms",
    },
]


def rerank_with_bonus(results, query, action_bonus):
    intents = detect_query_intents(query)
    if not results or not intents:
        return results

    bonuses = {**BASE_BONUSES, "action": action_bonus}
    leading_source = max(results, key=lambda item: item["similarity_score"])["source"]
    reranked = []

    for result in results:
        bonus = 0.0
        for intent in intents:
            if (
                result["source"] == leading_source
                and result["section"] == INTENT_TO_SECTION[intent]
            ):
                bonus += bonuses[intent]
        reranked.append(
            {
                **result,
                "simulated_bonus": bonus,
                "simulated_score": result["similarity_score"] + bonus,
            }
        )

    return sorted(reranked, key=lambda item: item["simulated_score"], reverse=True)


def get_vector_results(query):
    return search_runbooks(
        query,
        top_k=5,
        min_score=DEFAULT_MIN_SCORE,
        metadata_filters={"platform": "aws-lambda"},
        metadata_fallback=False,
        use_reranking=False,
    )


print("Reranking sensitivity experiment")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print("Scope: aws-lambda runbook chunks only")

for action_bonus in ACTION_BONUS_CANDIDATES:
    hits = 0
    print(f"\nAction bonus candidate: {action_bonus:.2f}")

    for case in TEST_CASES:
        vector_results = get_vector_results(case["query"])
        reranked = rerank_with_bonus(vector_results, case["query"], action_bonus)
        top_result = reranked[0] if reranked else None
        actual_section = top_result["section"] if top_result else "no evidence"
        passed = actual_section == case["expected_section"]
        if passed:
            hits += 1

        print(
            f"  {'PASS' if passed else 'FAIL'} {case['name']}: "
            f"expected={case['expected_section']} actual={actual_section}"
        )
        if top_result:
            print(
                "       "
                f"vector={top_result['similarity_score']:.4f} "
                f"bonus={top_result['simulated_bonus']:.2f} "
                f"final={top_result['simulated_score']:.4f}"
            )

    print(f"  Top-1 expected-section hits: {hits}/{len(TEST_CASES)}")

print("\nInterpretation")
print(
    "If a larger bonus fixes one short action query, it may still be unsafe "
    "unless broader evals prove it does not promote the wrong section for other queries."
)
