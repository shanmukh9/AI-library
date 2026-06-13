from runbook_rag import DEFAULT_MIN_SCORE, search_runbooks


TEST_CASES = [
    {
        "name": "api_cpu_saturation",
        "query": "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes",
        "expected_source": "api-cpu-saturation.md",
    },
    {
        "name": "lambda_timeout",
        "query": "Lambda function payment-processor timed out after 15 seconds, 47 consecutive failures",
        "expected_source": "lambda-timeout.md",
    },
    {
        "name": "kubernetes_oomkill",
        "query": "Kubernetes pod crash-looping on auth-service because it was OOMKilled repeatedly",
        "expected_source": "kubernetes-oomkill.md",
    },
    {
        "name": "database_pool_exhausted",
        "query": "RDS connection pool exhausted on orders-db with max database connections reached",
        "expected_source": "rds-connection-pool.md",
    },
    {
        "name": "alb_502_checkout",
        "query": "ALB health checks failing and 502 responses increasing on checkout service",
        "expected_source": "alb-502-health-checks.md",
    },
    {
        "name": "ssl_certificate_expiry",
        "query": "SSL certificate for www.example.com expiring in 3 days",
        "expected_source": "ssl-certificate-expiry.md",
    },
    {
        "name": "terse_kubernetes_memory_killed",
        "query": "auth pod memory killed repeatedly",
        "expected_source": "kubernetes-oomkill.md",
    },
    {
        "name": "terse_api_cpu_hot",
        "query": "api cpu hot",
        "expected_source": "api-cpu-saturation.md",
    },
    {
        "name": "negative_password_reset",
        "query": "employee laptop password reset request",
        "expected_source": None,
    },
    {
        "name": "negative_lambda_ok",
        "query": "lambda ok",
        "expected_source": None,
    }
]


positive_cases = [case for case in TEST_CASES if case["expected_source"]]
negative_cases = [case for case in TEST_CASES if not case["expected_source"]]
top_1_hits = 0
top_3_hits = 0
negative_passes = 0

for case in TEST_CASES:
    results = search_runbooks(case["query"], top_k=3, min_score=DEFAULT_MIN_SCORE)
    sources = [result["source"] for result in results]
    expected_source = case["expected_source"]
    is_negative_case = expected_source is None
    top_1_match = bool(results) and results[0]["source"] == expected_source
    top_3_match = expected_source in sources
    negative_match = is_negative_case and not results

    if top_1_match:
        top_1_hits += 1
    if top_3_match:
        top_3_hits += 1
    if negative_match:
        negative_passes += 1

    passed = negative_match if is_negative_case else top_3_match

    print(f"\n{'PASS' if passed else 'FAIL'} {case['name']}")
    print(f"Query: {case['query']}")
    if is_negative_case:
        print("Expected: no retrieved evidence")
    else:
        print(f"Expected: {expected_source}")
    print("Retrieved:")
    if not results:
        print("   No chunks passed the minimum similarity cutoff")
    else:
        for rank, result in enumerate(results, start=1):
            marker = "*" if result["source"] == expected_source else " "
            print(
                f" {marker} {rank}. {result['source']} / {result['section']} "
                f"(score={result['score']:.4f})"
            )

print()
print("Summary")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print(f"Positive cases: {len(positive_cases)}")
print(
    "Top-1 accuracy: "
    f"{top_1_hits}/{len(positive_cases)} "
    f"({(top_1_hits / len(positive_cases)) * 100:.1f}%)"
)
print(
    "Top-3 hit rate: "
    f"{top_3_hits}/{len(positive_cases)} "
    f"({(top_3_hits / len(positive_cases)) * 100:.1f}%)"
)
print(
    "Negative no-match: "
    f"{negative_passes}/{len(negative_cases)} "
    f"({(negative_passes / len(negative_cases)) * 100:.1f}%)"
)
