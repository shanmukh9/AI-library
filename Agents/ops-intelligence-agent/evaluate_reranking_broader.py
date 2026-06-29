from runbook_rag import (
    DEFAULT_MIN_SCORE,
    detect_query_intents,
    expand_query_for_retrieval,
    has_operational_problem_signal,
    normalize_operational_signals,
    search_runbooks,
)


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

ACTION_BONUS_CANDIDATES = [0.10, 0.15, 0.20, 0.22, 0.25]

RUNBOOK_CASES = [
    {
        "name": "lambda_timeout",
        "platform": "aws-lambda",
        "topic": "Lambda timeout failure",
    },
    {
        "name": "kubernetes_oomkill",
        "platform": "kubernetes",
        "topic": "Kubernetes OOMKilled pod",
    },
    {
        "name": "rds_connections",
        "platform": "aws-rds",
        "topic": "RDS max database connections reached",
    },
    {
        "name": "alb_502",
        "platform": "aws-alb",
        "topic": "ALB 502 health check failure",
    },
]

INTENT_QUERIES = [
    {
        "intent": "action",
        "template": "How do I fix {topic}?",
        "expected_section": "Immediate Actions",
    },
    {
        "intent": "action",
        "template": "What should I do immediately for {topic}?",
        "expected_section": "Immediate Actions",
    },
    {
        "intent": "cause",
        "template": "What caused {topic}?",
        "expected_section": "Probable Causes",
    },
    {
        "intent": "symptom",
        "template": "What symptoms confirm {topic}?",
        "expected_section": "Symptoms",
    },
]


def rerank_with_action_bonus(results, query, action_bonus):
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


def search_vector_candidates(query, platform):
    return search_runbooks(
        query,
        top_k=5,
        min_score=DEFAULT_MIN_SCORE,
        metadata_filters={"platform": platform},
        metadata_fallback=False,
        use_reranking=False,
    )


def explain_empty_result(query):
    expanded_query = expand_query_for_retrieval(query)
    normalized_query = normalize_operational_signals(expanded_query)
    if not has_operational_problem_signal(normalized_query):
        return "blocked_by_signal_gate"
    return "no_chunks_above_min_score_or_filter_removed_candidates"


def build_cases():
    cases = []
    for runbook in RUNBOOK_CASES:
        for intent_query in INTENT_QUERIES:
            cases.append(
                {
                    "name": f"{runbook['name']}_{intent_query['intent']}",
                    "query": intent_query["template"].format(topic=runbook["topic"]),
                    "platform": runbook["platform"],
                    "expected_section": intent_query["expected_section"],
                }
            )
    return cases


cases = build_cases()

print("Broader reranking safety experiment")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print(f"Runbooks tested: {len(RUNBOOK_CASES)}")
print(f"Cases per bonus: {len(cases)}")

for action_bonus in ACTION_BONUS_CANDIDATES:
    hits = 0
    misses = []

    for case in cases:
        vector_results = search_vector_candidates(case["query"], case["platform"])
        reranked = rerank_with_action_bonus(
            vector_results,
            case["query"],
            action_bonus,
        )
        top_result = reranked[0] if reranked else None
        actual_section = top_result["section"] if top_result else "no evidence"
        passed = actual_section == case["expected_section"]

        if passed:
            hits += 1
        else:
            misses.append(
                {
                    **case,
                    "actual_section": actual_section,
                    "top_result": top_result,
                }
            )

    print(f"\nAction bonus candidate: {action_bonus:.2f}")
    print(f"Expected-section Top-1: {hits}/{len(cases)}")

    if misses:
        print("Misses:")
        for miss in misses:
            print(
                f"  - {miss['name']}: expected={miss['expected_section']} "
                f"actual={miss['actual_section']}"
            )
            top_result = miss["top_result"]
            if top_result:
                print(
                    "    "
                    f"vector={top_result['similarity_score']:.4f} "
                    f"bonus={top_result['simulated_bonus']:.2f} "
                    f"final={top_result['simulated_score']:.4f}"
                )
            else:
                print(f"    empty_reason={explain_empty_result(miss['query'])}")
            print(f"    query={miss['query']}")
    else:
        print("Misses: none")

print("\nInterpretation")
print(
    "A bonus is safer only if it improves action-intent cases without breaking "
    "cause or symptom ranking across multiple runbooks."
)
