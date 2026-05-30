import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Load alerts
with open("data/alerts.json") as f:
    alerts = json.load(f)

# Pick first alert to test
alert = alerts[0]

# LM Studio local setup
llm = ChatOpenAI(
    model="gemma-4",
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

# System prompt
system = """You are an expert CloudOps engineer.
Given an alert, respond ONLY with valid JSON in this exact format:
{
  "root_cause": "one sentence explanation",
  "severity": "P1, P2, or P3",
  "confidence": 0.0 to 1.0,
  "immediate_action": "one sentence recommendation"
}"""

# Call the model
response = llm.invoke([
    SystemMessage(content=system),
    HumanMessage(content=f"Alert: {alert['text']}")
])

clean = response.content.strip().strip("```json").strip("```").strip()
print(f"Alert: {alert['text']}")
print(f"\nResponse:\n{clean}")