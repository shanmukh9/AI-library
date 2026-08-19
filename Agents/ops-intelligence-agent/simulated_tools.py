def inspect_lambda_metrics(*, function_name: str) -> dict:
    return {
        "mode": "simulation",
        "function": function_name,
        "duration_seconds": 14.8,
        "configured_timeout_seconds": 15,
        "downstream_latency": "normal",
        "recent_deployment": True,
    }



TOOL_HANDLERS = {
    "inspect_lambda_metrics": inspect_lambda_metrics,
}