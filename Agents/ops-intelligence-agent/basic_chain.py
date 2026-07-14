import json
import urllib.error
import urllib.request

from evidence_acceptance import assess_evidence
from hybrid_retriever import format_hybrid_evidence, hybrid_search_rrf


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
The provided runbook evidence has passed an evidence-acceptance gate. Ground the
root cause and immediate action in the alert and that evidence. Do not introduce
systems, causes, or actions that are absent from both.
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


def build_non_analysis_response(assessment):
    status_by_decision = {
        "clarify": "clarification_required",
        "no_coverage": "no_coverage",
    }
    return {
        "status": status_by_decision[assessment["decision"]],
        "grounding": "none",
        "source": None,
        "reason": assessment["reason"],
        "clarifying_question": assessment["clarifying_question"],
        "analysis": None,
        "escalation_required": assessment["decision"] == "no_coverage",
    }


def analyze_alert(alert):
    try:
        raw_candidates = hybrid_search_rrf(
            alert["text"],
            top_k=3,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        return {
            "status": "retrieval_error",
            "grounding": "none",
            "source": None,
            "reason": str(exc),
            "clarifying_question": None,
            "analysis": None,
            "escalation_required": True,
        }

    assessment = assess_evidence(alert["text"], raw_candidates)
    if assessment["decision"] != "accept":
        return build_non_analysis_response(assessment)

    retrieved_evidence = assessment["evidence"]
    evidence_text = format_hybrid_evidence(retrieved_evidence)

    try:
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
        analysis = parse_model_json(response_content)
    except (RuntimeError, ValueError) as exc:
        return {
            "status": "model_error",
            "grounding": "runbook",
            "source": retrieved_evidence[0]["source"],
            "reason": str(exc),
            "clarifying_question": None,
            "analysis": None,
            "escalation_required": True,
            "evidence": retrieved_evidence,
        }
    return {
        "status": "analysis_ready",
        "grounding": "runbook",
        "source": retrieved_evidence[0]["source"],
        "reason": assessment["reason"],
        "clarifying_question": None,
        "analysis": analysis,
        "escalation_required": False,
        "evidence": retrieved_evidence,
    }


def main():
    for alert_index in test_alert_ids:
        alert = alerts[alert_index]
        result = analyze_alert(alert)
        print(f"\nAlert: {alert['text'][:60]}...")
        print(f"Status: {result['status']} | Grounding: {result['grounding']}")
        print(f"Gate reason: {result['reason']}")

        if result["status"] == "analysis_ready":
            top = result["evidence"][0]
            print(
                "Top evidence: "
                f"{top['source']} / {top['section']} "
                f"(rrf={top['rrf_score']:.5f}, "
                f"retrieved_by={'+'.join(top['retrieved_by'])})"
            )
            analysis = result["analysis"]
            print(
                f"Predicted: {analysis['severity']} | "
                f"Expected: {alert['severity_hint']}"
            )
            print(
                f"Match: "
                f"{'YES' if analysis['severity'] == alert['severity_hint'] else 'NO'}"
            )
        else:
            print("Top evidence: none")
            if result["clarifying_question"]:
                print(f"Clarifying question: {result['clarifying_question']}")
            print(f"Escalation required: {result['escalation_required']}")


if __name__ == "__main__":
    main()
