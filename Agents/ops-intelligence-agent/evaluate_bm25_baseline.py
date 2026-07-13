from bm25_retriever import bm25_search
from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "exact_http_504",
        "query": "checkout HTTP 504 gateway timeout",
        "expected_source": "http-504-gateway-timeout.md",
        "lesson": "Exact status codes should be easy for lexical search.",
    },
    {
        "name": "exact_alb_502",
        "query": "ALB 502 health checks failing",
        "expected_source": "alb-502-health-checks.md",
        "lesson": "Exact error code plus service terms should rank strongly.",
    },
    {
        "name": "exact_oomkilled",
        "query": "pod OOMKilled",
        "expected_source": "kubernetes-oomkill.md",
        "lesson": "Rare operational tokens are BM25-friendly.",
    },
    {
        "name": "exact_lambda_timeout",
        "query": "lambda timeout failure",
        "expected_source": "lambda-timeout.md",
        "lesson": "Shared incident vocabulary works well.",
    },
    {
        "name": "exact_rds_connections",
        "query": "RDS max database connections reached",
        "expected_source": "rds-connection-pool.md",
        "lesson": "Database connection terms should retrieve the RDS runbook.",
    },
    {
        "name": "semantic_bad_gateway",
        "query": "checkout throwing bad gateway",
        "expected_source": "alb-502-health-checks.md",
        "lesson": "Semantic phrasing may need vector search, expansion, or richer runbook wording.",
    },
    {
        "name": "semantic_api_slow",
        "query": "api is slow",
        "expected_source": "api-cpu-saturation.md",
        "lesson": "Short vague queries are harder for exact keyword search.",
    },
    {
        "name": "iam_access_denied_after_deploy",
        "query": "payment service AccessDenied after deploy",
        "expected_source": "iam-accessdenied.md",
        "lesson": "Missing incident-family knowledge should be added as runbook coverage, not forced into the nearest neighbor.",
    },
]


def sources(results):
    return [result["source"] for result in results]


def summarize_result(results, expected_source):
    result_sources = sources(results)
    top_1 = bool(results) and results[0]["source"] == expected_source
    top_3 = expected_source in result_sources
    return top_1, top_3


def evaluate_bm25():
    top_1_hits = 0
    top_3_hits = 0
    details = []

    for case in TEST_CASES:
        results = bm25_search(case["query"], top_k=3)
        top_1, top_3 = summarize_result(results, case["expected_source"])
        top_1_hits += int(top_1)
        top_3_hits += int(top_3)
        details.append((case, results, top_1, top_3))

    return top_1_hits, top_3_hits, details


def evaluate_vector():
    top_1_hits = 0
    top_3_hits = 0
    details = []

    try:
        for case in TEST_CASES:
            results = search_runbooks(
                case["query"],
                top_k=3,
                min_score=DEFAULT_MIN_SCORE,
                use_expansion=True,
                use_reranking=True,
                reranking_query=case["query"],
            )
            top_1, top_3 = summarize_result(results, case["expected_source"])
            top_1_hits += int(top_1)
            top_3_hits += int(top_3)
            details.append((case, results, top_1, top_3))
    except RuntimeError as exc:
        print(f"Vector comparison skipped: {exc}")
        return None

    return top_1_hits, top_3_hits, details


def print_details(label, details):
    print()
    print(label)
    for case, results, top_1, top_3 in details:
        status = "PASS" if top_1 else "REVIEW" if top_3 else "FAIL"
        print(f"\n{status} {case['name']}")
        print(f"Query: {case['query']}")
        print(f"Expected: {case['expected_source']}")
        print(f"Lesson: {case['lesson']}")
        if not results:
            print("Retrieved: no evidence")
            continue
        for rank, result in enumerate(results, start=1):
            marker = "*" if result["source"] == case["expected_source"] else " "
            score_label = (
                "bm25"
                if "matched_terms" in result
                else "vector"
            )
            score = result.get("similarity_score", result["score"])
            print(
                f" {marker} {rank}. {result['source']} / {result['section']} "
                f"({score_label}={score:.4f})"
            )


bm25_top_1, bm25_top_3, bm25_details = evaluate_bm25()
vector_evaluation = evaluate_vector()

print("BM25 vs Vector Retrieval Baseline")
print(f"Cases: {len(TEST_CASES)}")
print()
print(
    "BM25-only Top-1: "
    f"{bm25_top_1}/{len(TEST_CASES)} "
    f"({(bm25_top_1 / len(TEST_CASES)) * 100:.1f}%)"
)
print(
    "BM25-only Top-3: "
    f"{bm25_top_3}/{len(TEST_CASES)} "
    f"({(bm25_top_3 / len(TEST_CASES)) * 100:.1f}%)"
)

if vector_evaluation:
    vector_top_1, vector_top_3, vector_details = vector_evaluation
    print(
        "Vector+Expansion+Rerank Top-1: "
        f"{vector_top_1}/{len(TEST_CASES)} "
        f"({(vector_top_1 / len(TEST_CASES)) * 100:.1f}%)"
    )
    print(
        "Vector+Expansion+Rerank Top-3: "
        f"{vector_top_3}/{len(TEST_CASES)} "
        f"({(vector_top_3 / len(TEST_CASES)) * 100:.1f}%)"
    )
else:
    vector_details = []

print_details("BM25 details", bm25_details)
if vector_details:
    print_details("Vector details", vector_details)
