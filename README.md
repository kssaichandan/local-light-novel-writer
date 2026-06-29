# Local Light Novel Writer

Local Light Novel Writer is a browser-based writing app for planning and drafting long light novels, web novels, and serialized fiction. It helps turn a reader's preferences into a structured story plan, writes chapters one at a time, keeps continuity notes, learns from feedback, and exports the finished work.

The app supports two modes:

- Online demo: a hosted demo where users try the interface with their own cloud AI provider key.
- Local use: a private setup on the user's computer with Ollama and local SQLite storage.

## Features

- Taste profile builder from questionnaires, free-text preferences, saved profiles, or pasted prompts.
- Story bible generation for premise, setting, characters, conflict, power system, tone, and endgame.
- Long-form planning across volumes, arcs, and chapter beats.
- Streaming chapter writing with autosave while generation is running.
- Continuity memory with chapter summaries, arc summaries, volume summaries, story state, and cast notes.
- Chapter feedback that updates the learned taste profile for later writing.
- Optional cloud AI routing for OpenAI-compatible APIs, OpenRouter, Anthropic, Google Gemini, and Groq.
- Optional cloud editor pass for draft revision when a cloud model is active.
- Reader interface with themes, local fonts, chapter navigation, text-to-speech, manual editing, Markdown export, and EPUB export.
- Repair workflow for rebuilding missing summaries and checking likely cut-off chapters.

## Online Demo

The hosted version is intended as a demo, not permanent hosted storage.

In the demo:

- Users provide their own cloud AI key in the browser.
- API keys are stored in browser local storage, not in the SQLite database.
- The backend forwards generation requests to the selected provider only when cloud writing is enabled.
- Render does not run Ollama for this service.
- Render free-tier filesystem storage is temporary, so demo stories can disappear after redeploys, restarts, idle spin-downs, or instance replacement.

For private writing, durable local storage, and Ollama generation, run the app locally.

## Local Setup

### Requirements

- Python 3.10 or newer
- Ollama installed and running
- At least one Ollama model pulled
- About 16 GB RAM recommended for the default local model

### Install

Clone the repository:

```bash
git clone https://github.com/kssaichandan/local-light-novel-writer.git
cd local-light-novel-writer
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Pull the recommended local model:

```bash
ollama pull gemma4:e4b-it-q4_K_M
```

For lower-memory machines, use a smaller model:

```bash
ollama pull gemma4:e2b
```

Start Ollama:

```bash
ollama serve
```

Run the app:

```bash
python run.py
```

Open the local site:

```text
http://127.0.0.1:8000
```

## Deploy the Demo on Render

This repository includes a `render.yaml` blueprint for a free Render web service.

1. Push the repository to GitHub.
2. Open the Render dashboard.
3. Choose `New` > `Blueprint`.
4. Connect the GitHub repository.
5. Keep the blueprint path as `render.yaml`.
6. Deploy the service.

Render uses:

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

The free Render deployment is a demo environment. It can run the app, but SQLite files are not durable on the free filesystem. Upgrade the Render service and mount a persistent disk at `/opt/render/project/src/data` if you later want hosted story storage to survive redeploys and restarts.

## Using Cloud AI in the Demo

The demo is designed for bring-your-own-key cloud generation.

1. Open the deployed app.
2. Open the app's AI model/key settings.
3. Choose a supported provider.
4. Save your API key in the browser.
5. Enable cloud writing.
6. Generate or continue a chapter.

Story text is sent to the selected cloud provider only for requests made with cloud writing enabled.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `LN_HOST` | `127.0.0.1` locally, `0.0.0.0` on Render | Server bind host |
| `LN_PORT` | `8000` | Local server port |
| `LN_MODEL` | `gemma4:e4b-it-q4_K_M` | Default Ollama model |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API URL for local use |
| `LN_STYLE_EXAMPLE` | `1` | Enables genre-matched style examples |
| `LN_POLISH` | `auto` | Editor pass mode: `auto`, `1`, or `0` |
| `LN_CLOUD_CTX_MULT` | `3` | Memory budget multiplier for cloud models |

## Project Structure

```text
backend/
  config.py          Runtime settings and filesystem paths
  db.py              SQLite schema, migrations, and storage helpers
  epub.py            EPUB export builder
  learning.py        Feedback-to-taste learning logic
  ollama_client.py   Ollama and cloud provider client routing
  pipeline.py        Planning, writing, memory, repair, and finalization
  prompts.py         Prompt templates
  main.py            FastAPI app and routes

frontend/
  index.html         Single-page app markup
  app.js             UI state, API calls, streaming, reader, and key manager
  style.css          App and reader styling
  fonts.css          Local font-face rules
  fonts/             Bundled WOFF2 fonts

scripts/
  fetch_fonts.py     Helper for refreshing bundled fonts

render.yaml          Render demo deployment blueprint
run.py               Local launcher
requirements.txt     Python dependencies
```

## API Overview

The FastAPI backend exposes endpoints for:

- Health and model checks
- Project creation, loading, listing, and deletion
- Taste profile generation and import
- Story bible, volume map, arc map, and chapter outline generation
- Streaming chapter writing
- Chapter finalization and continuity memory updates
- Feedback capture and taste learning
- Manual chapter editing
- Markdown and EPUB export
- Summary repair and cut-off checks

## Privacy and Data

Local mode is private by default:

- The backend runs on the user's computer.
- Ollama runs on the user's computer.
- Stories are stored in `data/stories.sqlite3`.
- The local launcher binds to `127.0.0.1`.
- Fonts are bundled locally.
- The app has no telemetry, analytics, accounts, or runtime CDN calls.

Cloud mode is opt-in:

- API keys are saved in browser local storage.
- API keys are not written to SQLite.
- Story text is sent to a cloud provider only when cloud writing is enabled.

The `.gitignore` excludes runtime data, exports, logs, private notes, local backups, database files, and common environment folders.

## Limitations

- Render free deployments are suitable for demos, not durable hosted writing.
- Local Ollama generation quality and speed depend on the chosen model and hardware.
- Cloud generation requires the user's own provider account and API key.
- No authentication layer is included by default. Add access control before using this as a shared production service.

## Development

Run Python syntax checks:

```bash
python -m compileall backend run.py
```

Check frontend JavaScript syntax:

```bash
node --check frontend/app.js
```

## License

No license has been added yet. Add a license before publishing terms for reuse, modification, or redistribution.
