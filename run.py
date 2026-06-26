"""Launcher. Run `python run.py` and open the printed URL in your browser.

Everything runs locally:
  - this web server (127.0.0.1)
  - your data (./data/stories.sqlite3)
  - the AI model (your local Ollama)
Nothing is sent anywhere.
"""
from __future__ import annotations

import webbrowser

import uvicorn

from backend import config


def main() -> None:
    url = f"http://{config.HOST}:{config.PORT}"
    print("=" * 60)
    print("  Local Light Novel Writer")
    print(f"  Open: {url}")
    print("  (Make sure Ollama is running: `ollama serve`)")
    print("=" * 60)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    uvicorn.run("backend.main:app", host=config.HOST, port=config.PORT, reload=False)


if __name__ == "__main__":
    main()
