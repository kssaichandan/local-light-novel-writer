# Local Light Novel Writer

Local Light Novel Writer is a web app for creating long light novels and web novels. It learns a reader's taste, builds a story bible, plans a full series in volumes and arcs, writes chapters one at a time, remembers continuity, lets the reader give feedback, and exports the finished novel.

The app is private and local-first by design. On a personal computer it writes with Ollama by default and stores stories in a local SQLite database. It also supports optional bring-your-own-key cloud AI providers for users who want stronger models and accept that story text will be sent to that provider.

## Repo Name Suggestion

Recommended repository name:

```text
local-light-novel-writer
```

Other good names:

```text
novel-forge-local
story-bible-writer
private-novel-generator
longform-ai-novel-writer
```

## Main Features

- Taste capture through a questionnaire, free-text preferences, saved taste profiles, or copy/paste "power mode" prompts.
- Full-plan import from a larger external LLM, so a user can paste a complete bible, volume map, arc map, and chapter outline.
- Layered planning: taste profile -> story bible -> volume map -> arc map -> per-arc chapter outline.
- Streaming chapter generation with progressive autosave, so interrupted chapters are not lost.
- Long-novel memory: recent chapter summaries, arc summaries, volume summaries, story-state ledger, and persistent character roster.
- Automatic chapter-plan sharpening so flat chapter beats become concrete scenes with tension.
- Per-novel voice card so chapters keep the same narrative sound.
- Genre-matched prose examples that help small local models write less generic prose.
- Optional cloud editor pass that drafts and then revises chapters when a cloud model is active.
- Chapter role guidance: setup, rising, breather, turn, and climax chapters get different pacing and ending instructions.
- Feedback learning: chapter ratings and notes update a learned taste profile used by later chapters.
- Reader UI with light/dark app theme, many reading themes, bundled local fonts, chapter navigation, read-aloud, manual editing, Markdown export, and EPUB export.
- Optional Chapter 0 primer for a spoiler-free world and character introduction.
- Repair endpoint to rebuild missing summaries and flag likely cut-off chapters.

## Privacy Model

Default local mode:

- The backend runs on your machine.
- Ollama runs on your machine.
- Stories are stored in `data/stories.sqlite3`.
- The normal launcher binds to `127.0.0.1`.
- Fonts are bundled locally.
- No telemetry, analytics, accounts, or runtime CDN calls.

Optional cloud mode:

- The user saves API keys only in browser local storage.
- Keys are not written to the SQLite database.
- When "Write with AI model" is enabled, the browser sends the key to the backend as a request header.
- The backend forwards generation to the selected provider for that request.
- Story text leaves the machine only in this opt-in mode.

Supported cloud routing includes OpenAI-compatible APIs, OpenRouter, Anthropic, Google Gemini, and Groq.

## Important Hosting Note

This project was originally built for private local use. If you deploy it live, anyone who can access the web UI can create, read, edit, export, or delete stories in the mounted database.

For a public deployment, put the app behind authentication or a private network. Render can host the web app, but Render does not provide local Ollama. For generation on Render, use the in-browser cloud key feature or point `OLLAMA_HOST` to your own reachable Ollama server.

## Tech Stack

- Python
- FastAPI
- Uvicorn
- HTTPX
- Pydantic
- SQLite
- Ollama for local generation
- Plain HTML, CSS, and JavaScript
- Local WOFF2 font bundle

## Project Structure

```text
backend/
  config.py          App settings, paths, generation defaults
  db.py              SQLite schema, migrations, and storage helpers
  epub.py            EPUB export builder
  learning.py        Feedback-to-taste learning logic
  ollama_client.py   Ollama client and optional cloud provider routing
  pipeline.py        Planning, writing, memory, repair, and finalization
  prompts.py         Prompt templates for all generation stages
  main.py            FastAPI app and routes

frontend/
  index.html         Single-page app markup
  app.js             UI state, API calls, streaming, reader, feedback, cloud keys
  style.css          App design system and reader styling
  fonts.css          Generated local font-face rules
  fonts/             Bundled WOFF2 fonts

scripts/
  fetch_fonts.py     Build-time helper to refresh bundled fonts

render.yaml          Render deployment blueprint
run.py               Local launcher
requirements.txt     Python dependencies
```

Private notes, old planning docs, logs, runtime data, exports, and backups are ignored by Git.

## Requirements for Local Use

- Python 3.10 or newer
- Ollama installed and running
- At least one local model pulled
- About 16 GB RAM recommended for the default model

Recommended model:

```bash
ollama pull gemma4:e4b-it-q4_K_M
```

Smaller fallback:

```bash
ollama pull gemma4:e2b
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start Ollama:

```bash
ollama serve
```

Run the app:

```bash
python run.py
```

Open:

```text
http://127.0.0.1:8000
```

## Deploy on Render

This repo includes `render.yaml`.

Basic steps:

1. Push this repository to GitHub.
2. In Render, choose "New" -> "Blueprint".
3. Connect the GitHub repository.
4. Render will read `render.yaml`.
5. Deploy the service.

The Render start command is:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

The blueprint uses Render's `free` plan. Free deployments can run the app, but they do not include a persistent disk. The app stores stories in SQLite under `data/`, so stories created on Render free can disappear after redeploys, restarts, or instance replacement.

For durable hosted story storage later, upgrade the Render service and add a persistent disk mounted at `/opt/render/project/src/data`.

## Render Generation Options

Render does not run Ollama inside this service. After deploying, generation has two practical paths:

1. Use the app's "AI model" key manager in the browser, save a provider key, and turn on "Write with AI model."
2. Host Ollama somewhere reachable from Render and set `OLLAMA_HOST` in Render to that URL.

If neither is configured, the UI can load, but local model generation will show Ollama as unavailable.

## Environment Variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `LN_MODEL` | `gemma4:e4b-it-q4_K_M` | Default local model name |
| `LN_HOST` | `127.0.0.1` locally, `0.0.0.0` on Render | Server bind host |
| `LN_PORT` | `8000` locally | Local server port |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API URL |
| `LN_STYLE_EXAMPLE` | `1` | Enables genre style examples |
| `LN_POLISH` | `auto` | Editor pass mode: `auto`, `1`, or `0` |
| `LN_CLOUD_CTX_MULT` | `3` | Memory budget multiplier for cloud models |

## API Summary

Core endpoints:

- `GET /api/health` checks local Ollama and lists models.
- `GET /api/projects` lists novels.
- `POST /api/projects` creates a novel.
- `GET /api/projects/{pid}` returns a full novel project.
- `DELETE /api/projects/{pid}` deletes a novel.
- `POST /api/projects/{pid}/taste` builds a taste profile.
- `POST /api/projects/{pid}/taste/import` imports a taste profile.
- `POST /api/projects/{pid}/bible` builds the story bible.
- `POST /api/projects/{pid}/volume-map` builds volume planning.
- `POST /api/projects/{pid}/arc-map` builds the arc map.
- `POST /api/projects/{pid}/outline/{arc_number}` expands one arc into chapter beats.
- `POST /api/projects/{pid}/write` streams a chapter.
- `POST /api/projects/{pid}/finalize` saves chapter memory.
- `POST /api/projects/{pid}/feedback` records feedback and updates learned taste.
- `GET /api/projects/{pid}/chapters` lists chapters.
- `GET /api/projects/{pid}/chapters/{number}` returns one chapter.
- `POST /api/projects/{pid}/chapters/{number}/edit` saves a manual chapter edit.
- `GET /api/projects/{pid}/export` exports Markdown.
- `GET /api/projects/{pid}/export-epub` exports EPUB.
- `POST /api/projects/{pid}/repair` rebuilds missing memory summaries.

## Writing Pipeline Summary

1. The app collects taste from the reader.
2. A taste profile is normalized into structured JSON.
3. A lean story bible defines the premise, world, characters, central conflict, power system, and endgame.
4. A volume map divides the long story into major movements.
5. An arc map gives each arc a title and goal.
6. One arc at a time is expanded into concrete chapter beats.
7. Before writing, short or flat chapter beats are sharpened into stronger scenes.
8. The chapter writer receives the bible, taste, state ledger, cast roster, story memory, previous chapter tail, next chapter hint, voice card, style example, and chapter role guidance.
9. Chapter prose streams to the browser.
10. The backend autosaves partial prose while streaming.
11. Finalization summarizes the chapter, updates the state ledger, and rolls up arc/volume memory when needed.

This lets the story scale to many chapters without putting the entire novel into every prompt.

## Data and Git Safety

The following should not be committed:

- `data/`
- `exports/`
- `docs/private/`
- `server.log`
- local backups
- SQLite database files
- API keys

The included `.gitignore` is set up for this.

## License

No license has been added yet. Add a license before publishing if you want other people to reuse, modify, or redistribute the project.
