# Daily Reflection Agent

A local reflection agent that turns messy daily activity notes into a calm, meaningful growth review.

It is tuned for:

- overall well-being
- fitness and energy
- AI career growth
- discipline and deep work
- mental strength
- communication
- confidence and consistency
- gratitude and Atomic Habits-style habit formation

## Project Structure

```text
daily-reflection-agent/
├── web/                 # Browser UI
├── data/reflections/    # Saved Markdown reflections from the CLI
├── examples/            # Sample daily notes
├── ai-edge-skills/      # Android AI Edge Gallery skill export
├── server.py            # Local LM Studio bridge and web server
├── daily_reflection_agent.py
└── README.md
```

## Open The UI With Local AI

1. Open LM Studio.
2. Load your Gemma model.
3. Start LM Studio's local server. The default endpoint should be:

```text
http://127.0.0.1:1234
```

4. In this project folder, run:

```powershell
python server.py
```

5. Open:

```text
http://127.0.0.1:8765
```

Your notes stay on your laptop. The UI sends them only to your local LM Studio server.

## Offline UI

Open [index.html](C:/Users/saina/Documents/Codex/daily-reflection-agent/web/index.html) in your browser.

Opening the file directly runs the simpler rule-based fallback without LM Studio. It keeps your draft and saved reflections in the browser's local storage.

## Optional CLI

Interactive mode:

```powershell
python daily_reflection_agent.py
```

From quick text:

```powershell
python daily_reflection_agent.py --text "Watched 1 hour AI podcast. Completed daily tasks. Felt stuck in comfort zone. Want to build AI agents."
```

From a notes file:

```powershell
python daily_reflection_agent.py --file examples/today_sample.txt
```

Each CLI run prints a concise reflection and saves a Markdown file under `data/reflections/`.

## Suggested Daily Input

Write rough points from your mobile. Messy is fine.

```text
- Watched 1 hour AI podcast from Raw Talks
- Completed some daily tasks
- Felt like I did not accomplish enough
- Want to build AI agents instead of watching more videos
- Did not exercise
- Felt grateful for having a holiday
```

## What It Produces

- score for the day
- meaningful summary
- key pattern
- direct challenge
- habit cue
- tomorrow's small win
- history view for saved reflections
- yesterday's promise check
- weekly pattern review from saved reflections
- export/import for your local data

## What Is Stored

The browser stores:

- `draftNotes`
- `reflectionHistory`
- `promiseStatus`
- `reflectionCache`

This is local to the browser profile for `http://127.0.0.1:8765`.

## Good First Upgrade Ideas

- Add a `--tone` option for balanced or highly challenging feedback.
- Add local passcode/encrypted storage.
- Package as Android APK later with no internet permission.
