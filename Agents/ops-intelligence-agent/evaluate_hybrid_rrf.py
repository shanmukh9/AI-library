from bm25_retriever import bm25_search
from evidence_acceptance import assess_evidence
from hybrid_retriever import hybrid_search_rrf
from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "exact_http_504",
        "query": "checkout HTTP 504 gateway timeout",
        "expected_source": "http-504-gateway-timeout.md",
        "expected_decision": "accept",
    },
    {
        "name": "exact_alb_502",
        "query": "ALB 502 health checks failing",
        "expected_source": "alb-502-health-checks.md",
        "expected_decision": "accept",
    },
    {
        "name": "exact_oomkilled",
        "query": "pod OOMKilled",
        "expected_source": "kubernetes-oomkill.md",
        "expected_decision": "accept",
    },
    {
        "name": "exact_lambda_timeout",
        "query": "lambda timeout failure",
        "expected_source": "lambda-timeout.md",
        "expected_decision": "accept",
    },
    {
        "name": "exact_rds_connections",
        "query": "RDS max database connections reached",
        "expected_source": "rds-connection-pool.md",
        "expected_decision": "accept",
    },
    {
        "name": "semantic_bad_gateway",
        "query": "checkout throwing bad gateway",
        "expected_source": "alb-502-health-checks.md",
        "expected_decision": "accept",
    },
    {
        "name": "semantic_api_slow",
        "query": "api is slow",
        "expected_source": "api-cpu-saturation.md",
        "expected_decision": "accept",
    },
    {
        "name": "iam_access_denied_after_deploy",
        "query": "payment service AccessDenied after deploy",
        "expected_source": "iam-accessdenied.md",
        "expected_decision": "accept",
    },
    {
        "name": "unknown_kafka_lag",
        "query": "Kafka consumer lag rising after deployment",
        "expected_source": None,
        "expected_decision": "no_coverage",
    },
    {
        "name": "unknown_redis_replication",
        "query": "Redis replica synchronization failed",
        "expected_source": None,
        "expected_decision": "no_coverage",
    },
    {
        "name": "ambiguous_certificate_error",
        "query": "certificate error",
        "expected_source": None,
        "expected_decision": "clarify",
    },
    {
        "name": "ambiguous_crashloopbackoff",
        "query": "pod CrashLoopBackOff, what should I check first?",
        "expected_source": None,
        "expected_decision": "clarify",
    },
]


def vector_search(query):
    return search_runbooks(
        query,
        top_k=3,
        min_score=DEFAULT_MIN_SCORE,
        use_expansion=True,
        use_reranking=True,
        reranking_query=query,
    )


def evaluate_method(name, search_fn):
    top_1_hits = 0
    top_3_hits = 0
    positive_count = 0
    negative_rejections = 0
    negative_count = 0
    details = []

    for case in TEST_CASES:
        try:
            results = search_fn(case["query"])
        except RuntimeError as exc:
            print(f"{name} skipped after retrieval error: {exc}")
            return None
        sources = [result["source"] for result in results]
        expected_source = case["expected_source"]

        if expected_source is None:
            negative_count += 1
            rejected = not results
            negative_rejections += int(rejected)
            details.append((case, results, False, False, rejected))
            continue

        positive_count += 1
        top_1 = bool(results) and results[0]["source"] == expected_source
        top_3 = expected_source in sources
        top_1_hits += int(top_1)
        top_3_hits += int(top_3)
        details.append((case, results, top_1, top_3, False))

    return {
        "name": name,
        "top_1_hits": top_1_hits,
        "top_3_hits": top_3_hits,
        "positive_count": positive_count,
        "negative_rejections": negative_rejections,
        "negative_count": negative_count,
        "details": details,
    }


def print_summary(evaluation):
    positive_count = evaluation["positive_count"]
    negative_count = evaluation["negative_count"]
    print(
        f"{evaluation['name']} Top-1: "
        f"{evaluation['top_1_hits']}/{positive_count} "
        f"({(evaluation['top_1_hits'] / positive_count) * 100:.1f}%)"
    )
    print(
        f"{evaluation['name']} Top-3: "
        f"{evaluation['top_3_hits']}/{positive_count} "
        f"({(evaluation['top_3_hits'] / positive_count) * 100:.1f}%)"
    )
    print(
        f"{evaluation['name']} Negative rejection: "
        f"{evaluation['negative_rejections']}/{negative_count} "
        f"({(evaluation['negative_rejections'] / negative_count) * 100:.1f}%)"
    )


def print_details(evaluation):
    print()
    print(evaluation["name"])
    for case, results, top_1, top_3, rejected in evaluation["details"]:
        if case["expected_source"] is None:
            status = "PASS" if rejected else "FAIL"
        else:
            status = "PASS" if top_1 else "REVIEW" if top_3 else "FAIL"
        print(f"\n{status} {case['name']}")
        print(f"Query: {case['query']}")
        print(f"Expected: {case['expected_source'] or 'no evidence'}")
        if not results:
            print("Retrieved: no evidence")
            continue
        for rank, result in enumerate(results, start=1):
            marker = "*" if result["source"] == case["expected_source"] else " "
            if "rrf_score" in result:
                detail = (
                    f"rrf={result['rrf_score']:.5f}, "
                    f"by={'+'.join(result['retrieved_by'])}, "
                    f"v_rank={result['vector_rank'] or '-'}, "
                    f"b_rank={result['bm25_rank'] or '-'}"
                )
            elif "matched_terms" in result:
                detail = f"bm25={result['score']:.4f}"
            else:
                detail = f"vector={result.get('similarity_score', result['score']):.4f}"
            print(
                f" {marker} {rank}. {result['source']} / {result['section']} "
                f"({detail})"
            )


def evaluate_acceptance_gate(hybrid_evaluation):
    decision_hits = 0
    accepted_source_hits = 0
    accepted_case_count = 0
    details = []

    for case, results, _top_1, _top_3, _rejected in hybrid_evaluation["details"]:
        assessment = assess_evidence(case["query"], results)
        decision_correct = assessment["decision"] == case["expected_decision"]
        decision_hits += int(decision_correct)

        source_correct = None
        if case["expected_decision"] == "accept":
            accepted_case_count += 1
            source_correct = bool(assessment["evidence"]) and (
                assessment["evidence"][0]["source"] == case["expected_source"]
            )
            accepted_source_hits += int(source_correct)

        details.append((case, assessment, decision_correct, source_correct))

    return {
        "decision_hits": decision_hits,
        "case_count": len(hybrid_evaluation["details"]),
        "accepted_source_hits": accepted_source_hits,
        "accepted_case_count": accepted_case_count,
        "details": details,
    }


def print_acceptance_gate(evaluation):
    print()
    print("Evidence Acceptance Gate")
    print(
        f"Decision accuracy: {evaluation['decision_hits']}/{evaluation['case_count']} "
        f"({(evaluation['decision_hits'] / evaluation['case_count']) * 100:.1f}%)"
    )
    print(
        f"Accepted source accuracy: "
        f"{evaluation['accepted_source_hits']}/{evaluation['accepted_case_count']} "
        f"({(evaluation['accepted_source_hits'] / evaluation['accepted_case_count']) * 100:.1f}%)"
    )

    for case, assessment, decision_correct, source_correct in evaluation["details"]:
        source_passed = source_correct is not False
        status = "PASS" if decision_correct and source_passed else "FAIL"
        print(f"\n{status} {case['name']}")
        print(f"Query: {case['query']}")
        print(f"Expected decision: {case['expected_decision']}")
        print(f"Actual decision: {assessment['decision']}")
        print(f"Reason: {assessment['reason']}")
        if assessment["clarifying_question"]:
            print(f"Clarifying question: {assessment['clarifying_question']}")
        if assessment["evidence"]:
            top = assessment["evidence"][0]
            print(f"Accepted evidence: {top['source']} / {top['section']}")


evaluations = [
    evaluation
    for evaluation in [
        evaluate_method("Vector+Expansion+Rerank", vector_search),
        evaluate_method("BM25-only", lambda query: bm25_search(query, top_k=3)),
        evaluate_method("Hybrid RRF", lambda query: hybrid_search_rrf(query, top_k=3)),
    ]
    if evaluation
]

print("Hybrid RRF Retrieval Evaluation")
print(f"Cases: {len(TEST_CASES)}")
print()
for evaluation in evaluations:
    print_summary(evaluation)

for evaluation in evaluations:
    print_details(evaluation)

hybrid_evaluation = next(
    (
        evaluation
        for evaluation in evaluations
        if evaluation["name"] == "Hybrid RRF"
    ),
    None,
)
if hybrid_evaluation:
    print_acceptance_gate(evaluate_acceptance_gate(hybrid_evaluation))
