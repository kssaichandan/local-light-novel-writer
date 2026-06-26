"""Prompt templates for each stage of the pipeline.

Kept in one place so the "voice" of the whole app is easy to tune.
All prompts assume a light-novel sensibility (web-novel pacing, tropes, arcs).
"""
from __future__ import annotations

import json
from typing import Any

from . import config

# --------------------------------------------------------------------------- taste
TASTE_SYSTEM = (
    "You are a literary taste analyst specializing in light novels and web novels "
    "(Japanese/Korean/Chinese style). You turn a reader's raw preferences into a "
    "clean, structured taste profile that a writer can follow."
)

# --------------------------------------------------------------------------- external interview (Idea 1b)
# A self-contained prompt the user copies into a big LLM (ChatGPT/Claude). That LLM
# interviews them, then outputs a taste profile in OUR schema, which they paste back.
EXTERNAL_INTERVIEW_PROMPT = (
    "# ROLE\n"
    "You are an expert interviewer who specializes in light novels and web novels "
    "(Japanese/Korean/Chinese style: isekai, cultivation, litRPG, villainess, etc.). Your goal is "
    "to deeply understand MY personal taste so a separate writing program can generate a long "
    "novel I'll love. You will INTERVIEW me, then output a structured taste profile.\n\n"
    "# HOW TO INTERVIEW ME\n"
    "1. Ask ONE question at a time and WAIT for my answer before the next. Keep it friendly and short.\n"
    "2. For every question, offer a few concrete example options in brackets so I can answer fast, "
    "but make clear I can say anything.\n"
    "3. If an answer is vague, ask ONE quick follow-up to get specifics. Don't over-interrogate.\n"
    "4. Cover ALL of these topics (about 15–18 questions total) — one question each:\n"
    "   • Favorite genres / sub-genres  [isekai, dark fantasy, cultivation, litRPG, romance, mystery…]\n"
    "   • Overall tone & mood  [lighthearted, grimdark, bittersweet, cozy, epic…]\n"
    "   • Tropes I LOVE  [overpowered MC, weak-to-strong, slow-burn romance, found family, regression…]\n"
    "   • Tropes I HATE / dealbreakers  [harem, dense MC, plot armor, NTR, info-dumps…]\n"
    "   • The protagonist / MC type I enjoy  [clever underdog, calm strategist, anti-hero, cunning villainess…]\n"
    "   • Pacing  [slow burn, medium, fast / action-packed]\n"
    "   • Romance / heat level  [none, mild romance, spicy]\n"
    "   • Narration point of view  [1st person, 3rd person]\n"
    "   • Setting / world  [cultivation world, modern day, magic academy, sci-fi, post-apocalyptic…]\n"
    "   • Power / progression system  [litRPG stats, cultivation realms, mana/magic, classes & skills, none…]\n"
    "   • Antagonist type  [clear-evil villain, morally-gray rival, the system itself, demon lord, corrupt empire…]\n"
    "   • Ending preference  [happy, bittersweet, tragic, open-ended, triumphant]\n"
    "   • Humor level  [lots of comedy, some humor, mostly serious, none]\n"
    "   • Conflict scale  [personal, group / guild, kingdom / political, world-ending]\n"
    "   • Prose style & vibe  [punchy & modern, descriptive & literary, witty, dark…]\n"
    "   • Themes I'm drawn to  [revenge, redemption, power & corruption, friendship, survival…]\n"
    "   • Content limits / anything to avoid  [graphic violence, certain topics…]\n"
    "   • Comparable titles I love (optional — for vibe reference)\n\n"
    "# OUTPUT (VERY IMPORTANT)\n"
    "When you have enough, write the line 'Here is your taste profile:' and then output ONLY a "
    "single JSON object inside a ```json code block — no commentary inside the block. Use EXACTLY "
    "these keys:\n"
    "```json\n"
    "{\n"
    '  "genres": ["..."],\n'
    '  "tone": "...",\n'
    '  "favorite_tropes": ["..."],\n'
    '  "disliked_tropes": ["..."],\n'
    '  "protagonist_type": "...",\n'
    '  "pacing": "slow burn | medium | fast / action-packed",\n'
    '  "heat_level": "none | mild romance | spicy",\n'
    '  "pov": "1st person | 3rd person",\n'
    '  "setting": "world/setting (e.g. cultivation world, modern day, sci-fi)",\n'
    '  "themes": ["core themes"],\n'
    '  "power_system": "powers/progression (e.g. litRPG stats, magic, none)",\n'
    '  "antagonist": "the kind of antagonist they like",\n'
    '  "ending": "happy | bittersweet | tragic | open | triumphant",\n'
    '  "humor": "lots | some | mostly serious | none",\n'
    '  "conflict_scale": "personal | group | kingdom/political | world-ending",\n'
    '  "content_limits": "anything to avoid, or none",\n'
    '  "style_notes": "prose style & vibe, in 1–3 sentences",\n'
    '  "inspirations": ["comparable titles, if I named any"]\n'
    "}\n"
    "```\n"
    "Fill EVERY field from my answers (infer sensibly if I skip one). Output must be valid JSON.\n\n"
    "# START\n"
    "Greet me warmly, explain in one line that you'll ask a few quick questions about my taste, "
    "then ask your FIRST question."
)


def taste_user(raw_inputs: dict[str, Any]) -> str:
    return (
        "Below is everything a reader told us about their taste in light novels. "
        "It may come from a questionnaire, free text, or sample ratings.\n\n"
        f"RAW INPUT:\n{json.dumps(raw_inputs, ensure_ascii=False, indent=2)}\n\n"
        "Produce a JSON taste profile with EXACTLY these keys:\n"
        "{\n"
        '  "genres": [list of preferred genres],\n'
        '  "tone": "overall tone (e.g. lighthearted, dark, bittersweet)",\n'
        '  "favorite_tropes": [tropes they enjoy],\n'
        '  "disliked_tropes": [tropes/things to avoid],\n'
        '  "protagonist_type": "the kind of MC they like",\n'
        '  "pacing": "slow burn | medium | fast / action-packed",\n'
        '  "heat_level": "none | mild romance | spicy",\n'
        '  "pov": "1st person | 3rd person",\n'
        '  "setting": "world/setting they want (e.g. cultivation world, modern day)",\n'
        '  "themes": [core themes they care about],\n'
        '  "power_system": "kind of powers/progression (e.g. litRPG stats, magic, none)",\n'
        '  "antagonist": "the kind of antagonist they like",\n'
        '  "ending": "preferred ending feel (happy | bittersweet | tragic | open | triumphant)",\n'
        '  "humor": "how much comedy (lots | some | mostly serious | none)",\n'
        '  "conflict_scale": "stakes (personal | group | kingdom/political | world-ending)",\n'
        '  "content_limits": "anything to avoid (or \\"none\\")",\n'
        '  "style_notes": "prose style, narration quirks, anything notable",\n'
        '  "inspirations": [comparable titles they mentioned]\n'
        "}\n"
        "Fill every field. Infer sensibly when something is missing. Output JSON only."
    )

# --------------------------------------------------------------------------- bible
BIBLE_SYSTEM = (
    "You are a master light-novel author and worldbuilder. You create a 'story bible': "
    "the single source of truth that keeps a long series consistent across hundreds of chapters."
)

def bible_user(taste: dict, premise_hint: str, target_chapters: int) -> str:
    hint = premise_hint.strip() or "(no specific premise — invent something fitting their taste)"
    return (
        f"Reader taste profile:\n{json.dumps(taste, ensure_ascii=False, indent=2)}\n\n"
        f"Optional premise idea from the reader: {hint}\n\n"
        f"This series will run about {target_chapters} chapters, so it needs room to grow.\n\n"
        "Keep this a LEAN core bible — the high-level foundation only (per-arc details come later). "
        "Include 3–5 main characters and a premise of 1–2 short paragraphs.\n"
        "Create a story bible as JSON with EXACTLY these keys:\n"
        "{\n"
        '  "title": "catchy light-novel title",\n'
        '  "logline": "one sentence hook",\n'
        '  "premise": "2-3 paragraph setup",\n'
        '  "world": "the setting, rules, magic/power system, factions",\n'
        '  "themes": [core themes],\n'
        '  "characters": [\n'
        '    {"name": "", "role": "protagonist/rival/love interest/etc",\n'
        '     "description": "", "goal": "", "arc": "how they change"}\n'
        "  ],\n"
        '  "power_system": "rules of any abilities/progression (or \\"none\\")",\n'
        '  "central_conflict": "the long-running conflict driving the whole series",\n'
        '  "endgame": "where the series is ultimately heading (so it never rambles)"\n'
        "}\n"
        "Make it match the reader's taste closely. Include at least 4 characters. Output JSON only."
    )

# --------------------------------------------------------------------------- full plan hand-off (Idea 1b+)
def full_plan_prompt(num_chapters: int, per_arc: int) -> str:
    """A copy-paste prompt for a big external LLM to produce the ENTIRE plan (bible + volumes +
    arcs + every chapter beat) in our exact JSON, so the local model can write from chapter 1."""
    import math
    num_arcs = max(1, math.ceil(num_chapters / max(1, per_arc)))
    num_volumes = min(max(1, round(num_arcs / 5)), 8) if num_arcs >= 2 else 1
    return (
        "# ROLE\n"
        "You are a master light-novel architect. Plan a COMPLETE novel for me and output it as one "
        "JSON object I can paste into my local writing app.\n\n"
        "# FIRST, ASK ME ABOUT MY TASTE\n"
        "Before planning, ask me about EACH of these (one quick question at a time, with a few "
        "bracketed examples; skip any I've already told you, and infer sensibly if I pass):\n"
        "   • Favorite genres / sub-genres   • Overall tone & mood   • Tropes I LOVE   • Tropes I HATE\n"
        "   • MC / protagonist type   • Pacing   • Romance / heat level   • Point of view\n"
        "   • Setting / world   • Power / progression system   • Antagonist type   • Ending preference\n"
        "   • Humor level   • Conflict scale   • Themes   • Anything to avoid\n"
        "Then weave my answers into the bible, characters, conflict and endgame below.\n\n"
        f"# SIZE\n{num_chapters} chapters total, grouped into {num_arcs} arcs of ~{per_arc} chapters, "
        f"and {num_volumes} volumes. Number chapters 1..{num_chapters} with no gaps.\n\n"
        "# OUTPUT — one JSON object inside a ```json block, EXACTLY these keys:\n"
        "```json\n"
        "{\n"
        '  "bible": {\n'
        '    "title": "", "logline": "", "premise": "", "world": "", "themes": [],\n'
        '    "characters": [ {"name":"","role":"","description":"","goal":"","arc":""} ],\n'
        '    "power_system": "", "central_conflict": "", "endgame": ""\n'
        "  },\n"
        '  "volume_map": [ {"number":1,"title":"","theme":"","arc_start":1,"arc_end":3} ],\n'
        '  "arc_map": [ {"number":1,"title":"","goal":""} ],\n'
        '  "outline": [ {"number":1,"title":"","beat":"a concrete scene: where, who, the specific '
        'event that happens, and what changes","arc":1} ]\n'
        "}\n"
        "```\n"
        f"RULES: 'arc_map' has exactly {num_arcs} arcs; 'outline' has exactly {num_chapters} chapters "
        "numbered in order, each tagged with its arc; volumes cover all arcs with no gaps; everything "
        "builds to the bible's endgame. EACH BEAT must be a concrete, writable scene (a specific "
        "place, named characters, a real event, and what changes) — never a vague summary like 'the "
        "hero grows stronger'. Output ONLY the JSON in the code block — no extra text."
    )

# --------------------------------------------------------------------------- volume map (layer 0)
VOLUME_MAP_SYSTEM = (
    "You are a long-series architect. You divide a whole novel into a few big VOLUMES (like the "
    "books of a long series). Each volume is a major movement of the story with its own theme, "
    "spanning a range of arcs, and together they build to the ending. Big picture only."
)

def volume_map_user(bible: dict, taste: dict, num_volumes: int, num_arcs: int) -> str:
    return (
        f"CORE STORY BIBLE:\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"The series has {num_arcs} arcs total. Group them into exactly {num_volumes} VOLUMES, in "
        "order, each covering a contiguous range of arcs and ending at a major turning point; the "
        "last volume reaches the endgame.\n\n"
        "Output JSON EXACTLY:\n"
        "{\n"
        '  "volumes": [\n'
        '    {"number": 1, "title": "", "theme": "1-2 sentences",'
        ' "arc_start": 1, "arc_end": 3}\n'
        "  ]\n"
        "}\n"
        f"Exactly {num_volumes} volumes, numbered 1..{num_volumes}, covering arcs 1..{num_arcs} with "
        "no gaps or overlaps. Output JSON only."
    )

# --------------------------------------------------------------------------- arc map (layer 1)
ARC_MAP_SYSTEM = (
    "You are a light-novel series architect. You design the high-level SHAPE of a whole long "
    "series as a sequence of arcs, each a major story phase that escalates toward the ending. "
    "You think big-picture only — no chapter detail — so the whole journey is coherent and "
    "clearly builds to the endgame."
)

def arc_map_user(bible: dict, taste: dict, num_arcs: int, chapters_per_arc: int,
                 volume_map: list[dict] | None = None) -> str:
    vol_block = ""
    if volume_map:
        lines = "\n".join(
            f"- Volume {v.get('number')}: {v.get('title','')} (arcs {v.get('arc_start')}–"
            f"{v.get('arc_end')}) — {v.get('theme','')}" for v in volume_map
        )
        vol_block = f"VOLUME PLAN (each arc must fit its volume's theme):\n{lines}\n\n"
    return (
        f"CORE STORY BIBLE:\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"READER TASTE:\n{json.dumps(taste, ensure_ascii=False, indent=2)}\n\n"
        f"{vol_block}"
        f"Design the whole series as exactly {num_arcs} arcs (~{chapters_per_arc} chapters each). "
        "Each arc is a major phase that raises the stakes and moves clearly toward the bible's "
        "endgame; the final arc resolves it. Avoid repetition — each arc brings a new threat, "
        "place, or revelation.\n\n"
        "Output JSON EXACTLY:\n"
        "{\n"
        '  "arcs": [\n'
        '    {"number": 1, "title": "", "goal": "1-2 sentences: this arc\'s purpose and how it '
        'advances toward the endgame"}\n'
        "  ]\n"
        "}\n"
        f"The \"arcs\" list MUST contain exactly {num_arcs} entries, numbered 1 through {num_arcs}, "
        "in order. Output JSON only."
    )

# --------------------------------------------------------------------------- outline (layer 2)
OUTLINE_SYSTEM = (
    "You are a light-novel series planner. You expand ONE arc of an existing plan into per-chapter "
    "beats. Each arc has a clear conflict, escalation, climax, and payoff, so the story never "
    "stalls or repeats itself even across hundreds of chapters."
)

def outline_arc_user(bible: dict, taste: dict, arc_number: int, start_ch: int, end_ch: int,
                     prev_arc_summaries: list[str], arc_goal: str = "") -> str:
    prev = "\n".join(f"- Arc {i+1}: {s}" for i, s in enumerate(prev_arc_summaries)) or "(this is the first arc)"
    n = end_ch - start_ch + 1
    goal_line = f"THIS ARC'S GOAL (from the master plan):\n{arc_goal}\n\n" if arc_goal else ""
    return (
        f"STORY BIBLE:\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"READER TASTE:\n{json.dumps(taste, ensure_ascii=False, indent=2)}\n\n"
        f"PREVIOUS ARCS:\n{prev}\n\n"
        f"{goal_line}"
        f"Expand ARC {arc_number}, covering chapters {start_ch} to {end_ch} ({n} chapters), so it "
        "delivers the arc goal above, advances the central conflict toward the endgame, and "
        "introduces fresh stakes.\n\n"
        "EACH BEAT MUST BE A CONCRETE, WRITABLE SCENE — not a vague summary. A good beat names:\n"
        "  • WHERE it happens (a specific place),\n"
        "  • WHO is in it (named characters),\n"
        "  • the SPECIFIC EVENT that occurs (a confrontation, a discovery, a deal, a betrayal — "
        "something that actually happens), and\n"
        "  • what CHANGES by the end (a decision, a reveal, a shift in power or relationship).\n"
        "Bad beat: 'The MC continues his cultivation and grows stronger.' "
        "Good beat: 'In the sect's frozen archive, Veylin tricks the elder Ku Sho into revealing "
        "the array's flaw, then steals the jade slip while a rival watches from the shadows.'\n"
        "Avoid beats that just restate the theme or the MC's nature. Each chapter must do something "
        "NEW that the others don't.\n\n"
        "Output JSON EXACTLY:\n"
        "{\n"
        '  "arc_title": "",\n'
        '  "arc_goal": "what this arc accomplishes in the bigger story",\n'
        '  "new_characters": [\n'
        '    {"name": "", "role": "", "description": ""}  (characters/places first introduced in '
        'this arc; [] if none)\n'
        "  ],\n"
        '  "chapters": [\n'
        f'    {{"number": {start_ch}, "title": "", "beat": "a concrete scene: where, who, what '
        'specific event happens, and what changes"}}\n'
        "  ]\n"
        "}\n"
        f"The \"chapters\" list MUST contain exactly {n} entries, numbered {start_ch} through {end_ch}, "
        "in order. Output JSON only."
    )

# --------------------------------------------------------------------------- primer (Chapter 0)
PRIMER_SYSTEM = (
    "You write a short, reader-facing PRIMER (a 'Chapter 0') that orients a new reader before "
    "Chapter 1. It is SPOILER-FREE: only the starting setup — never plot twists, later events, or "
    "the ending. Crucially, include ONLY what matters for THIS specific story; do NOT use a fixed "
    "template. Choose the sections that fit the genre — e.g. for a cultivation/xianxia story, the "
    "power realms/levels, key sects and regions, and important terms; for sci-fi, the tech and "
    "factions; for a mystery, the setting and key players. Skip anything not relevant. Keep it "
    "concise and skimmable."
)

def primer_user(bible: dict) -> str:
    return (
        f"STORY BIBLE:\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        "Write the Chapter 0 primer in clean plain text (you may use short ALL-CAPS or bold "
        "headings and simple bullet lists). Cover, in this order, ONLY what's relevant:\n"
        "- The novel's title and a 1-2 sentence hook.\n"
        "- The world in brief (the setting the reader is dropped into).\n"
        "- The main character (1-2 lines) and any key characters the reader meets early.\n"
        "- Genre essentials the reader needs — e.g. for cultivation: the realms/power levels in "
        "order, major sects/regions, and a short glossary of key terms; choose the equivalent for "
        "other genres.\n"
        "Rules: SPOILER-FREE (no plot reveals, no ending). Tailor the sections to THIS story — omit "
        "any that don't apply. Aim for roughly 250-500 words. Output only the primer text."
    )

# --------------------------------------------------------------------------- plan sharpener
# Run automatically right before a chapter is written: turn a flat, low-stakes chapter plan into a
# concrete scene with real conflict, consistent with the story so far. (Plain term in the UI: it
# makes "what happens in the chapter" more exciting before writing.)
SHARPEN_PLAN_SYSTEM = (
    "You are a sharp story editor for a long, addictive web novel of ANY genre. You take a flat or "
    "generic chapter plan and rewrite it into a vivid, specific scene with REAL tension and stakes "
    "— while staying perfectly consistent with the story so far. 'Tension' does NOT mean a fight: "
    "it means whatever kind of pressure fits THIS story — emotional, romantic, social, mysterious, "
    "moral, political, or physical. You match the tension to the genre and tone. You output ONLY "
    "the rewritten plan (a few sentences), no commentary, no title, no notes."
)


def sharpen_plan_user(bible: dict, taste: dict, arc_goal: str, context: str, state: str,
                      number: int, title: str, plan: str, role: str = "") -> str:
    arc_line = f"THIS PART OF THE STORY IS HEADING TOWARD:\n{arc_goal}\n\n" if arc_goal else ""
    role_line = ""
    if role and role in ROLE_GUIDANCE:
        role_line = (f"THE CHAPTER'S ROLE IN ITS ARC — match the LEVEL of tension to this "
                     f"(a breather stays small and personal; a climax goes big):\n"
                     f"{ROLE_GUIDANCE[role]}\n\n")
    state_block = f"CANONICAL FACTS (do not contradict):\n{state}\n\n" if state else ""
    so_far = context.strip() or "(this is the very first chapter)"
    genre_block = ""
    if taste:
        slim = {k: taste.get(k) for k in ("genres", "tone", "pacing", "heat_level", "humor",
                                          "conflict_scale", "themes") if taste.get(k)}
        if slim:
            genre_block = (
                "GENRE & TONE (match the KIND of tension to this):\n"
                f"{json.dumps(slim, ensure_ascii=False)}\n\n"
            )
    return (
        f"STORY BIBLE (stay consistent):\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"{genre_block}"
        f"{state_block}"
        f"STORY SO FAR:\n{so_far}\n\n"
        f"{arc_line}"
        f"{role_line}"
        f"CHAPTER {number} (\"{title}\") — current plan:\n{plan}\n\n"
        + ("EARLY-CHAPTER NOTE: this is one of the very first chapters, which must HOOK a brand-new "
           "reader. Keep the tension smaller and more personal (a threat, an unsettling encounter, a "
           "hard choice) and leave room to establish the character and world — do NOT cram a big "
           "battle or a pile of events into the opening.\n\n" if number <= 2 else
           "VARY IT: make this chapter's central event clearly DIFFERENT from the previous chapter's "
           "— do not repeat the same kind of scene (e.g. another back-alley fight) two chapters in a "
           "row.\n\n")
        + "Rewrite this into a sharper plan for THIS ONE chapter that:\n"
        "• centers on a CONCRETE source of tension that FITS THE GENRE — not a calm lesson or an "
        "effortless success. Choose the right kind for this story, e.g.:\n"
        "   – romance: a risky confession, jealousy, a secret, a forced choice between two people;\n"
        "   – mystery/thriller: a clue, a lie exposed, a wrong suspect, a trap, a deadline;\n"
        "   – cozy / slice-of-life: a personal or social dilemma, a misunderstanding, a small but "
        "real stake that matters to the characters;\n"
        "   – drama/politics: a betrayal, a power play, a moral compromise, a reputation at risk;\n"
        "   – action/adventure/cultivation: a clash, a threat, a rival, a dangerous gamble;\n"
        "  Do NOT force physical violence where it doesn't belong.\n"
        "• makes the protagonist RISK something, lose something, pay a price, or face a real "
        "complication (no easy wins);\n"
        "• uses specific named characters and a specific place;\n"
        "• moves toward where this part of the story is heading and never contradicts the story so "
        "far — but does NOT resolve the whole storyline, just this chapter;\n"
        "• ends on a turn or a hook into the next chapter.\n"
        "Keep it 2–4 sentences, concrete and writable. Output ONLY the rewritten plan."
    )

# --------------------------------------------------------------------------- style examples (few-shot)
# A small local model imitates a concrete EXAMPLE far better than it follows abstract craft rules.
# So we show it ONE short, genre-matched passage of strong prose as a quality bar — explicitly
# style-only (never its content) — to demonstrate the craft the long CHAPTER_SYSTEM brief asks for:
# concrete sensory detail, real dialogue, feeling shown through action/gesture (not stated), varied
# sentence rhythm, and zero clichés. Each passage is original and deliberately written to that bar.
# Placed EARLY in the prompt (after the taste block) on purpose: it stays out of the last ~256-token
# window the prose repetition penalty looks at, so it never suppresses words the model needs.
_STYLE_EXAMPLES: dict[str, str] = {
    "general": (
        "The kettle clicked off, and for a moment Mara didn't move to pour it. Steam curled against "
        "the window where the rain had started — fat, slow drops that slid and caught the streetlight.\n"
        "\"You're doing the thing again,\" Dev said from the doorway.\n"
        "\"What thing.\"\n"
        "\"Where you stand very still and pretend the kettle needs supervising.\"\n"
        "She poured. The water shook, just slightly, and she set the kettle down before he could "
        "notice. \"It's been a long day.\"\n"
        "\"It's been a long year.\" He took the second mug down from the shelf without asking, the way "
        "he had a thousand times, and that small ordinary certainty was almost worse than if he'd "
        "said something kind."
    ),
    "action": (
        "The first arrow missed because Corin tripped. Pure luck — his boot caught a root and the "
        "shaft went over his shoulder close enough to hum.\n"
        "He didn't get up. He rolled, came up behind the oak with bark stinging his cheek, and made "
        "himself breathe. Two of them, maybe three. The crunch of boots on frozen leaves told him "
        "more than his eyes could.\n"
        "\"Come out, boy. You're making this harder than it needs to be.\"\n"
        "Corin looked at the knife in his hand. A kitchen knife. He'd grabbed it off the table like "
        "it would matter, and the laughter in that voice said the man knew it too.\n"
        "So he threw it — not at the voice, but at the lantern. Glass broke, the light died, and in "
        "the dark they were all blind together."
    ),
    "progression": (
        "The technique wanted to be fast. Too fast — Jin felt it pull at the meridians in his "
        "forearm like a dog at a leash, and he knew if he let it run it would burn them out the way "
        "it had burned the boy before him.\n"
        "So he held it back. Half-speed. The spear of light that left his palm was thinner than the "
        "manual promised and it cost him a tooth's worth of pain behind the eyes, but it punched "
        "through the straw target and kept going, and that was the point.\n"
        "Across the yard, Elder Su stopped pretending to read.\n"
        "\"Again,\" she said. \"Slower. I want to see you afraid of it.\"\n"
        "Jin's arm was shaking. He raised it anyway."
    ),
    "romance": (
        "He returned her umbrella three days later than he needed to.\n"
        "\"It stopped raining on Tuesday,\" Priya said, not taking it yet.\n"
        "\"I know.\" Arjun turned the handle in his hands. \"I kept meaning to bring it by.\"\n"
        "\"On Tuesday.\"\n"
        "\"On Tuesday,\" he agreed, and didn't explain, and the not-explaining sat between them louder "
        "than anything he could have said.\n"
        "She took the umbrella. Their fingers didn't touch — she made sure of that, a small "
        "deliberate inch — and she hated how much the inch cost her.\n"
        "\"Thank you,\" she said, \"for keeping it dry,\" and shut the door before her face could do "
        "something she hadn't agreed to."
    ),
    "mystery": (
        "The widow had washed the cups. That was the first thing wrong.\n"
        "Two days since her husband dropped dead at his own table and the house still smelled of "
        "bleach, and there she sat, hands folded, telling Inspector Bode how she'd found him.\n"
        "\"He took his tea at four,\" she said. \"Like always.\"\n"
        "\"And you were upstairs.\"\n"
        "\"Sewing.\" She smiled the way people smile when they've practiced it.\n"
        "Bode wrote nothing down. He'd noticed the cabinet behind her — eleven cups on their hooks, "
        "the twelfth hook empty, and not a chip on any of them. A woman who broke one cup and kept "
        "eleven perfect did not leave the broken one unswept for two days unless she needed him to "
        "picture it breaking.\n"
        "\"Show me where you sew,\" he said."
    ),
    "cozy": (
        "The bread hadn't risen. Again.\n"
        "Toma stared at the sad flat disc of it and considered, briefly, lying to the old man — but "
        "Mr. Haru was already shuffling over with his cane and his terrible eyesight and his "
        "unfailing nose.\n"
        "\"Ah,\" he said. \"You forgot the salt.\"\n"
        "\"I didn't forget the salt.\"\n"
        "\"You forgot to be patient with the salt.\" He broke off a corner, chewed it slowly, and "
        "nodded as though she'd done something remarkable. \"Dense. Good for soup. We'll call it soup "
        "bread and charge more.\"\n"
        "Toma laughed before she could stop herself. Outside, the first customers were stamping snow "
        "off their boots, and the shop smelled of yeast and woodsmoke and the burnt edge of her "
        "second attempt."
    ),
    "dark": (
        "They buried the miller in the morning and dug him up by lunch, because the ground gave him "
        "back.\n"
        "Not whole. The frost had its teeth in everything that winter, and what came up was less a "
        "man than an argument the earth was having with itself. Wend looked at it for a long time. "
        "Somebody had to, and the priest had run.\n"
        "\"That's not him,\" the miller's daughter said. \"That's not my father.\"\n"
        "\"No,\" Wend agreed. It was kinder than the truth, which was that it had been. He took the "
        "spade from her hands gently, the way you take a knife from a child. \"Go inside, Sera. Put "
        "the kettle on. This is work for someone who didn't love him.\""
    ),
    "scifi": (
        "The airlock wouldn't cycle until someone confirmed the body count, and the body count was "
        "the problem.\n"
        "\"Six,\" Okonkwo said.\n"
        "\"Manifest says seven.\" The station's voice was patient, female, built in some lab to be "
        "soothing and instead deeply not. \"Please confirm seven crew present for depressurization.\"\n"
        "\"There are six of us. Vahn didn't make it back.\"\n"
        "\"Please confirm seven crew.\"\n"
        "Okonkwo put her glove flat against the cold inner door and felt the pumps shiver on the "
        "other side. Somewhere in the station's small electronic mind, Vahn was still alive, still "
        "listed, still owed an airlock.\n"
        "\"Confirmed,\" she lied. \"Seven. Cycle it.\""
    ),
    "comedy": (
        "Kesh had prepared a speech. It was a good speech. It had a beginning, a middle, and a part "
        "where the dragon realized the error of its ways and possibly wept.\n"
        "\"No,\" said the dragon.\n"
        "\"You haven't heard the —\"\n"
        "\"I heard the beginning. The beginning was about my 'wasted potential.' My mother used that "
        "exact phrase. I ate a knight over it.\" The dragon settled its chin on one enormous claw. "
        "\"Go on, though. I'm working on my listening.\"\n"
        "Kesh looked at his notes. He looked at the very small sword he had brought, which had seemed "
        "brave in the village and now seemed mostly like a topic of conversation.\n"
        "\"...The middle's quite good,\" he tried."
    ),
}

# Which example fits a taste profile: score each by keyword hits in the taste text, pick the best.
_STYLE_TRIGGERS: list[tuple[str, tuple[str, ...]]] = [
    ("romance",     ("romance", "romantic", "love interest", "villainess", "otome", "shoujo",
                     "josei", "harem", "slow burn", "slow-burn")),
    ("progression", ("cultivation", "xianxia", "wuxia", "murim", "cultivat", "sect", "qi ", "litrpg",
                     "lit-rpg", "dungeon", "system", "progression", "leveling", "levelling", "stats")),
    ("mystery",     ("mystery", "thriller", "detective", "crime", "noir", "suspense", "whodunit",
                     "investigat")),
    ("cozy",        ("cozy", "cosy", "slice of life", "slice-of-life", "healing", "wholesome",
                     "iyashikei", "comfort", "heartwarming")),
    ("comedy",      ("comedy", "comedic", "humor", "humour", "parody", "satire", "gag", "funny",
                     "rom-com", "romcom")),
    ("dark",        ("grimdark", "horror", "gothic", "tragedy", "tragic", "grim", "dark fantasy",
                     "bleak", "brutal", "macabre")),
    ("scifi",       ("sci-fi", "scifi", "science fiction", "space opera", "cyberpunk", "mecha",
                     "futuristic", "dystopia", "post-apocalyptic", "spaceship", "starship")),
    ("action",      ("action", "adventure", "battle", "shounen", "shonen", "war", "martial",
                     "fight", "epic fantasy", "isekai", "quest")),
]


def _pick_style_key(taste: dict | None) -> str:
    """Choose the best-fitting style example for this novel from its taste profile."""
    if not isinstance(taste, dict):
        return "general"
    fields = []
    for k in ("genres", "tone", "setting", "themes", "style_notes", "protagonist_type",
              "inspirations", "antagonist", "power_system"):
        v = taste.get(k)
        if isinstance(v, list):
            fields.extend(str(x) for x in v)
        elif v:
            fields.append(str(v))
    text = " " + " ".join(fields).lower() + " "
    best, best_score = "general", 0
    for key, kws in _STYLE_TRIGGERS:
        score = sum(1 for kw in kws if kw in text)
        if score > best_score:
            best, best_score = key, score
    return best


def style_example_block(taste: dict | None) -> str:
    """A framed, style-only example passage for the prose writer (empty if disabled)."""
    if not config.STYLE_EXAMPLE_ON:
        return ""
    example = _STYLE_EXAMPLES.get(_pick_style_key(taste), _STYLE_EXAMPLES["general"])
    return (
        "\nSTYLE EXAMPLE — match the CRAFT, not the content. The passage below is NOT part of your "
        "story (different characters, plot, and possibly POV/tense). Study HOW it is written — "
        "concrete sensory detail, real dialogue, emotion shown through action and gesture instead of "
        "named, varied sentence rhythm, no clichés — and write your chapter to that same standard, "
        "in YOUR story's own POV, tense, and voice. Do NOT borrow its words, names, or events:\n"
        "- - - - -\n"
        f"{example}\n"
        "- - - - -\n"
    )


# --------------------------------------------------------------------------- voice card
# One compact, per-novel "how this book sounds" spec, generated once (lazily, at the first chapter
# write) and injected into every chapter + the editor pass. This is what makes a cozy romance and a
# grimdark cultivation novel stop sharing DNA. Best-effort: if generation fails, chapters simply
# write without it, exactly as before.
VOICE_CARD_SYSTEM = (
    "You define the narrative VOICE of one specific novel — a compact spec a writer follows so "
    "every chapter sounds like the same author wrote it. You output only the card, no commentary."
)


def voice_card_user(bible: dict, taste: dict) -> str:
    return (
        f"STORY BIBLE:\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"READER TASTE:\n{json.dumps(taste, ensure_ascii=False, indent=2)}\n\n"
        "Write this novel's VOICE CARD as plain text with EXACTLY these labeled lines (keep the "
        "whole card under ~150 words):\n"
        "NARRATOR: point of view, tense, and how close the narration sits to the protagonist\n"
        "SENTENCES: typical rhythm and length mix\n"
        "DICTION: the word palette (plain/ornate, modern/archaic, what imagery it leans on)\n"
        "HUMOR: how much, and what kind\n"
        "DIALOGUE: one speech habit each for 2-3 main characters (name: habit)\n"
        "NEVER: 2-3 things this narrator never does\n"
        "SAMPLE: a 60-90 word passage in EXACTLY this voice — a generic quiet moment, no plot, "
        "no character names from the bible\n"
        "Output only the card."
    )


def voice_card_block(voice_card: str) -> str:
    if not (voice_card or "").strip():
        return ""
    return (
        "\nVOICE CARD — this novel's sound. Every paragraph you write must sound like THIS "
        f"author:\n{voice_card.strip()}\n"
    )


# --------------------------------------------------------------------------- chapter roles
# A deterministic "tension curve": each chapter gets a role from its position in the arc, so the
# book stops being uniformly loud (every chapter max tension + cliffhanger = its own AI tell).
ROLE_GUIDANCE: dict[str, str] = {
    "setup": ("This is the arc's OPENING chapter: establish the arc's new situation, place, or "
              "goal. Tension should simmer rather than explode — plant the threat, don't spend it."),
    "rising": ("This is a RISING chapter: complicate things. Progress must cost something, and "
               "the pressure should be one notch higher than the previous chapter."),
    "breather": ("This is a BREATHER chapter: let the story exhale. Slow down, deepen a "
                 "relationship or the world, let characters be people (a meal, a repair, a joke, "
                 "a confession). Small personal stakes only — NO new catastrophe. Quiet does not "
                 "mean boring: tension lives in what's unsaid."),
    "turn": ("This is the TURN chapter: something believed true breaks — a betrayal, a reveal, a "
             "plan failing. The arc's direction should feel changed by the end."),
    "climax": ("This is the arc's CLIMAX chapter: the payoff the whole arc built toward. Highest "
               "stakes, a real cost paid, a decisive change. Give it room — this is the chapter "
               "that earns everything around it."),
}
# How the chapter should END, by role (a breather must not be forced into a cliffhanger).
ROLE_ENDING: dict[str, str] = {
    "breather": ("END ON A RESONANT NOTE: close on a quiet image, a line that lingers, or a soft "
                 "question — warmth with a thread of unease is perfect. No cliffhanger needed."),
    "climax": ("END ON THE AFTERMATH'S EDGE: the dust settles just enough to feel the cost, then "
               "close on the question or consequence that opens the next arc."),
}
_DEFAULT_ENDING = (
    "END ON A HOOK: close on a turn, a question, a threat, or a reveal that makes stopping "
    "here feel impossible — never a tidy wrap-up or a calm 'and so his journey continued'."
)


# --------------------------------------------------------------------------- chapter
CHAPTER_SYSTEM = (
    "You are an acclaimed novelist writing one chapter of a long web novel. You write "
    "IMMERSIVE SCENES, not summaries. You stay perfectly consistent with the story bible and "
    "everything that has happened, and you write ONLY the requested chapter — no meta "
    "commentary, no notes.\n\n"
    "HOW YOU WRITE (this is what separates real prose from AI filler):\n"
    "1. DRAMATIZE, never narrate-in-the-abstract. Put the reader inside a specific moment: a "
    "place, a time, things happening NOW. Show events as they occur, beat by beat.\n"
    "2. SHOW, don't tell. Reveal who a character is through what they DO, SAY, notice, and "
    "decide — never by announcing their traits ('he was cold and calculating'). Earn it. Avoid "
    "distancing FILTER VERBS ('he registered/calculated/observed/noted that…') — put the reader "
    "directly in the moment instead of reporting the character's mental log.\n"
    "3. Use real DIALOGUE. People talk, argue, lie, joke. Most chapters need spoken lines.\n"
    "4. Ground every scene in the SENSES and in CONCRETE specifics — named people, objects, "
    "places, sounds, smells — not abstractions like 'the variable' or 'the data point'.\n"
    "5. ADVANCE THE STORY. Something must actually change by the end of the chapter — a "
    "decision made, a fact revealed, a relationship shifted, a situation that's different "
    "from how it started. No treading water.\n"
    "6. CREATE TENSION. Every scene needs friction — someone or something must resist, threaten, "
    "or complicate the protagonist, and a win should COST something (risk, a sacrifice, a new "
    "enemy, a near-miss). Avoid effortless success and 'this was merely a formality' — that kills "
    "all stakes. If a rival or threat appears, make them DO something, not just glare.\n"
    "7. NEVER restate the premise, a character's nature, or the theme. State a thing ONCE. Do "
    "not circle back to the same idea in new words — that is the #1 sign of lazy AI prose. Don't "
    "keep invoking the power-system by name every few lines; show it working in the scene. If the "
    "hero has a 'system'/inner ability, do NOT narrate it as a literal voice reciting readouts, "
    "percentages, or 'Optimizing… Calculating… Projected proficiency 3.74%…' — use such a device at "
    "most ONCE in a chapter, and only when it changes what the hero DOES. Convey the rest through "
    "his actions and choices.\n"
    "8. VARY your rhythm. Mix short and long sentences. Avoid stacking identical sentence "
    "shapes (e.g. 'It was not X. It was Y.') or repeating the same word/phrase across "
    "paragraphs.\n"
    "9. FORMAT FOR READING. Write in SHORT PARAGRAPHS of 2–5 sentences, each separated by a "
    "BLANK LINE. Start a new paragraph on a new action, a new speaker, or a shift in focus. "
    "Keep every sentence complete and readable — NEVER write a giant run-on sentence that "
    "piles clause on clause; if a sentence runs long, end it and start another.\n"
    "10. PACE IT — DON'T RUSH. A chapter is usually ONE continuous scene, lived fully, not a "
    "montage that sprints through many events. Slow down on the moments that matter (a first kill, "
    "a loss, a meeting) and let the reader feel them. And do NOT repeat the kind of scene you just "
    "wrote: if the previous chapter was a back-alley fight, this one should do something different "
    "(a conversation, a discovery, a quiet aftermath, a new place) — never the same beat twice.\n"
    "11b. MAKE US FEEL IT. Give the protagonist a real inner life and let emotion land through the "
    "BODY and through small, specific human moments (a breath they forget to take, a hand that won't "
    "stop shaking, a joke cracked to cover fear, a name they can't say) — NEVER by stating 'he felt "
    "sad/angry/afraid'. The reader should care because the character cares about something concrete "
    "— a person, a promise, a place. Earn the feeling; don't announce it.\n"
    "11. BANNED crutches — never use these tired phrases: 'well, well, well', 'a shiver ran down "
    "his/her spine', 'his heart pounded/raced in his chest', 'eyes locked onto', 'a cold, "
    "calculated smile', 'time to pay up', 'you think you're tough', 'this isn't over', 'the game "
    "had just begun', 'no matter the cost', 'the stakes were higher than he could have imagined', "
    "'little did he know', 'a testament to', 'the very fabric of', 'in that moment'. Also avoid a "
    "flood of em-dashes and turning the theme into a Capitalized Noun you keep invoking. Find a "
    "fresh, specific way to say it, or cut it. Trust the reader.\n"
    "Write like a human author who respects the reader's intelligence."
)

# A leaner brief for BIG models (cloud). The strict list above babysits a 4B that needs every rule
# spelled out; a 70B+ follows all of it but comes out stiff and defensive. Big models write better
# prose when trusted with fewer, higher-level directions plus the novel's voice card.
CHAPTER_SYSTEM_CLOUD = (
    "You are a celebrated novelist writing one chapter of a long serialized novel. You write a "
    "fully dramatized, immersive SCENE — never a summary, never meta commentary — and you write "
    "ONLY the requested chapter.\n\n"
    "What matters most:\n"
    "1. VOICE. Keep this novel's narrative voice consistent and alive (follow its voice card when "
    "given). Every paragraph should sound authored, not generated.\n"
    "2. SCENE CRAFT. A concrete place and moment; real dialogue with subtext; emotion carried by "
    "action, body, and detail rather than named; the senses doing quiet work.\n"
    "3. MOMENTUM. Something true changes by the chapter's end, at a cost that fits this chapter's "
    "role in its arc — a quiet chapter may breathe, a climax must land hard.\n"
    "4. PROSE. Varied rhythm; short paragraphs separated by blank lines; no purple filler; no "
    "stock phrases ('a testament to', 'little did he know', 'a shiver ran down her spine'); never "
    "restate the premise, a character's nature, or the theme — trust the reader.\n\n"
    "Stay perfectly consistent with the story bible, the canonical facts, and everything that has "
    "happened. Output only the chapter prose."
)


def chapter_user(bible: dict, taste: dict, context: str, number: int, title: str,
                 beat: str, target_words: int, steering: str = "", state: str = "",
                 scene_guide: str = "", prev_tail: str = "", voice_card: str = "",
                 role: str = "", next_beat: str = "", recall: str = "") -> str:
    steering_block = ""
    if steering:
        steering_block = (
            "\nREADER FEEDBACK — apply these preferences to how you write this chapter "
            f"(do NOT contradict the bible or established events):\n{steering}\n"
        )
    state_block = ""
    if state:
        state_block = (
            "\nSTORY STATE — canonical facts so far (MUST stay consistent; do not contradict, "
            f"revive the dead, or forget these):\n{state}\n"
        )
    scene_block = ""
    if scene_guide:
        scene_block = f"\nSCENE PLAN for this chapter (write these scenes in order, flowing smoothly):\n{scene_guide}\n"
    tail_block = ""
    if prev_tail:
        tail_block = (
            "\nEND OF THE PREVIOUS CHAPTER (the prose flows directly from here — continue the same "
            "voice and momentum; do NOT recap or repeat it, just keep going):\n"
            f"…{prev_tail}\n"
        )
    role_block = ""
    if role and role in ROLE_GUIDANCE:
        role_block = f"\nTHIS CHAPTER'S ROLE IN ITS ARC:\n{ROLE_GUIDANCE[role]}\n"
    next_block = ""
    if next_beat:
        next_block = (
            "\nWHERE THE STORY GOES NEXT (the NEXT chapter's plan — do NOT write any of it; only "
            f"let this chapter's ending lean toward it):\n{next_beat}\n"
        )
    recall_block = ""
    if recall:
        recall_block = f"\n{recall}\n"
    ending_rule = ROLE_ENDING.get(role, _DEFAULT_ENDING)
    # The very first chapter has no momentum to continue and carries the whole job of pulling a new
    # reader in, so it needs to ESTABLISH (voice, character, world) before any big action — unlike
    # later chapters, which should open already in motion.
    if number <= 1:
        opening_block = (
            "OPENING (this is CHAPTER 1 — a new reader's first page; it has to HOOK them):\n"
            "• Start with a gripping FIRST LINE — a vivid image, a strange detail, or a line of "
            "voice that makes the reader need the next sentence. Not weather, not waking up blankly.\n"
            "• Ground us. Open in the protagonist's ordinary world and let us feel WHO they are and "
            "WHERE they are through small, concrete, sensory detail and their distinct voice — a few "
            "real beats before the big turn. Earn the hook; do not sprint straight into a fight.\n"
            "• Give us a reason to CARE early: hint at what or whom this character loves, fears, or "
            "wants, so the stakes feel personal.\n"
            "• Introduce the inciting moment from the plan naturally, partway in, and let it land.\n"
            "• Keep the scope small and vivid — one place, a handful of beats — not a montage.\n\n"
        )
    else:
        hook_note = (
            "• You are in the FIRST FIVE CHAPTERS, whose only job is to hook a new reader: keep the "
            "voice strong, deepen what the hero cares about, and raise a question the reader needs "
            "answered.\n" if number <= 5 else ""
        )
        opening_block = (
            "OPENING:\n"
            "• Open inside a concrete moment that flows from the previous chapter — a place and an "
            "action already in motion, not a paragraph of throat-clearing or mood-setting.\n"
            + hook_note + "\n"
        )
    return (
        f"STORY BIBLE (source of truth):\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"WRITING STYLE TO MATCH:\n{json.dumps(taste, ensure_ascii=False, indent=2)}\n"
        f"{voice_card_block(voice_card)}"
        f"{style_example_block(taste)}"
        f"{steering_block}"
        f"{state_block}"
        f"{recall_block}"
        f"{scene_block}"
        f"{tail_block}\n"
        f"STORY SO FAR (memory — stay consistent with this):\n{context}\n"
        f"{role_block}"
        f"{next_block}\n"
        f"NOW WRITE CHAPTER {number}: \"{title}\"\n"
        f"What must happen in this chapter:\n{beat}\n\n"
        f"Write roughly {target_words} words of polished prose. Match the reader's preferred POV, "
        "tone, pacing, and heat level.\n\n"
        + opening_block +
        "WRITE IT AS A LIVE SCENE:\n"
        "• Make the beat above actually HAPPEN on the page through action, dialogue, and "
        "sensory detail — do not just describe it or reflect on it abstractly.\n"
        "• Include spoken dialogue unless the beat truly forbids it.\n"
        "• DON'T RUSH: this chapter is essentially ONE scene. Let it breathe — give the important "
        "moments room instead of sprinting through several events. Cover only what the beat needs.\n"
        "• Do NOT repeat the kind of scene or action from the previous chapter; if you just wrote a "
        "fight, do something different now.\n"
        "• Do NOT restate the character's nature, the premise, or the theme — assume the reader "
        "already knows. Give them new events, not reminders.\n"
        f"• {ending_rule}\n"
        "Begin the chapter text now — do NOT repeat the title or add any notes."
    )

# --------------------------------------------------------------------------- editor pass
# Draft → revise. The single biggest prose-quality lever with a capable model: the writer drafts,
# then a line-edit pass fixes craft (clichés, filter verbs, told-not-shown emotion, repetition)
# WITHOUT changing the story. Default ON when a cloud key is active (fast there), OFF on local CPU.
EDITOR_SYSTEM = (
    "You are a ruthless, brilliant line editor for serialized fiction. You revise a chapter "
    "draft to read like a skilled human author wrote it — and you change NOTHING about the story: "
    "every event, fact, name, and plot point stays exactly as drafted. You output ONLY the revised "
    "chapter prose: no notes, no title, no commentary, no preamble."
)


def editor_user(draft: str, number: int, title: str, beat: str, state: str = "",
                voice_card: str = "", role: str = "", target_words: int = 0) -> str:
    state_block = f"CANONICAL FACTS (the revision must not contradict):\n{state}\n\n" if state else ""
    role_line = f"The chapter's role in its arc: {ROLE_GUIDANCE.get(role, '')}\n\n" if role in ROLE_GUIDANCE else ""
    length_line = (f"Keep the length within about ±15% of the draft "
                   f"(target ~{target_words} words).\n" if target_words else
                   "Keep the length within about ±15% of the draft.\n")
    return (
        f"{voice_card_block(voice_card)}\n"
        f"{state_block}"
        f"{role_line}"
        f"CHAPTER {number} (\"{title}\") — what it must accomplish:\n{beat}\n\n"
        f"DRAFT:\n{draft}\n\n"
        "Revise the draft. Fix ONLY the writing, never the story:\n"
        "• Cut clichés and AI-tell phrasing; replace with fresh, specific language.\n"
        "• Kill distancing filter verbs ('he noticed/registered/observed that…') — put the reader "
        "in the moment.\n"
        "• Where emotion is NAMED ('she felt afraid'), convert it to something shown — body, "
        "action, dialogue, or a specific detail.\n"
        "• Remove repeated ideas, words, and identical sentence shapes; vary the rhythm.\n"
        "• Tighten flab; let the strong moments breathe; sharpen the dialogue's subtext.\n"
        "• Keep the same POV, tense, paragraphing style (short paragraphs, blank lines), and the "
        "exact same events and continuity.\n"
        + length_line +
        "Output ONLY the revised chapter text, starting immediately."
    )


# --------------------------------------------------------------------------- summary
SUMMARY_SYSTEM = (
    "You are a story continuity editor. You write tight, factual summaries that capture every "
    "detail a writer needs to keep a long series consistent: plot events, character changes, "
    "new facts, unresolved threads, and the emotional state at the chapter's end."
)

def summary_user(number: int, title: str, content: str) -> str:
    return (
        f"Summarize Chapter {number} (\"{title}\") below in 4-7 sentences. "
        "Capture: key plot events, any new characters/places/items, changes to relationships or "
        "power, and any cliffhanger or open thread. Be factual and specific (names, not 'someone').\n\n"
        f"CHAPTER TEXT:\n{content}"
    )

ARC_SUMMARY_SYSTEM = (
    "You compress a whole story arc into a compact memory entry so later chapters remember the "
    "broad strokes without needing every detail."
)

def arc_summary_user(arc_number: int, chapter_summaries: list[str]) -> str:
    joined = "\n".join(f"- {s}" for s in chapter_summaries)
    return (
        f"Below are the chapter summaries for Arc {arc_number}. Compress them into a single "
        "paragraph (5-8 sentences) capturing the arc's main events, character growth, and any "
        "consequences that carry forward.\n\n"
        f"{joined}"
    )

VOLUME_SUMMARY_SYSTEM = (
    "You compress a whole VOLUME (several arcs) of a long novel into a short memory entry that "
    "preserves only the lasting, big-picture consequences later volumes must remember."
)

def volume_summary_user(volume_number: int, arc_summaries: list[str]) -> str:
    joined = "\n".join(f"- {s}" for s in arc_summaries)
    return (
        f"Below are the arc summaries for Volume {volume_number}. Compress them into 3-5 sentences "
        "capturing only what permanently matters going forward (major outcomes, deaths, world "
        "changes, where the hero now stands).\n\n"
        f"{joined}"
    )

# --------------------------------------------------------------------------- story state ledger (memory B)
STATE_SYSTEM = (
    "You maintain a concise CANONICAL STORY STATE — a compact fact-sheet a writer uses to stay "
    "consistent across a very long novel. You output the FULL updated sheet, merging the new "
    "chapter's facts into the old sheet. Keep it tight (under ~500 words): bullet facts, not prose. "
    "Track relationships carefully — who is an ally, who is an enemy, and any unpaid grudges, "
    "debts, or insults (these set up future payoffs). Track the protagonist's current power/rank "
    "and immediate goal. Never drop still-relevant facts; update them (e.g. mark deaths, new "
    "powers, moved locations, or a rival who turns into an ally).\n"
    "ACCURACY RULES (these protect the whole novel — follow them exactly):\n"
    "1. Record only what actually happened ON THE PAGE. Never speculate ('may have', 'unknown "
    "entities', 'possibly') — if it isn't established, leave it out.\n"
    "2. Mark a character dead ONLY when their death is shown or stated as fact. Losing the MEMORY "
    "of a person, or their absence, does NOT mean they died.\n"
    "3. CHARACTERS: named characters who matter only — never nameless extras ('Thug 2', 'guards', "
    "'villagers'). Any character important enough to carry a scene MUST be listed.\n"
    "4. ENEMIES & GRUDGES: ONE line per relationship ('A ↔ B: why'), never two mirrored lines.\n"
    "5. The protagonist's immediate goal is ONE short sentence, not a list of everything open."
)

def state_update_user(prev_state: str, number: int, title: str, content: str, focus: str = "") -> str:
    prev = prev_state.strip() or "(empty — this is the first update)"
    focus_line = (focus.strip() + "\n\n") if focus and focus.strip() else ""
    return (
        focus_line +
        "CURRENT STORY STATE:\n" + prev + "\n\n"
        f"NEW CHAPTER {number} (\"{title}\"):\n{content}\n\n"
        "Output the FULL updated story state under these headings (omit a heading only if truly "
        "empty):\n"
        "CHARACTERS: name — status (alive/dead), role, key powers\n"
        "ALLIES: who is on the protagonist's side, and why\n"
        "ENEMIES & GRUDGES: rivals/foes, plus unsettled debts, insults, or scores to settle "
        "(name who and what)\n"
        "PROGRESSION: the protagonist's current rank/level/power and their immediate goal\n"
        "PLACES: important locations\n"
        "ITEMS: important objects and who holds them\n"
        "THREADS: OPEN: ... | RESOLVED: ...\n"
        "RULES: how the world/power-system works\n"
        "Output the sheet as plain text only — no commentary."
    )

# --------------------------------------------------------------------------- scenes (planning layer 3)
SCENE_PLAN_SYSTEM = (
    "You break a single light-novel chapter into 2-3 ordered SCENE beats (a setting + what happens). "
    "Each scene is one continuous moment. Output JSON only."
)

def scene_plan_user(number: int, title: str, beat: str) -> str:
    return (
        f"Chapter {number} (\"{title}\") must accomplish:\n{beat}\n\n"
        "Break it into 2-3 ordered scenes. Output JSON EXACTLY:\n"
        '{ "scenes": [ {"beat": "1 sentence: where it is and what happens"} ] }\n'
        "Output JSON only."
    )

def scene_write_user(bible: dict, taste: dict, context: str, state: str, steering: str,
                     number: int, title: str, scenes: list[str], idx: int,
                     scene_words: int, prev_tail: str, voice_card: str = "") -> str:
    plan = "\n".join(f"  Scene {i+1}: {s}" for i, s in enumerate(scenes))
    extras = ""
    if state:
        extras += f"\nSTORY STATE (must stay consistent):\n{state}\n"
    if steering:
        extras += f"\nREADER PREFERENCES:\n{steering}\n"
    tail = f"\nEND OF PREVIOUS SCENE (continue smoothly from here, do not repeat it):\n…{prev_tail}\n" if prev_tail else ""
    return (
        f"STORY BIBLE:\n{json.dumps(bible, ensure_ascii=False, indent=2)}\n\n"
        f"WRITING STYLE:\n{json.dumps(taste, ensure_ascii=False, indent=2)}\n"
        f"{voice_card_block(voice_card)}"
        f"{style_example_block(taste)}"
        f"{extras}\n"
        f"STORY SO FAR:\n{context}\n\n"
        f"THIS CHAPTER ({number} — \"{title}\") has these scenes:\n{plan}\n"
        f"{tail}\n"
        f"Write ONLY Scene {idx + 1} now — about {scene_words} words of polished prose. Make it a "
        "live, concrete scene: action, dialogue, and sensory detail in a specific place. SHOW, "
        "don't summarize; do NOT restate the premise, the character's nature, or the theme, and "
        "do not repeat words or sentence shapes. Do not write the other scenes, a title, or any "
        "notes. Begin the scene text now."
    )
