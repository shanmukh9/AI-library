def inspect_lambda_metrics() -> dict:
    return {
        "mode": "simulation",
        "function": "payment-processor",
        "duration_seconds": 14.8,
        "configured_timeout_seconds": 15,
        "downstream_latency": "normal",
        "recent_deployment": True,
    }


TOOL_HANDLERS = {
    "inspect_lambda_metrics": inspect_lambda_metrics,
}