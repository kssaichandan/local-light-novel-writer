"""FastAPI app: serves the local webpage and the generation API.

Bound to 127.0.0.1 only — the site is not reachable from the network.
Talks to a local Ollama. No external calls anywhere.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException

# Some Windows installs don't register the woff2 type, so bundled fonts get served
# as text/plain. Register it so the local fonts come back as font/woff2.
mimetypes.add_type("font/woff2", ".woff2")
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db, epub, learning, ollama_client as oc, pipeline, prompts


async def _llm_ctx(
    x_llm_key: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
    x_llm_provider: str | None = Header(default=None),
):
    """If the browser sent a pasted API key, route this request's generation to that cloud
    model; otherwise stay on local Ollama. The key is used in-memory only, never stored."""
    token = oc.set_cloud(x_llm_key, x_llm_model, x_llm_provider)
    try:
        yield
    finally:
        oc.reset_cloud(token)


app = FastAPI(title="Local Light Novel Writer", dependencies=[Depends(_llm_ctx)])
FRONTEND_DIR = config.ROOT_DIR / "frontend"


@app.on_event("startup")
def _startup() -> None:
    db.init()


# ============================================================ request models
class CreateProject(BaseModel):
    title: str = "Untitled"
    model: str = config.DEFAULT_MODEL
    target_chapters: int = 100
    chapters_per_arc: int = 10
    taste_profile_id: int | None = None  # start from a saved learned taste (Idea 2)
    use_scenes: bool = False  # scene-by-scene writing (layer 3)


class SettingsInput(BaseModel):
    use_scenes: bool | None = None
    model: str | None = None  # switch the local model used for the next chapters


class FeedbackInput(BaseModel):
    number: int
    feedback: dict = {}


class SaveTasteInput(BaseModel):
    name: str


class TasteInput(BaseModel):
    # Any subset — questionnaire fields, free text, sample ratings.
    raw: dict = {}


class TasteImport(BaseModel):
    # A finished taste profile produced by an external LLM (Idea 1b power mode).
    profile: dict = {}


class PlanImport(BaseModel):
    # A full plan (bible + volume_map + arc_map + outline) from an external LLM.
    plan: dict = {}


class BibleInput(BaseModel):
    premise_hint: str = ""


class WriteInput(BaseModel):
    number: int
    target_words: int = 1200
    apply_steering: bool = True  # False = faithful redo (don't push taste/feedback changes)


class FinalizeInput(BaseModel):
    number: int
    content: str


class EditChapterInput(BaseModel):
    content: str
    title: str | None = None


# ============================================================ status / models
@app.get("/api/health")
async def health() -> dict:
    up = await oc.is_up()
    models = await oc.list_models() if up else []
    return {"ollama_up": up, "models": models, "default_model": config.DEFAULT_MODEL}


# ============================================================ projects
@app.get("/api/projects")
def list_projects() -> list[dict]:
    return db.list_projects()


@app.post("/api/projects")
def create_project(body: CreateProject) -> dict:
    pid = db.create_project(body.title, body.model, body.target_chapters, body.chapters_per_arc)
    if body.use_scenes:
        db.update_project(pid, use_scenes=1)
    # Optionally seed taste + learned from a saved profile, skipping the taste step.
    if body.taste_profile_id:
        prof = db.get_taste_profile(body.taste_profile_id)
        if prof:
            db.update_project(pid, taste=prof["taste"], learned=prof["learned"], status="bible")
    return db.get_project(pid)


@app.post("/api/projects/{pid}/settings")
async def update_settings(pid: int, body: SettingsInput) -> dict:
    """Per-project toggles: scene-by-scene writing, and the local model used going forward."""
    _require(pid)
    if body.use_scenes is not None:
        db.update_project(pid, use_scenes=1 if body.use_scenes else 0)
    if body.model is not None:
        name = body.model.strip()
        if not name:
            raise HTTPException(400, "Model name required")
        installed = await oc.list_models() if await oc.is_up() else []
        if installed and name not in installed:
            raise HTTPException(400, f"Model '{name}' is not installed in Ollama")
        db.update_project(pid, model=name)
    return db.get_project(pid)


@app.get("/api/projects/{pid}")
def get_project(pid: int) -> dict:
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    p["written"] = db.chapter_count(pid)
    return p


@app.delete("/api/projects/{pid}")
def delete_project(pid: int) -> dict:
    db.delete_project(pid)
    return {"ok": True}


# ============================================================ pipeline stages
def _require(pid: int) -> dict:
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@app.get("/api/taste-prompt")
def taste_prompt() -> dict:
    """The copy-paste interview prompt for the optional 'power mode' (Idea 1b)."""
    return {"prompt": prompts.EXTERNAL_INTERVIEW_PROMPT}


@app.get("/api/full-plan-prompt")
def full_plan_prompt(chapters: int = 100, per_arc: int = 10) -> dict:
    """A copy-paste prompt for a big external LLM to produce the WHOLE plan (bible + volumes +
    arcs + every chapter beat) for the given size, so the local model can write from chapter 1."""
    return {"prompt": prompts.full_plan_prompt(max(1, chapters), max(1, per_arc))}


@app.post("/api/projects/{pid}/import-plan")
def import_plan(pid: int, body: PlanImport) -> dict:
    """Store a full externally-made plan and jump straight to writing chapter 1."""
    p = _require(pid)
    parts = pipeline.normalize_plan(body.plan, p["chapters_per_arc"])
    if not parts["bible"]:
        raise HTTPException(400, "The plan must include a 'bible' object.")
    outline = parts["outline"]
    nums = [c.get("number") for c in outline if isinstance(c.get("number"), int)]
    # Make the novel's length MATCH the pasted plan, so writing doesn't overrun into unplanned
    # chapters (generic beats) or stop early at a phantom target.
    target = max(nums) if nums else p["target_chapters"]
    # Flag a malformed plan (gaps or duplicate chapter numbers) so the user knows.
    issues = []
    if db.chapter_count(pid) > 0:
        issues.append("this project already has written chapters — they may not match the new plan's "
                      "numbering")
    if nums:
        seen, dupes = set(), set()
        for n in nums:
            (dupes if n in seen else seen).add(n)
        missing = sorted(set(range(1, max(nums) + 1)) - seen)
        if missing:
            issues.append(f"{len(missing)} missing chapter number(s) — gaps in the plan")
        if dupes:
            issues.append(f"{len(sorted(dupes))} duplicate chapter number(s)")
    fields = {
        "bible": parts["bible"], "volume_map": parts["volume_map"],
        "arc_map": parts["arc_map"], "outline": outline, "target_chapters": target,
        "title": parts["bible"].get("title", p["title"]), "status": "writing",
    }
    if parts["taste"] is not None:
        fields["taste"] = parts["taste"]
    db.update_project(pid, **fields)
    return {"ok": True, "chapters_planned": len(outline), "target_chapters": target,
            "arcs": len(parts["arc_map"]), "volumes": len(parts["volume_map"]), "issues": issues}


@app.post("/api/projects/{pid}/taste")
async def gen_taste(pid: int, body: TasteInput) -> dict:
    p = _require(pid)
    taste = await pipeline.build_taste_profile(p["model"], body.raw)
    db.update_project(pid, taste=taste, status="bible")
    return taste


@app.post("/api/projects/{pid}/taste/import")
def import_taste(pid: int, body: TasteImport) -> dict:
    """Store a taste profile produced by an external LLM. No local model call."""
    _require(pid)
    taste = pipeline.normalize_taste(body.profile)
    db.update_project(pid, taste=taste, status="bible")
    return taste


def _arc_volume_counts(project: dict) -> tuple[int, int]:
    """(num_arcs, num_volumes) for a project, from its chapter/arc settings."""
    per_arc = max(1, project["chapters_per_arc"])
    num_arcs = max(1, -(-project["target_chapters"] // per_arc))  # ceil
    # Aim for ~5 arcs per volume; keep it in a sensible 1–8 range.
    num_volumes = min(max(1, round(num_arcs / 5)), 8) if num_arcs >= 2 else 1
    return num_arcs, num_volumes


@app.post("/api/projects/{pid}/bible")
async def gen_bible(pid: int, body: BibleInput) -> dict:
    """Layer 1a: the lean core bible."""
    p = _require(pid)
    bible = await pipeline.build_bible(p["model"], p["taste"], body.premise_hint, p["target_chapters"])
    title = bible.get("title", p["title"])
    db.update_project(pid, bible=bible, title=title, status="volume_map")
    return bible


@app.post("/api/projects/{pid}/volume-map")
async def gen_volume_map(pid: int) -> dict:
    """Layer 0: split the whole novel into a few big volumes (planning layer 2)."""
    p = _require(pid)
    num_arcs, num_volumes = _arc_volume_counts(p)
    volume_map = await pipeline.build_volume_map(p["model"], p["bible"], p["taste"],
                                                 num_volumes, num_arcs)
    db.update_project(pid, volume_map=volume_map, status="arc_map")
    return {"volume_map": volume_map, "num_volumes": num_volumes}


@app.post("/api/projects/{pid}/arc-map")
async def gen_arc_map(pid: int) -> dict:
    """Layer 1b: the high-level map of the whole novel (all arcs, title + goal)."""
    p = _require(pid)
    num_arcs, _ = _arc_volume_counts(p)
    per_arc = max(1, p["chapters_per_arc"])
    arc_map = await pipeline.build_arc_map(p["model"], p["bible"], p["taste"], num_arcs,
                                           per_arc, p.get("volume_map"))
    db.update_project(pid, arc_map=arc_map, status="outline")
    return {"arc_map": arc_map, "num_arcs": num_arcs}


@app.post("/api/projects/{pid}/repair")
async def repair(pid: int) -> dict:
    """Heal the novel: fill missing chapter/arc/volume summaries, flag cut-off chapters."""
    p = _require(pid)
    return await pipeline.repair_novel(p)


@app.post("/api/projects/{pid}/primer")
async def gen_primer(pid: int) -> dict:
    """Generate the optional spoiler-free 'Chapter 0' primer from the bible."""
    p = _require(pid)
    if not p.get("bible"):
        raise HTTPException(400, "Build the story bible first.")
    intro = await pipeline.build_primer(p["model"], p["bible"])
    db.update_project(pid, intro=intro)
    return {"intro": intro}


@app.post("/api/projects/{pid}/outline/{arc_number}")
async def gen_arc_outline(pid: int, arc_number: int) -> dict:
    """Layer 2: expand one arc into chapter beats (guided by the arc map) + add new characters."""
    p = _require(pid)
    per_arc = p["chapters_per_arc"]
    start = (arc_number - 1) * per_arc + 1
    end = min(arc_number * per_arc, p["target_chapters"])
    if start > p["target_chapters"]:
        raise HTTPException(400, "Arc beyond target chapter count")

    # The arc's goal from the master plan (layer 1), if we have it.
    arc_goal = ""
    for a in p.get("arc_map", []):
        if a.get("number") == arc_number:
            arc_goal = a.get("goal", "")
            break

    prev_arcs = [a["summary"] for a in db.list_arcs(pid)]
    arc = await pipeline.build_arc_outline(
        p["model"], p["bible"], p["taste"], arc_number, start, end, prev_arcs, arc_goal
    )
    # Append/replace this arc's chapters in the stored outline.
    outline = [c for c in p["outline"] if not (start <= c.get("number", 0) <= end)]
    outline.extend(arc["chapters"])
    outline.sort(key=lambda c: c["number"])

    # Merge any newly-introduced characters into the bible (dedupe by name).
    bible = p["bible"]
    chars = bible.get("characters", []) if isinstance(bible.get("characters"), list) else []
    known = {str(c.get("name", "")).lower() for c in chars}
    for nc in arc.get("new_characters", []):
        nm = str(nc.get("name", "")).strip()
        if nm and nm.lower() not in known:
            chars.append(nc)
            known.add(nm.lower())
    bible["characters"] = chars

    db.update_project(pid, outline=outline, bible=bible, status="writing")
    return {"arc": arc, "total_planned": len(outline)}


@app.post("/api/projects/{pid}/write")
async def write_chapter(
    pid: int, body: WriteInput,
    x_llm_key: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
    x_llm_provider: str | None = Header(default=None),
):
    """Stream a chapter's text as it's generated (text/plain chunks).

    A brand-new chapter is **autosaved progressively as it streams**, so an in-progress new
    chapter is never lost if interrupted. But when RE-ROLLING a chapter that was already finalized
    (it has a saved summary = known-good prose), we DON'T overwrite that good row with partials —
    only a successful /finalize commits the new version. So a cancelled/failed re-roll keeps your
    original chapter intact.
    """
    p = _require(pid)
    beat = pipeline.find_beat(p, body.number)
    existing = db.get_chapter(pid, body.number)
    # "protect": the chapter is already finalized (has a summary) → this is a re-roll of good prose.
    protect = bool(existing and (existing.get("summary") or "").strip())

    async def gen():
        # Re-assert the cloud config inside the streaming context (so it's set wherever this
        # generator is iterated), then clear it when done.
        token = oc.set_cloud(x_llm_key, x_llm_model, x_llm_provider)
        full = ""
        errored = False
        i = 0
        try:
            async for chunk in pipeline.write_chapter_stream(
                p, body.number, body.target_words, apply_steering=body.apply_steering):
                full += chunk
                i += 1
                # Autosave partials only for NEW chapters; never clobber a finalized one mid-stream.
                if not protect and i % 16 == 0 and full.strip():
                    db.save_chapter(pid, body.number, beat["title"], full.strip(), "")
                yield chunk
        except oc.OllamaError as e:
            # The stream already returned HTTP 200, so we can't change the status code. Send the
            # real error (e.g. a cloud model/quota/key problem) inline with a sentinel the client
            # detects, so the user sees WHY instead of a generic "write failed".
            errored = True
            yield "\x00\x00LLMERR" + str(e)
        finally:
            # Persist the partial only for new chapters (and only if it didn't error). For a re-roll
            # of a finalized chapter, leave the original untouched — /finalize will commit the new text.
            if full.strip() and not errored and not protect:
                db.save_chapter(pid, body.number, beat["title"], full.strip(), "")
            oc.reset_cloud(token)

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


@app.post("/api/projects/{pid}/finalize")
async def finalize_chapter(pid: int, body: FinalizeInput) -> dict:
    """Save + summarize a finished chapter (called after streaming completes)."""
    p = _require(pid)
    return await pipeline.finalize_chapter(p, body.number, body.content)


# ============================================================ learning (Idea 2)
@app.post("/api/projects/{pid}/feedback")
def submit_feedback(pid: int, body: FeedbackInput) -> dict:
    """Record reader feedback on a chapter and evolve the learned taste."""
    p = _require(pid)
    return pipeline.record_feedback(p, body.number, body.feedback)


@app.get("/api/projects/{pid}/learned")
def get_learned(pid: int) -> dict:
    """Current learned taste + steering note + confidence (for the UI)."""
    p = _require(pid)
    learned = p.get("learned") or {}
    return {
        "learned": learned,
        "steering": learning.steering_note(learned),
        "confidence": learning.confidence(learned),
    }


@app.get("/api/taste-profiles")
def list_taste_profiles() -> list[dict]:
    """Saved, named learned-taste profiles (reusable across novels)."""
    return db.list_taste_profiles()


@app.post("/api/taste-profiles/{profile_id}/rename")
def rename_taste_profile(profile_id: int, body: SaveTasteInput) -> dict:
    """Rename a saved taste profile."""
    if not db.get_taste_profile(profile_id):
        raise HTTPException(404, "Saved taste not found")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    if not db.rename_taste_profile(profile_id, name):
        raise HTTPException(409, "Another saved taste already uses that name")
    return {"id": profile_id, "name": name}


@app.delete("/api/taste-profiles/{profile_id}")
def delete_taste_profile(profile_id: int) -> dict:
    """Delete a saved taste profile (does not affect novels already created from it)."""
    db.delete_taste_profile(profile_id)
    return {"ok": True}


@app.post("/api/projects/{pid}/save-taste")
def save_taste(pid: int, body: SaveTasteInput) -> dict:
    """Save this project's taste + learned as a named, reusable profile."""
    p = _require(pid)
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Name required")
    learned = p.get("learned") or {}
    fc = int(learned.get("feedback_count", 0))
    prof_id = db.save_taste_profile(name, p["taste"], learned, fc)
    return {"id": prof_id, "name": name}


# ============================================================ reading / export
@app.get("/api/projects/{pid}/chapters")
def chapters(pid: int) -> list[dict]:
    _require(pid)
    return db.list_chapters(pid)


@app.get("/api/projects/{pid}/chapters/{number}")
def chapter(pid: int, number: int) -> dict:
    _require(pid)
    ch = db.get_chapter(pid, number)
    if not ch:
        raise HTTPException(404, "Chapter not written yet")
    return ch


@app.get("/api/projects/{pid}/export")
def export_markdown(pid: int):
    p = _require(pid)
    chs = db.list_chapters(pid, with_content=True)
    lines = [f"# {p['title']}\n"]
    if p["bible"].get("logline"):
        lines.append(f"*{p['bible']['logline']}*\n")
    if p.get("intro"):
        lines.append("\n## Chapter 0 — About this world\n")
        lines.append(p["intro"])
    for ch in chs:
        lines.append(f"\n## Chapter {ch['number']}: {ch['title']}\n")
        lines.append(ch["content"])
    text = "\n".join(lines)
    fname = f"{p['title'].replace(' ', '_')[:40] or 'novel'}.md"
    return PlainTextResponse(
        text,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        media_type="text/markdown; charset=utf-8",
    )


@app.get("/api/projects/{pid}/export-epub")
def export_epub(pid: int):
    """Download the whole novel as a real .epub (readable on phones / e-readers)."""
    p = _require(pid)
    chs = db.list_chapters(pid, with_content=True)
    data = epub.build_epub(p, chs)
    safe = "".join(c for c in (p["title"] or "novel") if c.isalnum() or c in " _-").strip()
    fname = (safe.replace(" ", "_")[:40] or "novel") + ".epub"
    return Response(
        content=data,
        media_type="application/epub+zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.post("/api/projects/{pid}/chapters/{number}/edit")
async def edit_chapter(pid: int, number: int, body: EditChapterInput) -> dict:
    """Save user-edited chapter text. For a real chapter we re-summarize it so memory
    stays correct; if that model call fails we keep the old summary (never lose the edit).
    number 0 edits the optional Chapter 0 intro."""
    p = _require(pid)
    content = body.content.strip()
    if number == 0:
        db.update_project(pid, intro=content)
        return {"number": 0, "intro": content}
    ch = db.get_chapter(pid, number)
    if not ch:
        raise HTTPException(404, "Chapter not written yet")
    title = (body.title or ch["title"] or f"Chapter {number}").strip()
    try:
        summary = (await pipeline.summarize_chapter(p["model"], number, title, content)).strip()
    except Exception:
        summary = ch["summary"]  # model hiccup → keep the old summary, but save the text
    db.save_chapter(pid, number, title, content, summary)
    return {"number": number, "title": title, "summary": summary}


# ============================================================ frontend (last)
@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
