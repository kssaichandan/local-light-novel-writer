"""App configuration. Everything is local by default — nothing leaves the machine."""
from __future__ import annotations

import os
from pathlib import Path

# Project root = parent of the backend/ package.
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPORT_DIR = ROOT_DIR / "exports"
DB_PATH = DATA_DIR / "stories.sqlite3"

# Ollama runs locally. This URL is the user's own machine.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# Default model — small enough for a 16GB-RAM laptop with no GPU.
DEFAULT_MODEL = os.environ.get("LN_MODEL", "gemma4:e4b-it-q4_K_M")

# Server bind. Localhost only = the webpage is not exposed to the network.
HOST = os.environ.get("LN_HOST", "127.0.0.1")
PORT = int(os.environ.get("LN_PORT", "8000"))

# Generation defaults
DEFAULT_TEMPERATURE = 0.85
# Prose-only anti-repetition knobs. Small local models love to loop on the same word/phrase
# ("the Lattice… efficiency… optimization…") and the same sentence shape. A MILD penalty pushes
# the sampler off recently-used tokens. Kept gentle on purpose: too strong (and especially
# presence_penalty) also penalizes periods, newlines, and common words like "the", which makes the
# model STOP ending sentences and starting paragraphs → one giant run-on. So repeat_penalty stays
# near default and presence_penalty is OFF. Applied ONLY to prose — never to JSON stages.
PROSE_REPEAT_PENALTY = float(os.environ.get("LN_REPEAT_PENALTY", "1.15"))
PROSE_REPEAT_LAST_N = int(os.environ.get("LN_REPEAT_LAST_N", "256"))
PROSE_PRESENCE_PENALTY = float(os.environ.get("LN_PRESENCE_PENALTY", "0.0"))
PROSE_FREQUENCY_PENALTY = float(os.environ.get("LN_FREQUENCY_PENALTY", "0.3"))
# Context window + max output tokens. Ollama defaults num_ctx low (~4k), which
# truncates long JSON (the story bible) mid-string. A chapter prompt now stacks up a lot
# (bible + taste + story-so-far + state sheet + cast + previous-chapter tail), so 8k left too
# little room and chapters got cut off or the front of the prompt (the bible) was silently
# dropped. 16k comfortably fits the full input AND the output. Gemma supports far larger still.
NUM_CTX = int(os.environ.get("LN_NUM_CTX", "16384"))
NUM_PREDICT = int(os.environ.get("LN_NUM_PREDICT", "4096"))
# Inject ONE short, genre-matched STYLE EXAMPLE into the prose writer. A small local model imitates
# a concrete example far better than it follows abstract craft rules, so a single high-quality
# snippet (style-only — never its content) raises prose quality across genres. Off via
# LN_STYLE_EXAMPLE=0 if it ever causes trouble. JSON planning stages never see it.
STYLE_EXAMPLE_ON = os.environ.get("LN_STYLE_EXAMPLE", "1") != "0"

# Retry count for stages that must return valid JSON (small models fail intermittently).
JSON_RETRIES = 3
# How much of the rolling story context (in characters) we keep for the writer.
ROLLING_SUMMARY_BUDGET = 6000

# --- cloud-aware quality knobs -------------------------------------------------
# A big cloud model (Groq/OpenAI/Claude/…) has a far larger context window than the budgets we
# tuned for a 4B laptop model, so when a cloud key is active the memory budgets scale up by this
# factor (more recent-chapter summaries, a fuller cast slice, longer state sheet to the writer).
CLOUD_CTX_MULT = int(os.environ.get("LN_CLOUD_CTX_MULT", "3"))
# Editor pass (draft → critique → revise). "auto" = ON when a cloud key is active (fast + cheap
# there), OFF on local CPU (it would double the wait). LN_POLISH=1 forces on, LN_POLISH=0 forces off.
POLISH_MODE = os.environ.get("LN_POLISH", "auto").strip().lower()
# Gentle anti-repetition for cloud prose (OpenAI-compatible providers accept frequency_penalty;
# the Ollama-specific repeat_penalty doesn't exist there).
CLOUD_PROSE_FREQUENCY_PENALTY = float(os.environ.get("LN_CLOUD_FREQUENCY_PENALTY", "0.2"))
# Retries for cloud calls that fail before any text arrives (rate limits / transient errors).
CLOUD_RETRIES = int(os.environ.get("LN_CLOUD_RETRIES", "4"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
