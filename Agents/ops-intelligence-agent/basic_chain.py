import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


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


llm = ChatOpenAI(
    model="gemma-4",
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)

system = """You are an expert CloudOps engineer.
Respond ONLY with valid JSON:
{
  "root_cause": "one sentence explanation",
  "severity": "P1, P2, or P3",
  "model_confidence": 0.0 to 1.0,
  "immediate_action": "one sentence recommendation"
}
Note: model_confidence is your qualitative opinion only."""

for alert_index in test_alert_ids:
    alert = alerts[alert_index]
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=f"Alert: {alert['text']}"),
        ]
    )
    result = parse_model_json(response.content)
    print(f"\nAlert: {alert['text'][:60]}...")
    print(f"Predicted: {result['severity']} | Expected: {alert['severity_hint']}")
    print(f"Match: {'YES' if result['severity'] == alert['severity_hint'] else 'NO'}")
