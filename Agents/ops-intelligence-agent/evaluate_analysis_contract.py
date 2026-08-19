from basic_chain import parse_model_json, validate_alert_analysis


valid = validate_alert_analysis(
    parse_model_json(
        """{
          "root_cause": "Lambda duration is approaching its timeout.",
          "severity": "P1",
          "model_confidence": 0.9,
          "immediate_action": "Inspect Lambda duration metrics.",
          "tool_proposal": {
            "tool_name": "inspect_lambda_metrics",
            "tool_arguments": {
              "function_name": "payment-processor"
            },
            "rationale": "Confirm timeout pressure.",
            "evidence_refs": ["lambda-timeout.md"]
          }
        }"""
    )
)

assert valid["severity"] == "P1"
assert valid["tool_proposal"]["tool_name"] == "inspect_lambda_metrics"
print("PASS valid structured analysis satisfies the contract")


try:
    validate_alert_analysis(
        {
            "root_cause": "Unsupported action.",
            "severity": "P1",
            "model_confidence": 0.9,
            "immediate_action": "Delete the function.",
            "tool_proposal": {
                "tool_name": "delete_lambda",
                "tool_arguments": {
                    "function_name": "payment-processor",
                },
                "rationale": "Remove the failure.",
                "evidence_refs": ["lambda-timeout.md"],
            },
        }
    )
except ValueError as exc:
    assert str(exc) == "tool_proposal contains an unsupported tool."
else:
    raise AssertionError("Unsupported tool proposal should fail validation.")

print("PASS unsupported tool proposal fails the contract")
