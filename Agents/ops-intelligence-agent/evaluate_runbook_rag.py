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
    }
]


passes = 0

for case in TEST_CASES:
    results = search_runbooks(case["query"], top_k=3, min_score=DEFAULT_MIN_SCORE)
    sources = [result["source"] for result in results]
    matched = case["expected_source"] in sources
    if matched:
        passes += 1

    print(f"\n{'PASS' if matched else 'FAIL'} {case['name']}")
    print(f"Query: {case['query']}")
    print(f"Expected: {case['expected_source']}")
    print("Retrieved:")
    for rank, result in enumerate(results, start=1):
        marker = "*" if result["source"] == case["expected_source"] else " "
        print(
            f" {marker} {rank}. {result['source']} / {result['section']} "
            f"(score={result['score']:.4f})"
        )

print()
print("Summary")
print(f"Minimum similarity: {DEFAULT_MIN_SCORE:.2f}")
print(f"Passed: {passes}/{len(TEST_CASES)}")
print(f"Hit rate: {(passes / len(TEST_CASES)) * 100:.1f}%")
