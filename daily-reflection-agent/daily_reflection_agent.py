from __future__ import annotations

import argparse
import datetime as dt
import re
import textwrap
from pathlib import Path


DOMAINS = {
    "Fitness and Energy": {
        "keywords": {
            "walk",
            "gym",
            "workout",
            "exercise",
            "run",
            "steps",
            "sleep",
            "water",
            "food",
            "diet",
            "health",
            "fitness",
            "meditation",
            "yoga",
        },
        "next_rep": "Do one 10-minute body or mobility session before comfort can negotiate.",
    },
    "AI Career and Building": {
        "keywords": {
            "ai",
            "agent",
            "agents",
            "python",
            "project",
            "build",
            "code",
            "github",
            "career",
            "resume",
            "learn",
            "podcast",
            "course",
            "model",
        },
        "next_rep": "Ship one tiny artifact: script, prompt, note, README, or demo. Consumption only counts after conversion.",
    },
    "Discipline and Deep Work": {
        "keywords": {
            "focus",
            "deep",
            "work",
            "study",
            "procrastination",
            "scroll",
            "phone",
            "routine",
            "task",
            "tasks",
            "deadline",
            "planned",
        },
        "next_rep": "Set a 25-minute timer, put the phone away, and finish one defined task.",
    },
    "Mental Strength and Emotion": {
        "keywords": {
            "stress",
            "anxiety",
            "fear",
            "confidence",
            "comfort",
            "zone",
            "mood",
            "emotion",
            "grateful",
            "gratitude",
            "satisfied",
            "sad",
            "happy",
            "tired",
            "mental",
        },
        "next_rep": "Name the feeling, write the smallest courageous action, then do that action for five minutes.",
    },
    "Communication and Relationships": {
        "keywords": {
            "call",
            "message",
            "talk",
            "meeting",
            "communicate",
            "communication",
            "friend",
            "family",
            "colleague",
            "share",
            "write",
            "speaking",
        },
        "next_rep": "Send one clear message or speak one honest sentence you would normally avoid.",
    },
}

COMFORT_WORDS = {
    "watched",
    "scroll",
    "scrolled",
    "thinking",
    "thought",
    "planning",
    "plan",
    "maybe",
    "later",
    "course",
    "video",
    "podcast",
}

ACTION_WORDS = {
    "built",
    "created",
    "finished",
    "completed",
    "shipped",
    "wrote",
    "coded",
    "practiced",
    "exercised",
    "walked",
    "ran",
    "read",
    "called",
    "shared",
    "cleaned",
    "prepared",
}


def split_points(raw_text: str) -> list[str]:
    lines = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^[-*\d.)\s]+", "", line).strip()
        if line:
            lines.append(line)

    if len(lines) <= 1:
        chunks = re.split(r"(?<=[.!?])\s+|,\s+(?=(?:and\s+)?(?:i|I)\b)", raw_text)
        lines = [chunk.strip(" -") for chunk in chunks if chunk.strip(" -")]

    return lines


def words_for(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]+", text.lower()))


def classify(points: list[str]) -> dict[str, list[str]]:
    buckets = {domain: [] for domain in DOMAINS}
    for point in points:
        point_words = words_for(point)
        for domain, config in DOMAINS.items():
            if point_words & config["keywords"]:
                buckets[domain].append(point)
    return buckets


def score_day(points: list[str], buckets: dict[str, list[str]]) -> tuple[int, dict[str, int]]:
    all_words = words_for(" ".join(points))
    action_hits = len(all_words & ACTION_WORDS)
    comfort_hits = len(all_words & COMFORT_WORDS)
    covered_domains = sum(1 for items in buckets.values() if items)
    point_count = len(points)

    score = 35
    score += min(25, covered_domains * 5)
    score += min(20, action_hits * 4)
    score += min(10, point_count * 2)
    score -= min(15, max(0, comfort_hits - action_hits) * 3)
    score = max(20, min(95, score))

    details = {
        "domain_coverage": covered_domains,
        "action_hits": action_hits,
        "comfort_hits": comfort_hits,
        "logged_points": point_count,
    }
    return score, details


def score_label(score: int) -> str:
    if score >= 85:
        return "Strong day"
    if score >= 70:
        return "Solid day"
    if score >= 55:
        return "Mixed but useful day"
    return "Comfort-zone day"


def make_summary(points: list[str], buckets: dict[str, list[str]]) -> str:
    active_domains = [domain for domain, items in buckets.items() if items]
    if not active_domains:
        return "You showed up enough to log the day. That is the first rep, but tomorrow needs clearer action."

    domain_text = ", ".join(active_domains[:3])
    if len(active_domains) > 3:
        domain_text += f", and {len(active_domains) - 3} more areas"

    return (
        f"Today touched {domain_text}. The meaningful pattern is not whether the day was perfect; "
        "it is that your mind is asking for proof of growth. Use that signal well: convert one piece "
        "of awareness into one visible action."
    )


def key_pattern(points: list[str], buckets: dict[str, list[str]], details: dict[str, int]) -> str:
    if buckets["AI Career and Building"] and details["comfort_hits"] >= details["action_hits"]:
        return (
            "Your energy is pointed toward AI, but part of it is still living in consumption mode. "
            "The growth edge is to turn learning into a small artifact the same day."
        )
    if not buckets["Fitness and Energy"]:
        return (
            "The mind is asking for progress, but the body did not get a clear vote today. "
            "Fitness is not separate from ambition; it is the battery for ambition."
        )
    if not buckets["Discipline and Deep Work"]:
        return (
            "The day had activity, but the deep-work signal is weak. A focused 25-minute block "
            "would make tomorrow feel more owned."
        )
    return (
        "You are touching multiple growth areas. The next level is consistency: fewer intentions, "
        "more repeated small reps."
    )


def meaningful_improvement(buckets: dict[str, list[str]], details: dict[str, int]) -> str:
    if details["comfort_hits"] > details["action_hits"]:
        return (
            "Before watching or planning tomorrow, create something tiny first. A note, a script, a commit, "
            "or a five-line idea document is enough."
        )
    if not buckets["Fitness and Energy"]:
        return "Put a 10-minute walk or mobility session before screen-heavy work."
    if not buckets["Communication and Relationships"]:
        return "Practice one clear message or conversation. Confidence grows when expression becomes a rep."
    return "Choose one anchor habit and protect it. Do not make the system bigger until the small version repeats."


def hidden_progress(points: list[str]) -> list[str]:
    progress = []
    text = " ".join(points).lower()
    if any(word in text for word in ["podcast", "video", "course", "watched", "read"]):
        progress.append("You fed your mind with new inputs. Now train the identity: learner becomes builder.")
    if any(word in text for word in ["task", "completed", "finished", "done"]):
        progress.append("You completed ordinary tasks, which protects trust with yourself.")
    if any(word in text for word in ["comfort", "procrastination", "unsure", "confused", "feel"]):
        progress.append("You noticed an internal pattern instead of ignoring it. Awareness is a real mental rep.")
    if not progress:
        progress.append("You created a record of the day. That record is data for better decisions.")
    return progress


def growth_reframe(score: int) -> str:
    if score >= 75:
        return (
            "Do not label this as luck or mood. Label it as evidence: when you define the next rep, "
            "you can act with discipline."
        )
    if score >= 55:
        return (
            "This was not a failed day. It was a feedback day. The lesson is to reduce vague intention "
            "and increase small visible commitments."
        )
    return (
        "The comfort zone won some time today, but it did not win the full day because you are reviewing it. "
        "Tomorrow must start with action before consumption."
    )


def neuroplasticity_loop(buckets: dict[str, list[str]]) -> list[str]:
    weakest = [domain for domain, items in buckets.items() if not items]
    target = weakest[0] if weakest else "AI Career and Building"
    return [
        f"Cue: Choose one fixed trigger tomorrow, like morning tea, lunch, or laptop opening.",
        f"Rep: {DOMAINS[target]['next_rep']}",
        "Reward: Write one line immediately after: 'I kept the promise.'",
        "Repeat: Keep the rep small enough that excuses look unreasonable.",
    ]


def habit_signal(buckets: dict[str, list[str]], details: dict[str, int]) -> str:
    if details["action_hits"] >= 3:
        return (
            "Habit seed detected: you already have action energy. Attach it to a fixed time and keep the first "
            "version below 10 minutes, like Atomic Habits suggests: make it obvious, easy, and satisfying."
        )
    if buckets["AI Career and Building"]:
        return (
            "Habit to form: every piece of AI consumption must produce one artifact. One note, one prompt, "
            "one script, or one GitHub commit."
        )
    return (
        "Habit to form: a nightly two-minute reflection. The goal is not perfect journaling; it is closing "
        "the day with awareness and a next rep."
    )


def choose_tomorrow_action(buckets: dict[str, list[str]]) -> str:
    if buckets["AI Career and Building"]:
        return "Spend 25 minutes improving this reflection agent: add one feature, one sample, or one saved reflection."
    if not buckets["Fitness and Energy"]:
        return "Do a 10-minute walk or workout before any AI content."
    if not buckets["Discipline and Deep Work"]:
        return "Do one 25-minute deep-work block with a single written outcome."
    return "Pick one uncomfortable but useful task and finish the smallest version before noon."


def gratitude(points: list[str]) -> list[str]:
    items = []
    text = " ".join(points).lower()
    if "holiday" in text or "free" in text:
        items.append("You had free time today, which is a resource many people are wishing for.")
    if any(word in text for word in ["completed", "done", "finished", "task"]):
        items.append("You handled small responsibilities; that stability matters.")
    if any(word in text for word in ["learn", "podcast", "ai", "read", "watched"]):
        items.append("You have curiosity and access to ideas that can change your career path.")
    if not items:
        items.append("You have one more day of data about yourself. That is enough to improve tomorrow.")
    return items


def load_history(output_dir: Path, current_date: dt.date) -> list[str]:
    if not output_dir.exists():
        return []

    history = []
    for path in sorted(output_dir.glob("*-reflection.md"))[-7:]:
        if path.name.startswith(current_date.isoformat()):
            continue
        history.append(path.read_text(encoding="utf-8"))
    return history


def consistency_check(history: list[str], current_buckets: dict[str, list[str]]) -> str:
    if not history:
        return (
            "No previous reflections found yet. Today is day one, so the win is simple: create the record "
            "and come back tomorrow."
        )

    recent_text = "\n".join(history)
    repeated_domains = []
    for domain, items in current_buckets.items():
        if items and domain in recent_text:
            repeated_domains.append(domain)

    if len(repeated_domains) >= 2:
        return (
            "Consistency is starting to show in "
            + ", ".join(repeated_domains[:3])
            + ". Keep the reps boringly repeatable before trying to make them bigger."
        )
    if repeated_domains:
        return (
            f"Early habit signal: {repeated_domains[0]} appeared again. Protect that streak with a tiny daily minimum."
        )
    return (
        "Pattern warning: today's focus does not yet repeat from recent reflections. Choose one anchor habit "
        "to repeat tomorrow, even if the rest of the day changes."
    )


def render_reflection(
    raw_text: str,
    date: dt.date | None = None,
    history: list[str] | None = None,
) -> str:
    date = date or dt.date.today()
    history = history or []
    points = split_points(raw_text)
    buckets = classify(points)
    score, details = score_day(points, buckets)

    covered = [domain for domain, items in buckets.items() if items]
    missed = [domain for domain, items in buckets.items() if not items]

    sections = [
        f"# Daily Growth Reflection - {date.isoformat()}",
        "",
        f"## Score: {score}/100 - {score_label(score)}",
        "",
        make_summary(points, buckets),
        "",
        "## What You Logged",
        *(f"- {point}" for point in points),
        "",
        "## Areas Touched",
        *(f"- {domain}" for domain in covered),
    ]

    if missed:
        sections.extend(
            [
                "",
                "## Areas To Bring Back Tomorrow",
                *(f"- {domain}" for domain in missed[:3]),
            ]
        )

    sections.extend(
        [
            "",
            "## Hidden Progress",
            *(f"- {item}" for item in hidden_progress(points)),
            "",
            "## Growth Mindset Reframe",
            growth_reframe(score),
            "",
            "## Gratitude Reps",
            *(f"- {item}" for item in gratitude(points)),
            "",
            "## Neuroplasticity Loop",
            *(f"- {item}" for item in neuroplasticity_loop(buckets)),
            "",
            "## Challenge",
            "You said you feel stuck in your comfort zone, so here is the honest mirror: "
            "tomorrow, do not wait to feel inspired. Start with one visible output before consuming more content.",
            "",
            "## Habit Signal",
            habit_signal(buckets, details),
            "",
            "## Consistency Check",
            consistency_check(history, buckets),
            "",
            "## Tomorrow's Small Win",
            choose_tomorrow_action(buckets),
            "",
            "## Improve Tomorrow",
            "- Define the first action before sleeping or immediately after waking.",
            "- Keep the first rep tiny enough to finish even on a low-mood day.",
            "- Convert learning into building within the same day.",
            "- End the day by logging proof, not judging your identity.",
        ]
    )
    return "\n".join(sections) + "\n"


def render_concise_reflection(
    raw_text: str,
    date: dt.date | None = None,
    history: list[str] | None = None,
) -> str:
    date = date or dt.date.today()
    history = history or []
    points = split_points(raw_text)
    buckets = classify(points)
    score, details = score_day(points, buckets)

    sections = [
        f"# Daily Growth Reflection - {date.isoformat()}",
        "",
        f"## {score}/100 - {score_label(score)}",
        make_summary(points, buckets),
        "",
        "## Pattern",
        key_pattern(points, buckets, details),
        "",
        "## Growth Reframe",
        growth_reframe(score),
        "",
        "## Gratitude",
        gratitude(points)[0],
        "",
        "## Habit Cue",
        habit_signal(buckets, details),
        "",
        "## Challenge",
        "Start tomorrow with one visible output before consuming more content.",
        "",
        "## Tomorrow",
        choose_tomorrow_action(buckets),
        "",
        "## Improve",
        meaningful_improvement(buckets, details),
        "",
        "## Consistency",
        consistency_check(history, buckets),
    ]
    return "\n".join(sections) + "\n"


def read_input(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")

    print("Type your daily activity points. Press Enter twice when done.\n")
    lines = []
    while True:
        line = input()
        if not line.strip() and lines:
            break
        lines.append(line)
    return "\n".join(lines)


def save_reflection(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    match = re.search(r"# Daily Growth Reflection - ([0-9-]+)", content)
    date_part = match.group(1) if match else dt.date.today().isoformat()
    path = output_dir / f"{date_part}-reflection.md"
    path.write_text(content, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local Daily Growth Reflection Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python daily_reflection_agent.py --file today.txt
              python daily_reflection_agent.py --text "Watched AI podcast. Completed daily tasks. Felt stuck."
            """
        ),
    )
    parser.add_argument("--text", help="Daily notes as plain text.")
    parser.add_argument("--file", help="Path to a text file containing daily notes.")
    parser.add_argument(
        "--output-dir",
        default="data/reflections",
        help="Directory where markdown reflections are saved.",
    )
    args = parser.parse_args()

    raw_text = read_input(args)
    output_dir = Path(args.output_dir)
    history = load_history(output_dir, dt.date.today())
    reflection = render_concise_reflection(raw_text, history=history)
    output_path = save_reflection(reflection, output_dir)

    print(reflection)
    print(f"Saved reflection to: {output_path}")


if __name__ == "__main__":
    main()
