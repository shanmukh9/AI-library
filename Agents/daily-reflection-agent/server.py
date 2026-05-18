from __future__ import annotations

import json
import mimetypes
import ast
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rag import KNOWLEDGE_DIR, RAG_INDEX_PATH, build_index, format_context, retrieve, save_index


HOST = "127.0.0.1"
PORT = 8765
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
LM_STUDIO_CHAT_URL = f"{LM_STUDIO_BASE_URL}/chat/completions"
LM_STUDIO_MODELS_URL = f"{LM_STUDIO_BASE_URL}/models"
LM_STUDIO_TIMEOUT_SECONDS = 240
ROOT = Path(__file__).parent.resolve()
WEB_ROOT = ROOT / "web"

REFLECTION_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "daily_reflection",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "score": {"type": "integer", "minimum": 20, "maximum": 95},
                "label": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "pattern": {"type": "string"},
                "challenge": {"type": "string"},
                "tomorrow": {"type": "string"},
            },
            "required": ["score", "label", "title", "summary", "pattern", "challenge", "tomorrow"],
        },
    },
}

WEEKLY_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "weekly_review",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "repeatedPattern": {"type": "string"},
                "builderSignal": {"type": "string"},
                "comfortZone": {"type": "string"},
                "experiment": {"type": "string"},
                "scoreTrend": {"type": "string"},
            },
            "required": [
                "title",
                "summary",
                "repeatedPattern",
                "builderSignal",
                "comfortZone",
                "experiment",
                "scoreTrend",
            ],
        },
    },
}


SYSTEM_PROMPT = """You are a local daily reflection coach.

The user wants personal growth across overall wellbeing, fitness, AI career, AI agents, discipline, communication, consistency, confidence, mental strength, and deep work.

Tone:
- calm, soothing, emotionally intelligent
- mostly challenging, but not harsh
- concise and meaningful
- no long lists
- do not repeat all raw input points

Use growth mindset, neuroplasticity, gratitude, and Atomic Habits ideas in plain language.

Important output rule:
- Begin your response with { and end with }.
- Return one final JSON object only.
- Do not include analysis, reasoning, markdown, bullets, or commentary.
- If you are thinking internally, do not print that thinking.

Return JSON with these keys:
score: integer from 20 to 95
label: short phrase
title: one short sentence
summary: 2-3 sentences
pattern: 1-2 sentences
challenge: 1-2 sentences
tomorrow: one concrete action for tomorrow

Do not wrap JSON in markdown."""


WEEKLY_PROMPT = """You are a private weekly growth analyst for an aspiring AI builder.

Analyze the user's saved daily reflections from the last week.

Tone:
- calm, clear, and encouraging
- direct about comfort-zone patterns
- practical and builder-focused
- concise

Important output rule:
- Begin your response with { and end with }.
- Return one final JSON object only.
- Do not include analysis, reasoning, markdown, bullets, or commentary.
- If you are thinking internally, do not print that thinking.

Return JSON with these keys:
title: one short sentence
summary: 2-3 sentences about the week
repeatedPattern: 1-2 sentences
builderSignal: 1-2 sentences about AI-building or output creation
comfortZone: 1-2 sentences about avoidance or friction
experiment: one concrete 7-day experiment
scoreTrend: one short sentence about score/energy trend

Do not wrap JSON in markdown."""


def static_path(path: str) -> Path:
    cleaned = path.split("?", 1)[0].lstrip("/") or "index.html"
    target = (WEB_ROOT / cleaned).resolve()
    if WEB_ROOT not in target.parents and target != WEB_ROOT:
        return WEB_ROOT / "index.html"
    return target


def read_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")
    except Exception:
        return str(exc)


def get_lm_studio_model_id() -> str:
    with urllib.request.urlopen(LM_STUDIO_MODELS_URL, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))

    models = body.get("data", [])
    if not models:
        raise RuntimeError("LM Studio returned no loaded models from /v1/models.")

    return str(models[0]["id"])


def extract_json_object(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        content = content.removeprefix("json").strip()

    candidates = [content]
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(content[start : end + 1])

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc

        try:
            parsed = ast.literal_eval(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError) as exc:
            last_error = exc

        repaired = repair_json_like(candidate)
        if repaired != candidate:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as exc:
                last_error = exc

    preview = content[:500].replace("\n", "\\n")
    raise ValueError(f"Could not parse model JSON. Preview: {preview}") from last_error


def repair_json_like(content: str) -> str:
    repaired = content.strip()
    repaired = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', repaired)
    repaired = repaired.replace("'", '"')
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    return repaired


def parse_lm_message_content(body: dict) -> dict:
    message = body["choices"][0]["message"]
    content = str(message.get("content") or "").strip()
    if not content and message.get("reasoning_content"):
        raise ValueError(
            "The model produced reasoning text but no final JSON. Let it finish, reduce output size, "
            "disable reasoning/thinking in LM Studio if available, or use a non-reasoning/local-instruct model."
        )
    return extract_json_object(content)


def log_parse_error(exc: Exception) -> None:
    print(f"LM Studio response parse error: {exc}")


def parse_json_response(body: dict) -> dict:
    try:
        return parse_lm_message_content(body)
    except Exception as exc:
        log_parse_error(exc)
        raise


def call_lm_studio(
    notes: str,
    previous_promise: str = "",
    previous_promise_status: str = "",
    include_rag_debug: bool = False,
) -> dict:
    model_id = get_lm_studio_model_id()
    rag_context, rag_chunks = get_rag_context(notes)
    promise_context = ""
    if previous_promise:
        promise_context = (
            "\n\nPrevious promise context:\n"
            f"Promise: {previous_promise}\n"
            f"User marked it as: {previous_promise_status or 'not marked yet'}\n"
            "Use this gently for accountability if relevant."
        )
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Reflect on these messy daily notes. Compress them into a meaningful growth review.\n\n"
                    f"{rag_context}\n\n"
                    f"{notes}"
                    f"{promise_context}"
                ),
            },
        ],
        "temperature": 0.55,
        "max_tokens": 1200,
        "reasoning_effort": "none",
        "response_format": REFLECTION_JSON_SCHEMA,
        "stream": False,
    }

    request = urllib.request.Request(
        LM_STUDIO_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=LM_STUDIO_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))

    parsed = parse_json_response(body)
    reflection = normalize_reflection(parsed)
    reflection["model"] = model_id
    reflection["ragUsed"] = bool(rag_context)
    if include_rag_debug:
        reflection["ragDebug"] = rag_chunks
    return reflection


def ensure_rag_index() -> None:
    if RAG_INDEX_PATH.exists() or not KNOWLEDGE_DIR.exists():
        return

    markdown_files = list(KNOWLEDGE_DIR.glob("*.md"))
    if not markdown_files:
        return

    index = build_index(KNOWLEDGE_DIR)
    save_index(index)


def get_rag_context(query: str) -> tuple[str, list[dict]]:
    ensure_rag_index()
    chunks = retrieve(query, top_k=3)
    debug_chunks = [
        {
            "source": chunk.source,
            "heading": chunk.heading,
            "score": round(chunk.score, 2),
            "excerpt": chunk.text[:360],
        }
        for chunk in chunks
    ]
    return format_context(chunks), debug_chunks


def call_lm_studio_weekly(reflections: list[dict], promise_status: dict) -> dict:
    model_id = get_lm_studio_model_id()
    compact_reflections = []
    for item in reflections[-10:]:
        compact_reflections.append(
            {
                "date": item.get("day") or item.get("date", ""),
                "score": item.get("score", ""),
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "pattern": item.get("pattern", ""),
                "challenge": item.get("challenge", ""),
                "tomorrow": item.get("tomorrow", ""),
                "promiseStatus": promise_status.get(item.get("id", ""), ""),
            }
        )

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": WEEKLY_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze these saved reflections and produce the weekly growth review JSON.\n\n"
                    f"{json.dumps(compact_reflections, ensure_ascii=True)}"
                ),
            },
        ],
        "temperature": 0.5,
        "max_tokens": 1200,
        "reasoning_effort": "none",
        "response_format": WEEKLY_JSON_SCHEMA,
        "stream": False,
    }

    request = urllib.request.Request(
        LM_STUDIO_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=LM_STUDIO_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read().decode("utf-8"))

    parsed = parse_json_response(body)
    weekly = normalize_weekly_review(parsed)
    weekly["model"] = model_id
    return weekly


def normalize_reflection(data: dict) -> dict:
    score = int(data.get("score", 60))
    score = max(20, min(95, score))
    return {
        "score": score,
        "label": str(data.get("label", "Reflection ready"))[:80],
        "title": str(data.get("title", "Today has a signal worth noticing."))[:140],
        "summary": str(data.get("summary", ""))[:900],
        "pattern": str(data.get("pattern", ""))[:700],
        "challenge": str(data.get("challenge", ""))[:700],
        "tomorrow": str(data.get("tomorrow", ""))[:300],
        "source": "lm-studio",
    }


def normalize_weekly_review(data: dict) -> dict:
    return {
        "title": str(data.get("title", "This week has a pattern worth noticing."))[:160],
        "summary": str(data.get("summary", ""))[:1000],
        "repeatedPattern": str(data.get("repeatedPattern", ""))[:700],
        "builderSignal": str(data.get("builderSignal", ""))[:700],
        "comfortZone": str(data.get("comfortZone", ""))[:700],
        "experiment": str(data.get("experiment", ""))[:400],
        "scoreTrend": str(data.get("scoreTrend", ""))[:300],
        "source": "lm-studio",
    }


class ReflectionHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path not in {"/api/reflect", "/api/weekly"}:
            self.send_json(404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})
            return

        if self.path == "/api/weekly":
            reflections = body.get("reflections", [])
            promise_status = body.get("promiseStatus", {})
            if not isinstance(reflections, list) or len(reflections) < 2:
                self.send_json(400, {"error": "At least two saved reflections are required for a weekly review."})
                return
            if not isinstance(promise_status, dict):
                promise_status = {}
            self.handle_lm_call(lambda: call_lm_studio_weekly(reflections, promise_status))
            return

        notes = str(body.get("notes", "")).strip()
        previous_promise = str(body.get("previousPromise", "")).strip()
        previous_promise_status = str(body.get("previousPromiseStatus", "")).strip()
        include_rag_debug = bool(body.get("includeRagDebug", False))

        if not notes:
            self.send_json(400, {"error": "Notes are required"})
            return

        self.handle_lm_call(lambda: call_lm_studio(notes, previous_promise, previous_promise_status, include_rag_debug))

    def handle_lm_call(self, callback) -> None:
        try:
            self.send_json(200, callback())
        except urllib.error.HTTPError as exc:
            detail = read_http_error(exc)
            print(f"LM Studio HTTP error {exc.code}: {detail}")
            self.send_json(
                502,
                {
                    "error": "LM Studio returned an error while generating the reflection.",
                    "detail": detail,
                },
            )
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            print(f"LM Studio connection error: {exc}")
            self.send_json(
                503,
                {
                    "error": "LM Studio is not reachable or has no loaded model. Start the LM Studio local server and try again.",
                    "detail": str(exc),
                    "timeout_seconds": LM_STUDIO_TIMEOUT_SECONDS,
                },
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(
                502,
                {
                    "error": "The local model responded, but not in the expected reflection JSON format.",
                    "detail": str(exc),
                },
            )

    def do_GET(self) -> None:
        target = static_path(self.path)
        if not target.exists() or target.is_dir():
            self.send_error(404)
            return

        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    ensure_rag_index()
    server = ThreadingHTTPServer((HOST, PORT), ReflectionHandler)
    print(f"Daily Reflection Agent running at http://{HOST}:{PORT}")
    print("LM Studio should be running its local server at http://127.0.0.1:1234")
    print(f"LM Studio request timeout: {LM_STUDIO_TIMEOUT_SECONDS} seconds")
    if RAG_INDEX_PATH.exists():
        print(f"RAG index loaded: {RAG_INDEX_PATH}")
    server.serve_forever()


if __name__ == "__main__":
    main()
