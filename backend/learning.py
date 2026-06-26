"""The learning / evolution model.

We don't retrain the AI. Instead we keep a structured 'learned taste' profile —
craft DIALS (sliders) + content LISTS — that updates from the reader's feedback and
is turned into a plain-English 'steering note' fed into future chapter prompts.

Evolution over time: each feedback nudges the dials, but the step size SHRINKS as more
feedback arrives (big turns first, fine-tuning later), with recent feedback weighted
slightly more. So the profile converges on the reader's real taste and then stays stable.
"""
from __future__ import annotations

# Craft dials. For each, "+1/+2" means MORE of the positively-named quality (range −2..+2).
DIALS = [
    "pacing", "vocabulary", "sentences", "reading_level",
    "description", "dialogue", "action", "romance", "emotion",
    # newer dials (added in the feedback redesign)
    "sensory", "tension", "humor", "spice", "monologue", "worldbuilding", "cliffhanger",
]

# (phrase when dial is high, phrase when dial is low)
_PHRASE = {
    "pacing":       ("a faster pace with more momentum", "a slower, calmer pace"),
    "vocabulary":   ("richer, more advanced vocabulary", "simpler, plainer vocabulary"),
    "sentences":    ("longer, more varied sentences", "shorter, punchier sentences"),
    "reading_level":("a higher, more sophisticated reading level", "an easier reading level"),
    "description":  ("more vivid description and scene-setting", "leaner description, less scenery"),
    "dialogue":     ("more dialogue", "less dialogue"),
    "action":       ("more action", "less action"),
    "romance":      ("more romance", "less romance"),
    "emotion":      ("more emotional depth", "less sentimentality"),
    "sensory":      ("more vivid sensory detail (sight, sound, smell, touch)", "less sensory detail"),
    "tension":      ("more tension and higher stakes", "a calmer, lower-tension feel"),
    "humor":        ("more humor and levity", "a more serious tone with less humor"),
    "spice":        ("more spice/heat in romantic scenes", "tamer, less explicit romance"),
    "monologue":    ("more of the protagonist's inner thoughts", "less inner monologue"),
    "worldbuilding":("more worldbuilding and lore", "less lore, a tighter focus"),
    "cliffhanger":  ("stronger chapter-ending hooks/cliffhangers", "gentler chapter endings"),
}

_TRIGGER = 0.5  # how far a dial must move before it shows up in the steering note


_CHAR_CAP = 12   # keep favorite/disliked character lists from growing without bound


def new_learned() -> dict:
    return {
        "dials": {d: 0.0 for d in DIALS},
        "loved_elements": {},        # element -> weight
        "want_more": {},             # element -> weight
        "want_less": {},             # element -> weight   (incl. "avoid", weighted strongly)
        "favorite_characters": [],
        "disliked_characters": [],
        "notes": [],                 # recent free-text "make it better" notes (most recent last)
        "clarity_issues": 0,         # times the reader found a chapter confusing
        "feedback_count": 0,
    }


def _ensure(learned: dict | None) -> dict:
    base = new_learned()
    if learned:
        base.update(learned)
    base.setdefault("dials", {})
    for d in DIALS:
        base["dials"].setdefault(d, 0.0)
    for key in ("loved_elements", "want_more", "want_less"):
        if not isinstance(base.get(key), dict):
            base[key] = {}
    for key in ("favorite_characters", "disliked_characters", "notes"):
        if not isinstance(base.get(key), list):
            base[key] = []
    if not isinstance(base.get("clarity_issues"), int):
        base["clarity_issues"] = 0
    return base


def _bump(counter: dict, items, weight: int = 1) -> None:
    if isinstance(items, str):
        items = [items]
    for it in items or []:
        it = str(it).strip()
        if it:
            counter[it] = counter.get(it, 0) + weight


def apply_feedback(learned: dict | None, fb: dict) -> dict:
    """Update the learned profile from one feedback submission.

    fb shape (all optional):
      {
        "craft": {"pacing": +2, "vocabulary": -1, ...},  # each the chosen value on the −2..+2 scale
        "loved": ["material fusion"],
        "want_more": ["crafting scenes"],
        "want_less": ["long travel"],
        "tags": ["crafting/fusion"],
        "favorite_character": "Kael",
        "overall": "loved" | "ok" | "not_it",
        "note": "free text"
      }
    """
    learned = _ensure(learned)
    n = int(learned.get("feedback_count", 0))
    step = max(0.25, 1.0 / (1.0 + 0.5 * n))  # shrinks as feedback accumulates

    # The UI sends, for each dial the reader TOUCHED, their chosen value on the −2..+2 scale
    # ("much less" … "just right" … "much more"). We EASE the dial toward that value by `step`
    # (big moves early, fine-tuning later). Easing — not a one-way nudge — means picking "just right"
    # (0) actually pulls a previously-pushed dial back toward neutral (P7). Dials the reader didn't
    # touch are absent from `craft` and left untouched.
    craft = fb.get("craft") or {}
    for d in DIALS:
        if d not in craft:
            continue
        try:
            target = max(-2.0, min(2.0, float(craft[d])))
        except (TypeError, ValueError):
            continue
        cur = learned["dials"][d]
        learned["dials"][d] = max(-2.0, min(2.0, cur + step * (target - cur)))

    # The overall reaction WEIGHTS the content signals (loved → reinforce, not-it → push away).
    # "good" is a recognized mild-positive (between loved and neutral), not silently dropped.
    overall = str(fb.get("overall") or "").lower()
    like_w = {"loved": 2, "good": 1}.get(overall, 1)
    dislike_w = {"not_it": 3, "meh": 2}.get(overall, 1)

    _bump(learned["loved_elements"], fb.get("loved", []), like_w)
    _bump(learned["want_more"], fb.get("want_more", []), like_w)
    _bump(learned["want_more"], fb.get("tags", []), 1)
    _bump(learned["want_less"], fb.get("want_less", []), dislike_w)
    # "avoid" = a strong "please don't do this" → weighted more than ordinary want_less.
    _bump(learned["want_less"], fb.get("avoid", []), dislike_w + 1)

    # favorite character(s): accept a single string and/or a list. Adding to one list removes from
    # the other (so a character can't be both loved and disliked), and the lists are capped.
    favs = fb.get("favorite_characters") or []
    if isinstance(favs, str):
        favs = [favs]
    single = str(fb.get("favorite_character", "") or "").strip()
    if single:
        favs = list(favs) + [single]
    for f in favs:
        f = str(f).strip()
        if f:
            if f in learned["disliked_characters"]:
                learned["disliked_characters"].remove(f)
            if f not in learned["favorite_characters"]:
                learned["favorite_characters"].append(f)
    learned["favorite_characters"] = learned["favorite_characters"][-_CHAR_CAP:]

    disliked = fb.get("disliked_characters") or []
    if isinstance(disliked, str):
        disliked = [disliked]
    for dc in disliked:
        dc = str(dc).strip()
        if dc:
            if dc in learned["favorite_characters"]:
                learned["favorite_characters"].remove(dc)
            if dc not in learned["disliked_characters"]:
                learned["disliked_characters"].append(dc)
    learned["disliked_characters"] = learned["disliked_characters"][-_CHAR_CAP:]

    # "Confusing" — keep the count AND the specifics, so the writer avoids those exact things.
    confusing = fb.get("confusing")
    conf_list = [confusing] if isinstance(confusing, str) else (confusing or [])
    conf_list = [str(c).strip() for c in conf_list if str(c).strip()]
    if conf_list:
        learned["clarity_issues"] = int(learned.get("clarity_issues", 0)) + 1
        _bump(learned["want_less"], conf_list, 1)

    # Free-text "one line to make it better" — previously discarded; keep the most recent few.
    note = str(fb.get("note", "") or "").strip()
    if note:
        notes = learned.setdefault("notes", [])
        notes.append(note)
        learned["notes"] = notes[-5:]

    learned["feedback_count"] = n + 1
    return learned


def _top(counter: dict, k: int = 4) -> list[str]:
    return [x for x, _ in sorted(counter.items(), key=lambda kv: -kv[1])[:k]]


def steering_note(learned: dict | None) -> str:
    """Turn the learned profile into plain instructions for the next chapter."""
    learned = _ensure(learned)
    parts: list[str] = []

    dials = learned["dials"]
    style_bits = []
    for d in DIALS:
        v = dials.get(d, 0.0)
        if v >= _TRIGGER:
            style_bits.append(_PHRASE[d][0])
        elif v <= -_TRIGGER:
            style_bits.append(_PHRASE[d][1])
    if style_bits:
        parts.append("Style: " + "; ".join(style_bits) + ".")

    more = list(dict.fromkeys(_top(learned["want_more"]) + _top(learned["loved_elements"])))[:5]
    if more:
        parts.append("Feature more of: " + ", ".join(more) + ".")
    less = _top(learned["want_less"])
    if less:
        parts.append("Reduce/avoid: " + ", ".join(less) + ".")
    favs = learned["favorite_characters"][:3]
    if favs:
        parts.append("Give strong moments to: " + ", ".join(favs) + ".")
    disliked = learned.get("disliked_characters", [])[:3]
    if disliked:
        parts.append("Reduce focus on: " + ", ".join(disliked) + ".")
    if int(learned.get("clarity_issues", 0)) > 0:
        parts.append("Keep events clear and easy to follow.")
    notes = learned.get("notes") or []
    if notes:
        parts.append("Reader's note: " + str(notes[-1]))

    return " ".join(parts)


def confidence(learned: dict | None) -> int:
    """A rough 0–100 'how well it knows you' score from feedback volume."""
    learned = _ensure(learned)
    n = int(learned.get("feedback_count", 0))
    return min(100, int(n * 10))  # ~10 feedbacks ≈ confident
