from bm25_retriever import bm25_search
from hybrid_retriever import hybrid_search_rrf
from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "exact_http_504",
        "query": "checkout HTTP 504 gateway timeout",
        "expected_source": "http-504-gateway-timeout.md",
    },
    {
        "name": "exact_alb_502",
        "query": "ALB 502 health checks failing",
        "expected_source": "alb-502-health-checks.md",
    },
    {
        "name": "exact_oomkilled",
        "query": "pod OOMKilled",
        "expected_source": "kubernetes-oomkill.md",
    },
    {
        "name": "exact_lambda_timeout",
        "query": "lambda timeout failure",
        "expected_source": "lambda-timeout.md",
    },
    {
        "name": "exact_rds_connections",
        "query": "RDS max database connections reached",
        "expected_source": "rds-connection-pool.md",
    },
    {
        "name": "semantic_bad_gateway",
        "query": "checkout throwing bad gateway",
        "expected_source": "alb-502-health-checks.md",
    },
    {
        "name": "semantic_api_slow",
        "query": "api is slow",
        "expected_source": "api-cpu-saturation.md",
    },
    {
        "name": "iam_access_denied_after_deploy",
        "query": "payment service AccessDenied after deploy",
        "expected_source": "iam-accessdenied.md",
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
    details = []

    for case in TEST_CASES:
        try:
            results = search_fn(case["query"])
        except RuntimeError as exc:
            print(f"{name} skipped after retrieval error: {exc}")
            return None
        sources = [result["source"] for result in results]
        top_1 = bool(results) and results[0]["source"] == case["expected_source"]
        top_3 = case["expected_source"] in sources
        top_1_hits += int(top_1)
        top_3_hits += int(top_3)
        details.append((case, results, top_1, top_3))

    return {
        "name": name,
        "top_1_hits": top_1_hits,
        "top_3_hits": top_3_hits,
        "details": details,
    }


def print_summary(evaluation):
    total = len(TEST_CASES)
    print(
        f"{evaluation['name']} Top-1: "
        f"{evaluation['top_1_hits']}/{total} "
        f"({(evaluation['top_1_hits'] / total) * 100:.1f}%)"
    )
    print(
        f"{evaluation['name']} Top-3: "
        f"{evaluation['top_3_hits']}/{total} "
        f"({(evaluation['top_3_hits'] / total) * 100:.1f}%)"
    )


def print_details(evaluation):
    print()
    print(evaluation["name"])
    for case, results, top_1, top_3 in evaluation["details"]:
        status = "PASS" if top_1 else "REVIEW" if top_3 else "FAIL"
        print(f"\n{status} {case['name']}")
        print(f"Query: {case['query']}")
        print(f"Expected: {case['expected_source']}")
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
