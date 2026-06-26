"""The novel-generation pipeline.

Stages: taste profile -> story bible -> per-arc outline -> chapter writing loop.

The "no breaking over 100+ chapters" trick lives in build_context(): each new
chapter sees the bible + arc summaries + the most recent chapter summaries, which
stays a roughly constant size no matter how long the book gets.
"""
from __future__ import annotations

import asyncio
import re
from typing import AsyncIterator

from . import config, db, learning, ollama_client as oc, prompts

# Hard cap (chars) on the canonical story-state sheet, so it can't grow unbounded and blow the
# model's context window on a long novel. ~8000 chars ≈ ~1200 words (well above the ~500-word target).
_STATE_SHEET_CAP = 8000

# ----- persistent character roster (memory B+, fixes AUDIT #7 silent cast decay) -----
# The free-text state sheet drops old characters to stay short; the roster never does. We parse the
# CHARACTERS section the model already writes each chapter (no extra LLM call) and merge it into a
# durable per-character store, then inject the relevant slice (recently-seen + anyone named in the
# upcoming beat) into the writer's context so early characters are never forgotten when they return.
_SECTION_RE = re.compile(r"^\s*([A-Za-z][A-Za-z &/]{2,30}):\s*(.*)$")
_KNOWN_SECTIONS = {"CHARACTERS", "ALLIES", "ENEMIES", "ENEMIES & GRUDGES", "PROGRESSION",
                   "MC PROGRESSION", "PLACES", "ITEMS", "THREADS", "RULES"}


def _char_from_line(line: str):
    line = line.lstrip("-*•·–— ").strip()
    if not line:
        return None
    for sep in ("—", "–", " - ", ":"):     # name <sep> description (avoid bare '-' for hyphen names)
        if sep in line:
            name, desc = line.split(sep, 1)
            name, desc = name.strip(), desc.strip()
            return (name, desc) if name and len(name) <= 60 else None
    return (line, "") if len(line) <= 60 else None   # a bare short name, no description


def _parse_characters(sheet: str):
    """Pull (name, description) pairs from the CHARACTERS section of a state sheet (tolerant)."""
    out, in_chars = [], False
    for raw in (sheet or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _SECTION_RE.match(line)
        if m and m.group(1).upper().strip() in _KNOWN_SECTIONS:
            in_chars = m.group(1).upper().strip().startswith("CHARACTER")
            rest = m.group(2).strip()
            if in_chars and rest:
                nm = _char_from_line(rest)
                if nm:
                    out.append(nm)
            continue
        if in_chars:
            nm = _char_from_line(line)
            if nm:
                out.append(nm)
    return out


# Nameless extras ("Thug 2", "the guards", "servant boys") used to live in the roster forever and
# were fed to the writer every chapter as KNOWN CHARACTERS — noise that crowds out real characters.
_GENERIC_NOUNS = (r"thug|guard|servant|soldier|villager|vendor|merchant|bandit|cultivator|"
                  r"disciple|stranger|onlooker|crowd|mob|man|woman|men|women|boy|girl|boys|girls|"
                  r"child|children|figure|voice")
_GENERIC_NAME_RE = re.compile(
    r"^(the |a |an )?(burly |old |young |tall |short |fat |thin |masked |hooded |scarred )?"
    rf"(?:(?:{_GENERIC_NOUNS}) )?(?:{_GENERIC_NOUNS})s?( \d+)?$", re.I)


def _is_generic_name(name: str) -> bool:
    n = (name or "").strip()
    return not n or bool(_GENERIC_NAME_RE.match(n))


def _merge_cast(cast: dict, sheet: str, number: int) -> dict:
    """Merge this chapter's characters into the durable roster — append/update, never delete.
    Nameless extras are filtered out so the roster stays signal, not noise."""
    cast = dict(cast or {})
    for name, desc in _parse_characters(sheet):
        if _is_generic_name(name):
            continue
        e = dict(cast.get(name) or {"first_seen": number})
        if desc:
            e["desc"] = desc
        e["last_seen"] = number
        low = (desc or "").lower()
        if any(w in low for w in ("dead", "deceased", "killed", "slain")):
            e["status"] = "dead"
        else:
            e.setdefault("status", "alive")
        cast[name] = e
    return cast


def _ctx_mult() -> int:
    """Memory budgets scale up when a cloud model is writing — it has a far larger context window
    than the 4B laptop model the base budgets were tuned for."""
    return max(1, config.CLOUD_CTX_MULT) if oc.cloud_active() else 1


def _cast_context(project: dict, cast: dict, upcoming_number: int, budget: int = 1500) -> str:
    """A bounded 'who's who' for the writer: anyone named in the upcoming beat (always kept) plus the
    most recently-seen characters, so an early character returning later is never forgotten."""
    if not cast:
        return ""
    budget *= _ctx_mult()
    beat = find_beat(project, upcoming_number)
    beat_text = (str(beat.get("beat", "")) + " " + str(beat.get("title", ""))).lower()
    scored = []
    for name, e in cast.items():
        in_beat = name.lower() in beat_text
        scored.append((1 if in_beat else 0, int(e.get("last_seen", 0)), name, e))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)   # in-beat first, then most-recent
    lines, used = [], 0
    for in_beat, _rec, name, e in scored:
        status = e.get("status", "alive")
        desc = e.get("desc", "")
        line = f"  {name} ({status})" + (f" — {desc}" if desc else "")
        if not in_beat and (used + len(line) > budget or len(lines) >= 30):
            continue                                        # keep in-beat ones even past the cap
        lines.append(line)
        used += len(line) + 1
    if not lines:
        return ""
    return "KNOWN CHARACTERS (stay consistent — do not forget or contradict these):\n" + "\n".join(lines)


# --------------------------------------------------------------------------- taste
_TASTE_KEYS = {
    "genres": list, "tone": str, "favorite_tropes": list, "disliked_tropes": list,
    "protagonist_type": str, "pacing": str, "heat_level": str, "pov": str,
    "setting": str, "themes": list, "power_system": str, "antagonist": str,
    "ending": str, "humor": str, "conflict_scale": str, "content_limits": str,
    "style_notes": str, "inspirations": list,
}


async def build_taste_profile(model: str, raw_inputs: dict) -> dict:
    return await oc.chat_json(model, prompts.TASTE_SYSTEM, prompts.taste_user(raw_inputs))


async def repair_novel(project: dict) -> dict:
    """Heal a novel after an interruption: fill any MISSING chapter/arc/volume summaries and
    flag cut-off chapters. Does NOT rewrite chapter prose or the bible (that would change the story).
    """
    pid = project["id"]
    model = project["model"]
    per_arc = max(1, project["chapters_per_arc"])
    report = {"summaries_fixed": [], "arcs_fixed": [], "volumes_fixed": [], "flagged_chapters": []}

    chs = db.list_chapters(pid, with_content=True)
    # 1) missing chapter summaries + flag likely-truncated chapters
    for c in chs:
        content = (c["content"] or "").strip()
        if not content:
            continue
        if not (c["summary"] or "").strip():
            s = await summarize_chapter(model, c["number"], c["title"], content)
            db.save_chapter(pid, c["number"], c["title"], content, s.strip())
            report["summaries_fixed"].append(c["number"])
        wc = len(content.split())
        if wc < 150 or content[-1] not in ".!?\"')]”’":   # short or no sentence-ending = likely cut off
            report["flagged_chapters"].append(c["number"])

    maxnum = max((c["number"] for c in chs), default=0)
    completed_arcs = maxnum // per_arc
    sum_by_num = {c["number"]: (c["summary"] or "") for c in db.list_chapters(pid)}

    # 2) missing arc summaries for fully-written arcs
    existing_arcs = {a["number"] for a in db.list_arcs(pid)}
    for arc in range(1, completed_arcs + 1):
        if arc in existing_arcs:
            continue
        start, end = (arc - 1) * per_arc + 1, arc * per_arc
        if all(sum_by_num.get(n) for n in range(start, end + 1)):
            summaries = [f"Ch {n}: {sum_by_num[n]}" for n in range(start, end + 1)]
            txt = await oc.chat(model, prompts.ARC_SUMMARY_SYSTEM,
                                prompts.arc_summary_user(arc, summaries), temperature=0.3)
            db.save_arc(pid, arc, txt.strip())
            report["arcs_fixed"].append(arc)

    # 3) missing volume summaries for fully-written volumes
    existing_vols = {v["number"] for v in db.list_volumes(pid)}
    arc_sum = {a["number"]: a["summary"] for a in db.list_arcs(pid)}
    for v in project.get("volume_map", []):
        if v["number"] in existing_vols:
            continue
        a0, a1 = int(v.get("arc_start", 0)), int(v.get("arc_end", 0))
        if a1 and a1 <= completed_arcs and all(arc_sum.get(n) for n in range(a0, a1 + 1)):
            summaries = [f"Arc {n}: {arc_sum[n]}" for n in range(a0, a1 + 1)]
            txt = await oc.chat(model, prompts.VOLUME_SUMMARY_SYSTEM,
                                prompts.volume_summary_user(v["number"], summaries), temperature=0.3)
            db.save_volume(pid, v["number"], txt.strip())
            report["volumes_fixed"].append(v["number"])

    return report


async def build_primer(model: str, bible: dict) -> str:
    """The optional spoiler-free 'Chapter 0' primer, tailored to this novel's genre."""
    text = await oc.chat(model, prompts.PRIMER_SYSTEM, prompts.primer_user(bible), temperature=0.6)
    return text.strip()


def normalize_plan(plan: dict, per_arc: int) -> dict:
    """Coerce an externally-supplied full plan (bible + volume_map + arc_map + outline) into our
    shapes. Tolerant of small model/formatting slips. Returns the pieces to store."""
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a JSON object.")
    bible = plan.get("bible") if isinstance(plan.get("bible"), dict) else {}
    volume_map = plan.get("volume_map") if isinstance(plan.get("volume_map"), list) else []
    arc_map = plan.get("arc_map") if isinstance(plan.get("arc_map"), list) else []
    raw_outline = plan.get("outline") if isinstance(plan.get("outline"), list) else []
    per_arc = max(1, per_arc)

    outline = []
    for i, ch in enumerate(raw_outline):
        if not isinstance(ch, dict):
            continue
        try:
            num = int(ch.get("number", i + 1))
        except (TypeError, ValueError):
            num = i + 1
        try:
            arc = int(ch.get("arc", (num - 1) // per_arc + 1))
        except (TypeError, ValueError):
            arc = (num - 1) // per_arc + 1
        outline.append({
            "number": num,
            "title": str(ch.get("title", f"Chapter {num}")).strip() or f"Chapter {num}",
            "beat": str(ch.get("beat", "")).strip(),
            "arc": arc,
        })
    outline.sort(key=lambda c: c["number"])

    taste = plan.get("taste") if isinstance(plan.get("taste"), dict) else None
    return {"bible": bible, "volume_map": volume_map, "arc_map": arc_map,
            "outline": outline, "taste": taste}


def normalize_taste(profile: dict) -> dict:
    """Coerce an externally-supplied taste profile into our expected shape (Idea 1b)."""
    if not isinstance(profile, dict):
        raise ValueError("Taste profile must be a JSON object.")
    out: dict = {}
    for key, kind in _TASTE_KEYS.items():
        val = profile.get(key)
        if kind is list:
            if isinstance(val, str):
                val = [v.strip() for v in val.split(",") if v.strip()]
            out[key] = val if isinstance(val, list) else []
        else:
            out[key] = str(val) if val is not None else ""
    return out


# --------------------------------------------------------------------------- bible
async def build_bible(model: str, taste: dict, premise_hint: str, target_chapters: int) -> dict:
    return await oc.chat_json(
        model, prompts.BIBLE_SYSTEM, prompts.bible_user(taste, premise_hint, target_chapters),
        temperature=0.8,
    )


# --------------------------------------------------------------------------- volume map (layer 0)
async def build_volume_map(model: str, bible: dict, taste: dict, num_volumes: int,
                           num_arcs: int) -> list[dict]:
    """Group the novel's arcs into a few big volumes (title + theme + arc range). Layer 0."""
    result = await oc.chat_json(
        model, prompts.VOLUME_MAP_SYSTEM,
        prompts.volume_map_user(bible, taste, num_volumes, num_arcs),
        temperature=0.7,
    )
    vols = result.get("volumes", []) if isinstance(result, dict) else []
    fixed = []
    # Default even split, used to repair any missing/odd ranges from the model.
    base = max(1, num_arcs // num_volumes)
    for i in range(num_volumes):
        v = vols[i] if i < len(vols) else {}
        default_start = i * base + 1
        default_end = num_arcs if i == num_volumes - 1 else (i + 1) * base
        try:
            start = int(v.get("arc_start", default_start))
            end = int(v.get("arc_end", default_end))
        except (TypeError, ValueError):
            start, end = default_start, default_end
        fixed.append({
            "number": i + 1,
            "title": str(v.get("title", f"Volume {i + 1}")).strip() or f"Volume {i + 1}",
            "theme": str(v.get("theme", "")).strip(),
            "arc_start": start,
            "arc_end": end,
        })
    # P5: force the volumes to TILE arcs 1..num_arcs with no gaps or overlaps, even if the model
    # returned ranges that overlapped or skipped arcs. Each volume starts right after the previous
    # one ends; the last volume always reaches the final arc. (Bad ranges would otherwise make the
    # "story so far" memory skip or double-count whole arcs.)
    prev_end = 0
    last = len(fixed) - 1
    for i, v in enumerate(fixed):
        start = min(prev_end + 1, num_arcs)
        if i == last:
            end = num_arcs
        else:
            end = max(start, min(int(v["arc_end"]), num_arcs))
        v["arc_start"], v["arc_end"] = start, end
        prev_end = end
    return fixed


# --------------------------------------------------------------------------- arc map (layer 1)
async def build_arc_map(model: str, bible: dict, taste: dict, num_arcs: int,
                        chapters_per_arc: int, volume_map: list[dict] | None = None) -> list[dict]:
    """High-level map of the whole novel: one entry per arc (title + goal). Layer 1."""
    result = await oc.chat_json(
        model, prompts.ARC_MAP_SYSTEM,
        prompts.arc_map_user(bible, taste, num_arcs, chapters_per_arc, volume_map),
        temperature=0.7,
    )
    arcs = result.get("arcs", []) if isinstance(result, dict) else []
    fixed = []
    for i in range(num_arcs):
        a = arcs[i] if i < len(arcs) else {}
        fixed.append({
            "number": i + 1,
            "title": str(a.get("title", f"Arc {i + 1}")).strip() or f"Arc {i + 1}",
            "goal": str(a.get("goal", "")).strip(),
        })
    return fixed


# --------------------------------------------------------------------------- outline (layer 2)
async def build_arc_outline(
    model: str, bible: dict, taste: dict, arc_number: int, start_ch: int, end_ch: int,
    prev_arc_summaries: list[str], arc_goal: str = "",
) -> dict:
    """Expand one arc into chapter beats + the new characters it introduces. Layer 2.
    Returns {arc_title, arc_goal, new_characters:[...], chapters:[...]}."""
    result = await oc.chat_json(
        model, prompts.OUTLINE_SYSTEM,
        prompts.outline_arc_user(bible, taste, arc_number, start_ch, end_ch,
                                 prev_arc_summaries, arc_goal),
        temperature=0.7,
    )
    # Force EXACTLY (end_ch - start_ch + 1) chapters, numbered in order, so the writer loop never
    # hits a missing plan (too few → blank/generic chapters) or a number that overruns into the next
    # arc (too many). Pad any shortfall with an arc-goal-aware default (the plan-sharpener will turn
    # it into a concrete scene before writing); drop any extras.
    n = end_ch - start_ch + 1
    raw = result.get("chapters", []) or []
    default_beat = (f"Advance Arc {arc_number} toward its goal: {arc_goal}".strip()
                    if arc_goal else "Advance the arc and raise the stakes toward its climax.")
    fixed = []
    for i in range(n):
        ch = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
        num = start_ch + i
        beat = str(ch.get("beat", "")).strip() or default_beat
        fixed.append({
            "number": num,
            "title": str(ch.get("title", f"Chapter {num}")).strip() or f"Chapter {num}",
            "beat": beat,
            "arc": arc_number,
        })
    result["chapters"] = fixed
    if not isinstance(result.get("new_characters"), list):
        result["new_characters"] = []
    return result


# --------------------------------------------------------------------------- memory
def build_context(project: dict, upcoming_number: int) -> str:
    """Assemble the 'story so far' the writer model needs for the next chapter.

    Hierarchical: completed-arc summaries (broad strokes) + recent chapter
    summaries (fine detail). Trimmed to a character budget so it never blows up.
    """
    pid = project["id"]
    budget = config.ROLLING_SUMMARY_BUDGET * _ctx_mult()

    # Broad-strokes HEAD (always kept): the persistent character roster (so early characters who
    # return aren't forgotten) + whole-volume summaries + not-yet-folded arc summaries.
    head: list[str] = []
    cast_block = _cast_context(project, (project.get("state") or {}).get("cast") or {}, upcoming_number)
    if cast_block:
        head.append(cast_block + "\n")
    volumes = db.list_volumes(pid)
    covered_until_arc = 0
    if volumes:
        vm = {v["number"]: v for v in project.get("volume_map", [])}
        head.append("EARLIER VOLUMES:")
        head.extend(f"  Volume {v['number']}: {v['summary']}" for v in volumes)
        for v in volumes:
            info = vm.get(v["number"]) or {}
            covered_until_arc = max(covered_until_arc, int(info.get("arc_end", 0) or 0))
    arcs = [a for a in db.list_arcs(pid) if a["number"] > covered_until_arc]
    if arcs:
        head.append("\nEARLIER ARCS:")
        head.extend(f"  Arc {a['number']}: {a['summary']}" for a in arcs)

    # Recent chapter detail (bounded by the chapter being written so a regenerate never sees its
    # own old summary). Newest-first within budget — a cloud model gets a deeper window.
    recent = db.recent_summaries(pid, limit=12 * _ctx_mult(), before_number=upcoming_number)
    recent_lines = [f"  Ch {r['number']} ({r['title']}): {r['summary']}" for r in recent]

    if not head and not recent_lines:
        return "(This is the very first chapter. Establish the opening.)"

    head_text = "\n".join(head)
    # Always keep the broad-strokes head; then fill in as many RECENT chapters as fit (newest first),
    # instead of a raw byte-slice that could drop the high-level throughline or cut mid-sentence.
    remaining = budget - len(head_text) - len("\nRECENT CHAPTERS:\n")
    kept: list[str] = []
    for line in reversed(recent_lines):
        if remaining - (len(line) + 1) < 0:
            break
        kept.append(line)
        remaining -= len(line) + 1
    kept.reverse()
    out = head_text + (("\nRECENT CHAPTERS:\n" + "\n".join(kept)) if kept else "")

    # Safety: if the head alone still exceeds budget (very long volume/arc summaries), drop whole
    # oldest detail lines rather than slicing characters mid-sentence.
    if len(out) > budget:
        lines = out.split("\n")
        while len(lines) > 1 and len("\n".join(lines)) > budget:
            del lines[1]
        out = "\n".join(lines)
    return out


_PREV_TAIL_CHARS = 700


def _prev_chapter_tail(project: dict, upcoming_number: int) -> str:
    """The last few hundred characters of the previous chapter's prose, so the writer can
    continue the same voice and momentum instead of recapping from a summary. Empty for the
    first chapter (or if the previous chapter has no saved prose yet)."""
    if upcoming_number is None or upcoming_number <= 1:
        return ""
    prev = db.get_chapter(project["id"], upcoming_number - 1)
    if not prev:
        return ""
    content = (prev.get("content") or "").strip()
    if not content:
        return ""
    return content[-_PREV_TAIL_CHARS:].lstrip()


async def summarize_chapter(model: str, number: int, title: str, content: str) -> str:
    return await oc.chat(
        model, prompts.SUMMARY_SYSTEM, prompts.summary_user(number, title, content),
        temperature=0.3,
    )


def _arc_of(project: dict, number: int) -> int | None:
    """Which arc a chapter belongs to — from its stored 'arc' field, falling back to the uniform
    arc size for older novels that predate the field."""
    for ch in project.get("outline", []):
        if ch.get("number") == number and isinstance(ch.get("arc"), int):
            return ch["arc"]
    per = project.get("chapters_per_arc") or 0
    return ((number - 1) // per + 1) if per > 0 else None


def _last_chapter_of_arc(project: dict, arc_number: int) -> int | None:
    """The highest chapter number planned for an arc (so we roll it up only when it truly ends)."""
    nums = [ch["number"] for ch in project.get("outline", [])
            if ch.get("arc") == arc_number and isinstance(ch.get("number"), int)]
    return max(nums) if nums else None


async def maybe_roll_up_arc(model: str, project: dict, finished_number: int) -> None:
    """When an arc's LAST chapter is finished, compress that arc into one summary. Works for the
    final short arc and for uneven (imported) plans, because it keys off the chapter's real arc."""
    arc_number = _arc_of(project, finished_number)
    if not arc_number:
        return
    last = _last_chapter_of_arc(project, arc_number)
    if last is None or finished_number != last:
        return                                  # not the end of this arc yet
    arc_nums = sorted(ch["number"] for ch in project.get("outline", [])
                      if ch.get("arc") == arc_number and isinstance(ch.get("number"), int))
    sum_by_num = {r["number"]: (r["summary"] or "") for r in db.list_chapters(project["id"])}
    summaries = [f"Ch {n}: {sum_by_num[n]}" for n in arc_nums if sum_by_num.get(n)]
    if not summaries:
        return
    arc_summary = await oc.chat(
        model, prompts.ARC_SUMMARY_SYSTEM, prompts.arc_summary_user(arc_number, summaries),
        temperature=0.3,
    )
    db.save_arc(project["id"], arc_number, arc_summary.strip())


async def maybe_roll_up_volume(model: str, project: dict, finished_number: int) -> None:
    """When the last arc of a volume completes, compress that volume's arcs into one summary (A)."""
    arc_number = _arc_of(project, finished_number)
    if not arc_number:
        return
    last = _last_chapter_of_arc(project, arc_number)
    if last is None or finished_number != last:
        return                                  # this arc hasn't finished yet
    volume = None
    for v in project.get("volume_map", []):
        if int(v.get("arc_end", -1)) == arc_number:
            volume = v
            break
    if not volume:
        return
    arc_rows = db.list_arcs(project["id"])
    summaries = [
        f"Arc {a['number']}: {a['summary']}"
        for a in arc_rows
        if int(volume["arc_start"]) <= a["number"] <= int(volume["arc_end"])
    ]
    if not summaries:
        return
    vol_summary = await oc.chat(
        model, prompts.VOLUME_SUMMARY_SYSTEM,
        prompts.volume_summary_user(volume["number"], summaries), temperature=0.3,
    )
    db.save_volume(project["id"], volume["number"], vol_summary.strip())


def _state_focus(project: dict) -> str:
    """A one-line, genre-aware hint so the state sheet tracks what matters for THIS story
    (e.g. cultivation realms & sects, or litRPG stats) — without any per-genre branching."""
    taste = project.get("taste") or {}
    genres = taste.get("genres") or []
    if isinstance(genres, str):
        genres = [genres]
    g = ", ".join(str(x) for x in genres[:3] if x)
    ps = (project.get("bible") or {}).get("power_system") or ""
    bits = []
    if g:
        bits.append(f"Genre: {g}.")
    if ps:
        bits.append(f"Power/progression system: {str(ps)[:200]}.")
    if not bits:
        return ""
    return "FOCUS FOR THIS STORY (track what matters here): " + " ".join(bits)


async def update_state(model: str, project: dict, number: int, title: str, content: str) -> dict:
    """Update the canonical story-state ledger from a finished chapter (memory B)."""
    prev = (project.get("state") or {}).get("sheet", "")
    sheet = await oc.chat(
        model, prompts.STATE_SYSTEM,
        prompts.state_update_user(prev, number, title, content, focus=_state_focus(project)),
        temperature=0.2,
    )
    sheet = sheet.strip()
    # Hard cap so the canonical sheet can't grow without bound and silently blow the model's
    # context window on a long novel. Keep the HEAD (CHARACTERS come first in the sheet) and drop
    # from the tail at a line boundary. (Mitigation; a structured per-character store is the
    # longer-term fix — see docs/AUDIT.md #7.)
    if len(sheet) > _STATE_SHEET_CAP:
        sheet = sheet[:_STATE_SHEET_CAP].rsplit("\n", 1)[0].rstrip()
    # Merge this chapter's characters into the durable roster (kept ALONGSIDE the sheet, never
    # trimmed) so a long novel's cast can't silently decay. Backward-compatible: old novels simply
    # start building a roster from here on.
    prev_state = project.get("state") or {}
    cast = _merge_cast(prev_state.get("cast") or {}, sheet, number)
    state = {"sheet": sheet, "cast": cast}
    db.update_project(project["id"], state=state)
    return state


# --------------------------------------------------------------------------- writer
def _writer_bible(bible: dict) -> dict:
    """A trimmed copy of the bible for the chapter prompt (fixes P3/P8). The bible's character list
    GROWS every arc (new_characters are merged in), and the full thing was dumped into every chapter
    prompt — bloating it and duplicating the state sheet + persistent roster, which already tell the
    writer who's who. Keep the core fields and cap the character list to the core cast."""
    if not isinstance(bible, dict):
        return bible
    b = dict(bible)
    chars = b.get("characters")
    if isinstance(chars, list) and len(chars) > 8:
        b["characters"] = chars[:8]   # the original main cast; the roster covers everyone else
    return b


def find_beat(project: dict, number: int) -> dict:
    for ch in project["outline"]:
        if ch.get("number") == number:
            return ch
    # No stored plan for this chapter (e.g. a gap in an imported plan). Don't fall back to a flavorless
    # "continue the story" — point it at the current arc's goal so it still advances the plot (P9).
    # The plan-sharpener then turns this into a concrete scene before writing.
    goal = _arc_goal_for(project, number)
    beat = (f"Advance this arc toward its goal: {goal}" if goal
            else "Continue the story naturally, raising the stakes of the current arc.")
    return {"number": number, "title": f"Chapter {number}", "beat": beat}


def _arc_goal_for(project: dict, number: int) -> str:
    """Where this part of the story is heading (the arc's goal), used to anchor plan sharpening."""
    per = project.get("chapters_per_arc") or 0
    if per <= 0:
        return ""
    arc_no = (number - 1) // per + 1
    for a in project.get("arc_map") or []:
        if a.get("number") == arc_no:
            return a.get("goal", "") or ""
    return ""


# ---- tension curve: a deterministic role for each chapter from its position in the arc ----
# No model call, no stored data — so it can never fail or drift. Uniform max-tension chapters with
# a cliffhanger every single time is itself an AI tell; roles give the arc a human rhythm.
def _chapter_role(project: dict, number: int) -> str:
    if number <= 0:
        return ""
    arc_no = _arc_of(project, number)
    if not arc_no:
        return "rising"
    nums = sorted(ch["number"] for ch in project.get("outline", [])
                  if ch.get("arc") == arc_no and isinstance(ch.get("number"), int))
    if number not in nums:                      # not planned yet — assume mid-arc
        return "rising"
    idx, n = nums.index(number) + 1, len(nums)
    if n < 4:                                   # tiny arcs: just open and close
        return "setup" if idx == 1 else ("climax" if idx == n else "rising")
    if idx == 1:
        return "setup"
    if idx == n:
        return "climax"
    if idx == n - 1:
        return "turn"
    if idx == (n // 2) + 1:                     # one mid-arc breather
        return "breather"
    return "rising"


# Climaxes earn more room; breathers shouldn't be padded to the same length as everything else.
_ROLE_WORDS = {"climax": 1.25, "turn": 1.1, "breather": 0.85}


def _role_words(role: str, target_words: int) -> int:
    return max(300, int(target_words * _ROLE_WORDS.get(role, 1.0)))


def _next_beat_line(project: dict, number: int) -> str:
    """One line of the NEXT chapter's plan so this chapter's ending can lean toward it."""
    for ch in project.get("outline", []):
        if ch.get("number") == number + 1:
            beat = str(ch.get("beat", "")).strip()
            title = str(ch.get("title", "")).strip()
            if beat:
                return f"Chapter {number + 1} ({title}): {beat[:300]}"
            break
    return ""


_RECALL_GAP = 8          # "long-absent" = not seen for at least this many chapters
_RECALL_MAX_CHARS = 4    # at most this many returning characters per chapter


def _returning_recall(project: dict, upcoming_number: int) -> str:
    """When the upcoming chapter's plan names characters who haven't appeared in a while, pull the
    actual summaries of the chapters where they last appeared — so a returner comes back with their
    real history, not just a one-line roster entry. Plain text search, no model call."""
    cast = (project.get("state") or {}).get("cast") or {}
    if not cast:
        return ""
    beat = find_beat(project, upcoming_number)
    beat_text = (str(beat.get("beat", "")) + " " + str(beat.get("title", ""))).lower()
    returning = []
    for name, e in cast.items():
        last = int(e.get("last_seen", 0) or 0)
        if name.lower() in beat_text and 0 < last <= upcoming_number - _RECALL_GAP:
            returning.append((last, name))
    if not returning:
        return ""
    returning.sort(reverse=True)
    returning = returning[:_RECALL_MAX_CHARS]
    rows = db.list_chapters(project["id"])
    blocks = []
    for last, name in returning:
        hits = [r for r in rows
                if r["number"] < upcoming_number and name.lower() in (r["summary"] or "").lower()]
        for r in hits[-2:]:                     # the 2 most recent chapters they appeared in
            blocks.append(f"  Ch {r['number']}: {r['summary']}")
        if not hits:
            desc = (cast[name] or {}).get("desc", "")
            blocks.append(f"  {name} (last seen ch {last}){' — ' + desc if desc else ''}")
    if not blocks:
        return ""
    return ("RETURNING CHARACTERS — they haven't appeared in a while; here is what actually "
            "happened with them (stay true to it):\n" + "\n".join(dict.fromkeys(blocks)))


# ---- per-novel voice card (generated once, lazily, best-effort) ----
async def ensure_voice_card(project: dict) -> str:
    """The novel's 'how this book sounds' spec. Generated at the first chapter write (covers new
    novels, imported plans, and old novels alike), stored inside the bible. Best-effort: failure
    just means chapters write without it, exactly as before."""
    bible = project.get("bible") or {}
    card = str(bible.get("voice_card") or "").strip()
    if card or bible.get("voice_card_failed"):
        return card
    try:
        card = (await oc.chat(project["model"], prompts.VOICE_CARD_SYSTEM,
                              prompts.voice_card_user(_writer_bible(bible),
                                                      project.get("taste") or {}),
                              temperature=0.6)).strip()
        card = card[:1400]
    except Exception:
        card = ""
    bible = dict(bible)
    if card:
        bible["voice_card"] = card
    else:
        bible["voice_card_failed"] = True       # don't retry on every single chapter
    try:
        db.update_project(project["id"], bible=bible)
        project["bible"] = bible
    except Exception:
        pass
    return card


def _polish_on() -> bool:
    """Editor pass switch: LN_POLISH=1 forces on, =0 forces off; 'auto' = on only when a cloud
    model is writing (fast there; on a local CPU it would double the wait)."""
    mode = config.POLISH_MODE
    if mode in ("1", "on", "true", "yes"):
        return True
    if mode in ("0", "off", "false", "no"):
        return False
    return oc.cloud_active()


_SHARPEN_PREAMBLE_RE = re.compile(
    r"^\s*(sure[,!.]?\s*)?(here(?:'s| is)[^:\n]*:|(?:the\s+)?(?:rewritten|sharper|revised|new)\s+"
    r"(?:chapter\s+)?plan:|chapter\s+plan:|plan:)\s*", re.I)
_SHARPEN_REFUSAL = ("i can't", "i cannot", "i'm unable", "i am unable", "as an ai", "i won't", "i will not")


def _clean_sharpened(text: str) -> str:
    """Tidy the plan-sharpener's reply (P6): strip code fences, a leading 'Here's the plan:' style
    preamble, and wrapping quotes. Returns '' for an obvious refusal so the original plan is kept."""
    t = (text or "").strip()
    t = re.sub(r"^```[a-z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t).strip()
    t = _SHARPEN_PREAMBLE_RE.sub("", t).strip()
    t = t.strip('"').strip("'").strip()
    if any(p in t.lower()[:80] for p in _SHARPEN_REFUSAL):
        return ""
    return t


async def sharpen_chapter_plan(project: dict, number: int, beat: dict, context: str) -> bool:
    """Right before writing, rewrite this chapter's plan into a concrete, higher-conflict scene
    (consistent with the story so far) and store it so re-writes stay consistent. Runs once per
    chapter (guarded by beat['sharpened']). Best-effort: any failure leaves the plan unchanged.

    Returns True if the plan was changed + persisted."""
    if number <= 0 or beat.get("sharpened"):
        return False
    original = (beat.get("beat") or "").strip()
    # A plan that is already long and concrete (e.g. written by a big model in Power mode) doesn't
    # need sharpening — rewriting it mostly bloats it and invents stray details. Leave it alone.
    if len(original) > 300:
        beat["sharpened"] = True
        try:
            db.update_project(project["id"], outline=project["outline"])
        except Exception:
            pass
        return False
    try:
        state = (project.get("state") or {}).get("sheet", "")
        arc_goal = _arc_goal_for(project, number)
        improved = await oc.chat(
            project["model"], prompts.SHARPEN_PLAN_SYSTEM,
            prompts.sharpen_plan_user(project["bible"], project.get("taste") or {}, arc_goal,
                                      context, state, number, beat.get("title", ""), original,
                                      role=_chapter_role(project, number)),
            temperature=0.7,
        )
        improved = _clean_sharpened(improved)
    except Exception:
        improved = ""
    # Mark as handled either way so we don't retry every re-roll; only overwrite if we got something
    # real and clearly not a refusal/echo.
    beat["sharpened"] = True
    changed = bool(improved) and improved.lower() != original.lower() and len(improved) > 20
    if changed:
        beat["beat"] = improved
    try:
        db.update_project(project["id"], outline=project["outline"])
    except Exception:
        pass
    return changed


async def write_chapter_stream(
    project: dict, number: int, target_words: int = 1200, apply_steering: bool = True,
) -> AsyncIterator[str]:
    """Stream a chapter's prose. Caller is responsible for saving + summarizing after.

    If the project has scene mode on (layer 3), the chapter is written scene-by-scene so the
    model never produces a whole chapter in one breath; otherwise it's one streamed call.

    apply_steering=False → a faithful redo: keep the bible/taste/memory but DON'T inject the
    learned-feedback steering, so fixing a cut-off chapter won't drift its style.
    """
    beat = find_beat(project, number)
    context = build_context(project, number)
    # Automatically sharpen this chapter's plan into a concrete, higher-conflict scene before
    # writing (once per chapter; stored so re-writes are consistent). No-op if it was already done.
    await sharpen_chapter_plan(project, number, beat, context)
    steering = learning.steering_note(project.get("learned")) if apply_steering else ""
    state = (project.get("state") or {}).get("sheet", "")
    prev_tail = _prev_chapter_tail(project, number)
    model = project["model"]
    voice_card = await ensure_voice_card(project)            # best-effort, generated once
    role = _chapter_role(project, number)
    words = _role_words(role, target_words)                  # climaxes longer, breathers shorter
    next_beat = _next_beat_line(project, number)
    recall = _returning_recall(project, number)

    if project.get("use_scenes"):
        async for chunk in _write_by_scenes(project, number, beat, context, steering, state,
                                            target_words, prev_tail, voice_card):
            yield chunk
        return

    # Big cloud models get the lean, voice-first brief; the strict rule-wall stays for small
    # local models, which genuinely need the babysitting.
    system = prompts.CHAPTER_SYSTEM_CLOUD if oc.cloud_active() else prompts.CHAPTER_SYSTEM
    user = prompts.chapter_user(
        _writer_bible(project["bible"]), project["taste"], context, number,
        beat["title"], beat["beat"], words, steering=steering, state=state,
        prev_tail=prev_tail, voice_card=voice_card, role=role, next_beat=next_beat,
        recall=recall,
    )

    # Editor pass (draft → revise): the draft is written quietly, then the REVISED chapter is what
    # streams to the reader. Default on for cloud, off for local CPU (LN_POLISH overrides).
    if _polish_on():
        draft = ""
        try:
            async for chunk in oc.chat_stream(model, system, user, prose=True):
                draft += chunk
        except Exception:
            draft = draft.strip()
            if not draft:
                raise
        draft = draft.strip()
        revised_any = False
        try:
            async for chunk in oc.chat_stream(
                model, prompts.EDITOR_SYSTEM,
                prompts.editor_user(draft, number, beat["title"], beat["beat"], state=state,
                                    voice_card=voice_card, role=role, target_words=words),
                temperature=0.6, prose=True,
            ):
                revised_any = True
                yield chunk
        except Exception:
            if revised_any:
                raise              # revised text already streamed; can't fall back cleanly
            yield draft            # editor failed before it began — the draft is still a chapter
        return

    async for chunk in oc.chat_stream(model, system, user, prose=True):
        yield chunk


async def _write_by_scenes(
    project: dict, number: int, beat: dict, context: str, steering: str, state: str,
    target_words: int, prev_tail: str = "", voice_card: str = "",
) -> AsyncIterator[str]:
    """Scene-by-scene writing (layer 3). Plan 2-3 scenes, then write each as a short call."""
    model = project["model"]
    try:
        plan = await oc.chat_json(model, prompts.SCENE_PLAN_SYSTEM,
                                  prompts.scene_plan_user(number, beat["title"], beat["beat"]))
        scenes = [str(s.get("beat", "")).strip() for s in plan.get("scenes", []) if s.get("beat")]
    except oc.OllamaError:
        scenes = []
    if not scenes:
        # Fall back to a normal single-call chapter if planning failed.
        user = prompts.chapter_user(_writer_bible(project["bible"]), project["taste"], context, number,
                                    beat["title"], beat["beat"], target_words,
                                    steering=steering, state=state, prev_tail=prev_tail,
                                    voice_card=voice_card)
        async for chunk in oc.chat_stream(model, prompts.CHAPTER_SYSTEM, user, prose=True):
            yield chunk
        return

    scene_words = max(150, target_words // len(scenes))
    written = ""
    for idx in range(len(scenes)):
        if idx:
            yield "\n\n"
            written += "\n\n"
        # Scene 1 continues from the previous chapter's tail; later scenes from what we just wrote.
        tail = written[-600:] if idx else prev_tail
        user = prompts.scene_write_user(_writer_bible(project["bible"]), project["taste"], context, state,
                                        steering, number, beat["title"], scenes, idx,
                                        scene_words, tail, voice_card=voice_card)
        async for chunk in oc.chat_stream(model, prompts.CHAPTER_SYSTEM, user, prose=True):
            written += chunk
            yield chunk


def record_feedback(project: dict, number: int, fb: dict) -> dict:
    """Store one feedback submission and evolve the project's learned taste.

    Returns the updated learned profile + the new steering note (for preview).
    """
    db.save_feedback(project["id"], number, fb)
    learned = learning.apply_feedback(project.get("learned"), fb)
    db.update_project(project["id"], learned=learned)
    return {
        "learned": learned,
        "steering": learning.steering_note(learned),
        "confidence": learning.confidence(learned),
    }


async def finalize_chapter(project: dict, number: int, content: str) -> dict:
    """Persist a finished chapter, then build its memory (summary, state ledger, arc/volume roll-ups).

    The chapter prose is saved FIRST and every memory step is **best-effort**: a slow or failed
    local-model call (common on a busy CPU) must never lose the chapter or 500 a write that already
    succeeded. Any step that fails is simply skipped — Repair can fill the gaps later.
    """
    beat = find_beat(project, number)
    model = project["model"]
    # 1) Save the prose immediately — this must never fail the user's chapter.
    db.save_chapter(project["id"], number, beat["title"], content.strip(), "")

    # 2) Summary + 3) story-state ledger. These two are independent, so on a CLOUD model we run them
    # concurrently to speed up auto-continue (P10). On LOCAL Ollama we keep them sequential — two
    # generations at once would thrash/OOM a small CPU. Both are best-effort: a slow/failed memory
    # step must never lose the prose or 500 a write that already succeeded.
    async def _do_summary():
        s = (await summarize_chapter(model, number, beat["title"], content)).strip()
        if s:
            db.save_chapter(project["id"], number, beat["title"], content.strip(), s)
        return s

    async def _do_state():
        await update_state(model, project, number, beat["title"], content)

    summary = ""
    if oc.cloud_active():
        res = await asyncio.gather(_do_summary(), _do_state(), return_exceptions=True)
        if not isinstance(res[0], Exception) and res[0]:
            summary = res[0]
    else:
        try:
            summary = await _do_summary()
        except Exception:
            pass
        try:
            await _do_state()
        except Exception:
            pass
    # 4) Arc, then (if a volume just ended) volume roll-up — best-effort, each isolated.
    try:
        await maybe_roll_up_arc(model, project, number)
    except Exception:
        pass
    try:
        fresh = db.get_project(project["id"]) or project
        await maybe_roll_up_volume(model, fresh, number)
    except Exception:
        pass
    db.update_project(project["id"], status="writing")
    return {"number": number, "title": beat["title"], "summary": summary}
