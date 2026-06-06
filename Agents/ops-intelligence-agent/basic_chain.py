import json
import urllib.error
import urllib.request

from runbook_rag import DEFAULT_MIN_SCORE, format_evidence, search_runbooks


CHAT_COMPLETIONS_URL = "http://127.0.0.1:1234/v1/chat/completions"
CHAT_MODEL = "google/gemma-4-e4b"
ALERT_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause": {"type": "string"},
        "severity": {"type": "string", "enum": ["P1", "P2", "P3"]},
        "model_confidence": {"type": "number"},
        "immediate_action": {"type": "string"},
    },
    "required": [
        "root_cause",
        "severity",
        "model_confidence",
        "immediate_action",
    ],
    "additionalProperties": False,
}

with open("data/alerts.json", encoding="utf-8") as alerts_file:
    alerts = json.load(alerts_file)

test_alert_ids = [0, 1, 7]


def parse_model_json(content):
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        preview = cleaned[:300].replace("\n", "\\n")
        raise ValueError(f"Model did not return valid JSON. Preview: {preview}") from exc


def call_chat_model(messages):
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 500,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "alert_analysis",
                "schema": ALERT_ANALYSIS_SCHEMA,
            },
        },
    }
    request = urllib.request.Request(
        CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Could not reach LM Studio chat endpoint. "
            "Start LM Studio and load the chat model."
        ) from exc
    message = body["choices"][0]["message"]
    return message.get("content") or message.get("reasoning_content") or ""


system = """You are an expert CloudOps engineer.
Use retrieved runbook evidence when it is provided. If no evidence is available,
use your general CloudOps judgment and say the recommendation is not grounded in a runbook.
Severity policy:
- P1: customer-facing outage risk, repeated hard failures, crash loops on critical services, sustained CPU above 95 percent, database exhaustion, or active 5xx impact.
- P2: degraded service, expiring certificates, capacity pressure, missed acknowledgement, or delayed observability without confirmed outage.
- P3: low-risk maintenance, cost awareness, CI/CD failure, or non-urgent infrastructure hygiene.
Do not include reasoning, markdown, or prose outside the JSON object.
Respond ONLY with valid JSON:
{
  "root_cause": "one sentence explanation",
  "severity": "P1, P2, or P3",
  "model_confidence": 0.0 to 1.0,
  "immediate_action": "one sentence recommendation"
}
Note: model_confidence is your qualitative opinion only. It is not calibrated probability."""

for alert_index in test_alert_ids:
    alert = alerts[alert_index]
    try:
        retrieved_evidence = search_runbooks(
            alert["text"],
            top_k=2,
            min_score=DEFAULT_MIN_SCORE,
        )
        evidence_text = format_evidence(retrieved_evidence)
    except (FileNotFoundError, RuntimeError) as exc:
        retrieved_evidence = []
        evidence_text = f"No retrieved runbook evidence. Retrieval error: {exc}"

    response_content = call_chat_model(
        [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": "\n\n".join(
                    [
                        f"Alert: {alert['text']}",
                        f"Service: {alert['service']}",
                        "Retrieved runbook evidence:",
                        evidence_text,
                    ]
                ),
            },
        ]
    )
    result = parse_model_json(response_content)
    print(f"\nAlert: {alert['text'][:60]}...")
    if retrieved_evidence:
        top = retrieved_evidence[0]
        print(
            "Top evidence: "
            f"{top['source']} / {top['section']} "
            f"(score={top['score']:.4f})"
        )
    else:
        print("Top evidence: none")
    print(f"Predicted: {result['severity']} | Expected: {alert['severity_hint']}")
    print(f"Match: {'YES' if result['severity'] == alert['severity_hint'] else 'NO'}")
