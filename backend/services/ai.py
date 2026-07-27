import os
import re
import logging
import requests
from pathlib import Path
from typing import Optional
from fastapi import HTTPException

_SKILLS_BASE = Path(__file__).parent.parent.parent / "astro-skills"

logger = logging.getLogger("starjyotish.ai")

# Human-readable labels for skill file paths (shown in logs and UI)
_SKILL_LABELS: dict[str, str] = {
    "planets/jupiter/SKILL.md":                    "Jupiter Planetary Guide",
    "planets/saturn/SKILL.md":                     "Saturn Planetary Guide",
    "planets/rahu/SKILL.md":                       "Rahu Planetary Guide",
    "planets/venus/SKILL.md":                      "Venus Planetary Guide",
    "houses/astrology-12-houses/SKILL.md":         "12 Houses Guide",
    "houses/house-lords/SKILL.md":                 "House Lords System",
    "career/career-d10-bootcamp/SKILL.md":         "Career & D10 Bootcamp",
    "career/d10-dasamsa/SKILL.md":                 "D10 Dasamsa Chart",
    "career/vedic-career/SKILL.md":                "Vedic Career Astrology",
    "children/child-astrology/SKILL.md":           "Child Astrology",
    "children/d7-progeny/SKILL.md":                "D7 Progeny Astrology",
    "children/d7-saptamsha/SKILL.md":              "D7 Saptamsha Chart",
    "marriage/SKILL.md":                           "Marriage Consultation",
    "gemstones/vedic-gemstones/SKILL.md":          "Vedic Gemstones Guide",
    "gemstones/vedic-gemstones-complete/SKILL.md": "Navratna Complete Guide",
    "gemstones/crystals/SKILL.md":                 "Crystals & Chakras",
    "gemstones/crystal-trees/SKILL.md":            "Crystal Trees Guide",
    "gemstones/gems-crystals-guide/SKILL.md":      "Gems & Crystals Guide",
    "gemstones/vedic-gemstones/references/ruby.md":          "Ruby (Gemstone)",
    "gemstones/vedic-gemstones/references/pearl.md":         "Pearl (Gemstone)",
    "gemstones/vedic-gemstones/references/red-coral.md":     "Red Coral (Gemstone)",
    "gemstones/vedic-gemstones/references/emerald.md":       "Emerald (Gemstone)",
    "gemstones/vedic-gemstones/references/yellow-sapphire.md": "Yellow Sapphire (Gemstone)",
    "gemstones/vedic-gemstones/references/diamond.md":       "Diamond (Gemstone)",
    "gemstones/vedic-gemstones/references/blue-sapphire.md": "Blue Sapphire (Gemstone)",
    "gemstones/vedic-gemstones/references/hessonite.md":     "Hessonite (Gemstone)",
    "gemstones/vedic-gemstones/references/cats-eye.md":      "Cat's Eye (Gemstone)",
    "gemstones/vedic-gemstones/references/opal.md":          "Opal (Gemstone)",
    "numerology/mulank/SKILL.md":                  "Mulank Numerology",
    "numerology/bhagyank/SKILL.md":                "Bhagyank Numerology",
    "nakshatra/SKILL.md":                          "Nakshatra Guide",
    "rudraksha/SKILL.md":                          "Rudraksha Guide",
    "vedic-kundli/SKILL.md":                       "Vedic Kundli Reader",
}

# ── Classical dignity tables (sign_index 0=Aries … 11=Pisces) ────────────

_EXALTED = {
    "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5,
    "Jupiter": 3, "Venus": 11, "Saturn": 6,
}
_DEBILITATED = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0,
}
_OWN_SIGNS: dict[str, list[int]] = {
    "Sun":     [4],
    "Moon":    [3],
    "Mars":    [0, 7],
    "Mercury": [2, 5],
    "Jupiter": [8, 11],
    "Venus":   [1, 6],
    "Saturn":  [9, 10],
}

_SECTION_NAMES = [
    "Chart Overview",
    "Personality & Appearance",
    "Career & Wealth",
    "Relationships & Marriage",
    "Health",
    "Spiritual Inclination",
    "Current Period (Dasha)",
]
_SECTION_ICONS = {
    "Chart Overview":            "📜",
    "Personality & Appearance":  "🧬",
    "Career & Wealth":           "💼",
    "Relationships & Marriage":  "💞",
    "Health":                    "🌿",
    "Spiritual Inclination":     "🕉️",
    "Current Period (Dasha)":    "⏳",
}

# ── Divisional chart keyword detection ───────────────────────────────────────
# Stored as ordered list of tuples so iteration order is guaranteed.
# Longer / more-specific keys first to prevent substring collisions
# (e.g. "d6" must NOT match inside "d60").
_TRANSIT_KEYWORDS = [
    "transit", "gochara", "gochar", "current position", "currently",
    "right now", "today", "this week", "this month", "this year",
    "running dasha", "running period", "upcoming", "future",
    "effect of", "impact of", "influence of", "present",
    "planetary movement", "moving through", "passing through",
    "shani", "rahu transit", "jupiter transit", "saturn transit",
    "what is happening", "what will happen", "prediction for",
]

_DIVISION_KEYWORDS: list[tuple[str, int]] = [
    # multi-word phrases first
    ("past life",    60),
    ("real estate",   4),
    # single-word, longer before shorter
    ("profession",   10),
    ("business",     10),
    ("meditation",   20),
    ("education",    24),
    ("spiritual",    20),
    ("fertility",     7),
    ("learning",     24),
    ("property",      4),
    ("vehicle",      16),
    ("sibling",       3),
    ("brother",       3),
    ("vitality",     27),
    ("physical",     27),
    ("worship",      20),
    ("courage",       3),
    ("finance",       2),
    ("partner",       9),
    ("disease",       6),
    ("illness",       6),
    ("sister",        3),
    ("father",       12),
    ("mother",       12),
    ("parent",       12),
    ("children",      7),
    ("daughter",      7),
    ("dharma",        9),
    ("spouse",        9),
    ("career",       10),
    ("wealth",        2),
    ("health",        6),
    ("money",         2),
    ("karma",        60),
    ("child",         7),
    ("study",        24),
    ("pooja",        20),
    ("work",         10),
    ("home",          4),
    ("land",          4),
    ("job",          10),
    # exact chart codes — longer before shorter to avoid d6 matching d60
    ("d60",          60),
    ("d45",          45),
    ("d40",          40),
    ("d30",          30),
    ("d27",          27),
    ("d24",          24),
    ("d20",          20),
    ("d16",          16),
    ("d12",          12),
    ("d10",          10),
    ("d9",            9),
    ("d8",            8),
    ("d7",            7),
    ("d6",            6),
    ("d4",            4),
    ("d3",            3),
    ("d2",            2),
    # generic fallbacks
    ("marriage",      9),
    ("navamsa",       9),
    ("marry",         9),
    ("married",       9),
]

# Complete D1–D60 divisional chart reference names
_DIVISION_NAMES = {
    1:  "D1 (Lagna — Overall life & personality)",
    2:  "D2 (Hora — Wealth & financial potential)",
    3:  "D3 (Drekkana — Siblings, courage & short journeys)",
    4:  "D4 (Chaturthamsha — Property, home & fixed assets)",
    6:  "D6 (Shashthamsha — Health, enemies & disease)",
    7:  "D7 (Saptamsha — Children & progeny)",
    8:  "D8 (Ashtamsha — Obstacles & sudden events)",
    9:  "D9 (Navamsha — Marriage, dharma & spiritual strength)",
    10: "D10 (Dashamsha — Career, profession & public life)",
    12: "D12 (Dwadashamsha — Parents & ancestral lineage)",
    16: "D16 (Shodashamsha — Vehicles, luxury & comforts)",
    20: "D20 (Vimshamsha — Spiritual practices & worship)",
    24: "D24 (Chaturvimshamsha — Education, skills & learning)",
    27: "D27 (Nakshatramsha — Physical strength & vitality)",
    30: "D30 (Trimshamsha — Misfortunes & evils)",
    40: "D40 (Khavedamsha — Maternal ancestry)",
    45: "D45 (Akshavedamsha — Paternal ancestry)",
    60: "D60 (Shashtiamsha — Past-life karma & soul's journey)",
}

# ── Skill file keyword map ────────────────────────────────────────────────────
# Ordered list of (keyword, relative_path).  Longest / most-specific first.
_GEM_REFS = "gemstones/vedic-gemstones/references"
_MARRIAGE_REFS = "marriage/references"
_SKILL_MAP: list[tuple[str, str]] = [
    # ── Gemstones: specific stones (multi-word before single-word) ────────
    ("yellow sapphire",  f"{_GEM_REFS}/yellow-sapphire.md"),
    ("blue sapphire",    f"{_GEM_REFS}/blue-sapphire.md"),
    ("red coral",        f"{_GEM_REFS}/red-coral.md"),
    ("cat's eye",        f"{_GEM_REFS}/cats-eye.md"),
    ("cats eye",         f"{_GEM_REFS}/cats-eye.md"),
    ("cat eye",          f"{_GEM_REFS}/cats-eye.md"),
    ("lehsunia",         f"{_GEM_REFS}/cats-eye.md"),
    ("hessonite",        f"{_GEM_REFS}/hessonite.md"),
    ("gomedh",           f"{_GEM_REFS}/hessonite.md"),
    ("gomed",            f"{_GEM_REFS}/hessonite.md"),
    ("pukhraj",          f"{_GEM_REFS}/yellow-sapphire.md"),
    ("neelam",           f"{_GEM_REFS}/blue-sapphire.md"),
    ("moonga",           f"{_GEM_REFS}/red-coral.md"),
    ("manikya",          f"{_GEM_REFS}/ruby.md"),
    ("emerald",          f"{_GEM_REFS}/emerald.md"),
    ("panna",            f"{_GEM_REFS}/emerald.md"),
    ("diamond",          f"{_GEM_REFS}/diamond.md"),
    ("heera",            f"{_GEM_REFS}/diamond.md"),
    ("sapphire",         f"{_GEM_REFS}/blue-sapphire.md"),
    ("coral",            f"{_GEM_REFS}/red-coral.md"),
    ("pearl",            f"{_GEM_REFS}/pearl.md"),
    ("ruby",             f"{_GEM_REFS}/ruby.md"),
    ("opal",             f"{_GEM_REFS}/opal.md"),
    # ── General gemstone / crystal ────────────────────────────────────────
    # (more specific multi-word keywords first — first match wins, so a
    # general single-word keyword later in this block must not shadow them)
    ("complete gemstone",       "gemstones/vedic-gemstones-complete/SKILL.md"),
    ("all 9 gemstones",         "gemstones/vedic-gemstones-complete/SKILL.md"),
    ("navratna complete",       "gemstones/vedic-gemstones-complete/SKILL.md"),
    ("navratna",         "gemstones/vedic-gemstones/SKILL.md"),
    ("ratna",            "gemstones/vedic-gemstones/SKILL.md"),
    ("gemstone",         "gemstones/vedic-gemstones/SKILL.md"),
    ("gem stone",        "gemstones/vedic-gemstones/SKILL.md"),
    ("gem",              "gemstones/vedic-gemstones/SKILL.md"),
    ("crystal",          "gemstones/crystals/SKILL.md"),
    ("chakra",           "gemstones/crystals/SKILL.md"),
    # ── Doshas & special yogas ────────────────────────────────────────────
    ("mangal dosha",     "vedic-kundli/SKILL.md"),
    ("kaal sarp",        "vedic-kundli/SKILL.md"),
    ("kalsarpa",         "vedic-kundli/SKILL.md"),
    ("sade sati",        "vedic-kundli/SKILL.md"),
    ("manglik",          "vedic-kundli/SKILL.md"),
    # ── Career (multiple skills) ──────────────────────────────────────────
    ("ashtakvarga",      "career/vedic-career/SKILL.md"),
    ("vedic career",     "career/vedic-career/SKILL.md"),
    ("profession",       "career/career-d10-bootcamp/SKILL.md"),
    ("business",         "career/career-d10-bootcamp/SKILL.md"),
    ("career",           "career/career-d10-bootcamp/SKILL.md"),
    ("job",              "career/career-d10-bootcamp/SKILL.md"),
    ("work",             "career/career-d10-bootcamp/SKILL.md"),
    # ── Children / Progeny ───────────────────────────────────────────────
    ("panchak",          "children/d7-progeny/references/panchak-gandmool.md"),
    ("gandmool",         "children/d7-progeny/references/panchak-gandmool.md"),
    ("progeny",          "children/d7-progeny/SKILL.md"),
    ("fertility",        "children/d7-progeny/SKILL.md"),
    ("conception",       "children/d7-progeny/SKILL.md"),
    ("children",         "children/child-astrology/SKILL.md"),
    ("child",            "children/child-astrology/SKILL.md"),
    # ── Marriage ─────────────────────────────────────────────────────────
    # (specific reference-file keywords first — see ordering note above)
    ("marriage timing",  f"{_MARRIAGE_REFS}/timing-techniques.md"),
    ("when will i get married", f"{_MARRIAGE_REFS}/timing-techniques.md"),
    ("when will i marry", f"{_MARRIAGE_REFS}/timing-techniques.md"),
    ("quality of marriage", f"{_MARRIAGE_REFS}/quality-of-marriage.md"),
    ("happy marriage",    f"{_MARRIAGE_REFS}/quality-of-marriage.md"),
    ("darakaraka",         f"{_MARRIAGE_REFS}/darakaraka.md"),
    ("marriage",         "marriage/SKILL.md"),
    ("spouse",           "marriage/SKILL.md"),
    ("partner",          "marriage/SKILL.md"),
    # ── Planets ──────────────────────────────────────────────────────────
    ("jupiter",          "planets/jupiter/SKILL.md"),
    ("saturn",           "planets/saturn/SKILL.md"),
    ("shukra",           "planets/venus/SKILL.md"),
    ("shani",            "planets/saturn/SKILL.md"),
    ("venus",            "planets/venus/SKILL.md"),
    ("rahu",             "planets/rahu/SKILL.md"),
    ("guru",             "planets/jupiter/SKILL.md"),
    # ── Houses ───────────────────────────────────────────────────────────
    ("house lord",       "houses/house-lords/SKILL.md"),
    ("lord in",          "houses/house-lords/SKILL.md"),
    ("house",            "houses/astrology-12-houses/SKILL.md"),
    # ── Numerology ───────────────────────────────────────────────────────
    ("bhagyank",         "numerology/bhagyank/SKILL.md"),
    ("mulank",           "numerology/mulank/SKILL.md"),
    ("numerology",       "numerology/mulank/SKILL.md"),
    # ── Other topics ─────────────────────────────────────────────────────
    ("nakshatra",        "nakshatra/SKILL.md"),
    ("rudraksha gift",   "rudraksha/references/gifting.md"),
    ("gift rudraksha",   "rudraksha/references/gifting.md"),
    ("purify rudraksha", "rudraksha/references/purification-rituals.md"),
    ("rudraksha purification", "rudraksha/references/purification-rituals.md"),
    ("rudraksha",        "rudraksha/SKILL.md"),
    ("past life",        "vedic-kundli/SKILL.md"),
    ("education",        "houses/astrology-12-houses/SKILL.md"),
    ("disease",          "vedic-kundli/SKILL.md"),
    ("illness",          "vedic-kundli/SKILL.md"),
    ("health",           "vedic-kundli/SKILL.md"),
    ("karma",            "vedic-kundli/SKILL.md"),
    # ── Divisional chart codes — longer before shorter ────────────────────
    ("d60",              "vedic-kundli/SKILL.md"),
    ("d24",              "houses/astrology-12-houses/SKILL.md"),
    ("d12",              "vedic-kundli/SKILL.md"),
    ("d10",              "career/d10-dasamsa/SKILL.md"),
    ("d9",               "marriage/SKILL.md"),
    ("d7",               "children/d7-saptamsha/SKILL.md"),
    ("d6",               "vedic-kundli/SKILL.md"),
]

# ── Cross-reference map (from index.md "Skill Compatibility" table) ──────────
# When BOTH keywords appear in the question, load the secondary skill
# in addition to the primary match from _SKILL_MAP.
_SKILL_CROSS_REFS: list[tuple[str, str, str]] = [
    # rudraksha sub-topics (more robust than exact-phrase keywords above,
    # since "purify my rudraksha" etc. won't literally contain "purify rudraksha")
    ("rudraksha", "gift",    "rudraksha/references/gifting.md"),
    ("rudraksha", "purify",  "rudraksha/references/purification-rituals.md"),
    ("rudraksha", "purification", "rudraksha/references/purification-rituals.md"),
    # marriage sub-topics
    ("marriage",  "quality", "marriage/references/quality-of-marriage.md"),
    ("marriage",  "happy",   "marriage/references/quality-of-marriage.md"),
    ("marriage",  "timing",  "marriage/references/timing-techniques.md"),
    # marriage combos
    ("marriage",  "venus",   "planets/venus/SKILL.md"),
    ("marriage",  "saturn",  "planets/saturn/SKILL.md"),
    ("marriage",  "rahu",    "planets/rahu/SKILL.md"),
    ("marriage",  "jupiter", "planets/jupiter/SKILL.md"),
    ("spouse",    "venus",   "planets/venus/SKILL.md"),
    # career combos
    ("career",    "saturn",  "planets/saturn/SKILL.md"),
    ("career",    "rahu",    "planets/rahu/SKILL.md"),
    ("career",    "jupiter", "planets/jupiter/SKILL.md"),
    ("career",    "d10",     "career/d10-dasamsa/SKILL.md"),
    ("job",       "saturn",  "planets/saturn/SKILL.md"),
    # children combos
    ("children",  "jupiter", "planets/jupiter/SKILL.md"),
    ("child",     "jupiter", "planets/jupiter/SKILL.md"),
    ("children",  "d7",      "children/d7-saptamsha/SKILL.md"),
    ("child",     "d7",      "children/d7-saptamsha/SKILL.md"),
    # gemstone + planet
    ("gemstone",  "saturn",  "planets/saturn/SKILL.md"),
    ("gemstone",  "jupiter", "planets/jupiter/SKILL.md"),
    ("gemstone",  "venus",   "planets/venus/SKILL.md"),
    ("gemstone",  "rahu",    "planets/rahu/SKILL.md"),
    # house + lord
    ("house",     "lord",    "houses/house-lords/SKILL.md"),
    ("lord",      "house",   "houses/house-lords/SKILL.md"),
    # rahu + career
    ("rahu",      "career",  "career/career-d10-bootcamp/SKILL.md"),
    # dosha combos
    ("mangal",    "dosha",   "vedic-kundli/SKILL.md"),
    ("sade",      "sati",    "planets/saturn/SKILL.md"),
    # kundli reading
    ("kundli",    "career",  "career/career-d10-bootcamp/SKILL.md"),
    ("kundli",    "marriage","marriage/SKILL.md"),
]

# Supplementary lagna-map appended when a per-stone reference file is loaded
_GEM_LAGNA_MAP = "gemstones/vedic-gemstones/SKILL.md"

_CLASSICAL = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"}

_GROQ_URL          = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL        = "llama-3.3-70b-versatile"
_CLAUDE_MODEL      = "claude-sonnet-4-6"
_OPENROUTER_URL    = "https://openrouter.ai/api/v1/chat/completions"
_OPENROUTER_MODEL  = "anthropic/claude-sonnet-4.6"


# ─────────────────────────────────────────────────────────────────────────────
# Dignity helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_dignity(planet_name: str, sign_index: int) -> str:
    if planet_name not in _CLASSICAL:
        return ""
    if _EXALTED.get(planet_name) == sign_index:
        return "exalted"
    if _DEBILITATED.get(planet_name) == sign_index:
        return "debilitated"
    if sign_index in _OWN_SIGNS.get(planet_name, []):
        return "own sign"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Division detection
# ─────────────────────────────────────────────────────────────────────────────

def _detect_division(question: str) -> int:
    """
    Return the most relevant divisional chart number for this question.
    Iterates ordered keyword list (longest first) to prevent substring
    collisions (e.g. "d6" inside "d60").  Defaults to 1 (D1).
    """
    q_lower = question.lower()
    for keyword, division in _DIVISION_KEYWORDS:
        if keyword in q_lower:
            return division
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Skill-file loading helpers
# ─────────────────────────────────────────────────────────────────────────────

def _strip_frontmatter(raw: str) -> str:
    """Remove YAML frontmatter (--- … ---) from a markdown file."""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        return parts[2].strip() if len(parts) >= 3 else raw
    return raw


# Lookup tables used by _extract_relevant_section
_ORDINALS = [
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th",
]
_ROMAN_NUMS   = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
_WORD_ORDINALS = [
    "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
]
_SIGNS_LOWER = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]


def _find_in_content(content_lower: str, terms: list[str], after: int = 0) -> int:
    """Earliest position where any term appears after `after`. -1 if none."""
    best = -1
    for t in terms:
        idx = content_lower.find(t, after)
        if idx != -1 and (best == -1 or idx < best):
            best = idx
    return best


def _extract_relevant_section(
    content: str,
    question: str,
    intro_chars: int = 800,
    section_chars: int = 9000,
) -> str:
    """
    Return a targeted excerpt from a potentially large skill file.

    Strategy (in priority order):
      1. Find a markdown heading that mentions the query term.
      2. Fall back to first plain-text occurrence after the intro.
      3. Return the opening chunk if nothing matches.

    Uses "house <roman>" variants to avoid Roman-numeral substring collisions
    (e.g. bare "v" would match "iv" and "vi").
    Normalises CRLF → LF so anchors work on Windows-authored files.
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    q_lower  = question.lower()
    c_lower  = content.lower()
    intro    = content[:intro_chars]

    def _heading_search(variants: list[str]) -> int:
        for v in variants:
            # {{1,4}} — doubled braces produce literal {1,4} in the regex
            m = re.search(
                rf"(?:^|\n)#{{1,4}}[^\n]*{re.escape(v)}[^\n]*",
                c_lower,
            )
            if m and m.start() >= intro_chars:
                return m.start()
        return -1

    def _text_search(variants: list[str]) -> int:
        return _find_in_content(c_lower, variants, after=intro_chars)

    def _extract(pos: int) -> str:
        return f"{intro}\n[...]\n{content[pos: pos + section_chars]}"

    # 1. House number
    for i, (ord_, roman, word) in enumerate(zip(_ORDINALS, _ROMAN_NUMS, _WORD_ORDINALS), 1):
        triggers = [ord_, f"house {i}", f"{i} house", f"{word} house", f"house {word}"]
        if any(t in q_lower for t in triggers):
            heading_variants = [f"house {roman}", word, ord_, f"house {i}", f"{word} house"]
            pos = _heading_search(heading_variants)
            if pos == -1:
                pos = _text_search([f"house {roman}", word, ord_])
            if pos != -1:
                return _extract(pos)
            break

    # 2. Zodiac sign
    for sign in _SIGNS_LOWER:
        if sign in q_lower:
            pos = _heading_search([sign])
            if pos == -1:
                pos = _text_search([sign])
            if pos != -1:
                return _extract(pos)
            break

    # 3. Dasha / timing
    if any(k in q_lower for k in ("dasha", "mahadasha", "antardasha", "transit")):
        pos = _heading_search(["dasha", "maha dasha", "antardasha", "timing"])
        if pos == -1:
            pos = _text_search(["dasha"])
        if pos != -1:
            return _extract(pos)

    # 4. Remedies
    if any(k in q_lower for k in ("remedy", "remedies", "mantra", "upay")):
        pos = _heading_search(["remed", "mantra", "upay"])
        if pos == -1:
            pos = _text_search(["remed", "mantra"])
        if pos != -1:
            return _extract(pos)

    # Fallback: opening chunk
    return content[: intro_chars + section_chars]


def _read_skill(rel_path: str, question: str, max_chars: int) -> str:
    """Read one skill file and return a relevant excerpt (stripped of frontmatter)."""
    try:
        raw = _strip_frontmatter((_SKILLS_BASE / rel_path).read_text(encoding="utf-8"))
    except Exception:
        return ""
    if len(raw) > max_chars:
        return _extract_relevant_section(raw, question)
    return raw


def _load_skill_content(question: str, max_chars: int = 10000) -> str:
    """
    Return skill reference text for the question.

    1. Loads the primary skill matched by _SKILL_MAP.
    2. For per-stone reference files appends the gemstone lagna map.
    3. Checks _SKILL_CROSS_REFS and appends a secondary skill excerpt
       (3 000 chars) when two triggering keywords co-occur.

    Returns "" when nothing matches.
    """
    q_lower = question.lower()
    primary_path = None
    primary_excerpt = ""

    for keyword, rel_path in _SKILL_MAP:
        if keyword in q_lower:
            primary_path = rel_path
            excerpt = _read_skill(rel_path, question, max_chars)
            if not excerpt:
                continue
            primary_excerpt = f"\nRELEVANT ASTROLOGY SKILL REFERENCE ({rel_path}):\n{excerpt}"
            break

    if not primary_excerpt:
        return ""

    parts = [primary_excerpt]

    # Gemstone stone-reference → also inject the lagna compatibility map
    if primary_path and "/references/" in primary_path:
        try:
            lagna_raw = _strip_frontmatter(
                (_SKILLS_BASE / _GEM_LAGNA_MAP).read_text(encoding="utf-8")
            )
            marker = "## Quick lagna-to-favorable-stones map"
            idx = lagna_raw.find(marker)
            lagna_section = lagna_raw[idx: idx + 3500] if idx >= 0 else lagna_raw[:3500]
            parts.append(f"\nGEMSTONE LAGNA COMPATIBILITY MAP:\n{lagna_section}")
        except Exception:
            pass

    # Cross-reference secondary skill (max 3 000 chars of targeted excerpt)
    for kw1, kw2, secondary_path in _SKILL_CROSS_REFS:
        if (kw1 in q_lower and kw2 in q_lower
                and secondary_path != primary_path):
            excerpt = _read_skill(secondary_path, question, max_chars=3000)
            if excerpt:
                parts.append(
                    f"\nCROSS-REFERENCE SKILL ({secondary_path}):\n{excerpt[:3000]}"
                )
            break   # one cross-ref per question is enough

    return "\n".join(parts) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# Chart formatting
# ─────────────────────────────────────────────────────────────────────────────

def _format_planets(planets: list, label: str) -> str:
    """Format a planet list into compact readable lines."""
    lines = [f"\n{label}:"]
    for p in planets:
        dignity = get_dignity(p["name"], p["sign_index"])
        parts = [p["sign"]]
        if dignity:
            parts.append(dignity)
        if p.get("retrograde"):
            parts.append("retrograde")
        parts.append(f"house {p['house']}")
        lines.append(f"  {p['name']}: {', '.join(parts)}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Reading prompt
# ─────────────────────────────────────────────────────────────────────────────

# Maps reading section name → divisional charts most relevant to it
_SECTION_CHART_GUIDE = {
    "Chart Overview":
        "Use D1: ascendant, Moon sign, nakshatra, current Dasha.",
    "Personality & Appearance":
        "Use D1: lagna lord, Moon, Sun, Ascendant degree and nakshatra.",
    "Career & Wealth":
        "Use D10 Dashamsha for career specifics; D2 Hora for financial patterns; "
        "cross-check D1 10th house and its lord.",
    "Relationships & Marriage":
        "Use D9 Navamsha: 7th house, 7th lord, Venus, Jupiter in D9. "
        "Also check D1 7th house for partnership indicators.",
    "Health":
        "Use D6 Shashthamsha: 6th house lord, malefics in D6, Saturn/Mars afflictions. "
        "Cross-check D1 6th and 8th houses.",
    "Spiritual Inclination":
        "Use D60 Shashtiamsha for past-life karma and soul patterns; "
        "D20 Vimshamsha for worship and spiritual practices; "
        "also D9 12th house for moksha tendencies.",
    "Current Period (Dasha)":
        "Use D1: current dasha lord house and sign. "
        "Cross-check the dasha lord's D9 and D10 positions for career/life themes.",
}


def build_prompt(
    chart: dict,
    dasha: dict,
    language: str,
    div_charts: Optional[dict] = None,
) -> str:
    """
    Build the full reading prompt.

    div_charts maps division number → divisional chart dict.
    D9 is always drawn from chart['navamsa_planets'] (pre-computed in astro_calc).
    All other charts are passed in from the route.
    """
    lang_instruction = "Hindi" if language == "hi" else "English"
    asc       = chart["ascendant"]
    div_charts = div_charts or {}

    moon = next((p for p in chart["planets"] if p["name"] == "Moon"), None)
    sun  = next((p for p in chart["planets"] if p["name"] == "Sun"), None)
    moon_sign = (
        f"{moon['sign']} ({moon.get('nakshatra', '')} nakshatra)" if moon else "unknown"
    )
    sun_sign = sun["sign"] if sun else "unknown"

    lines = [
        f"You are a wise, warm Vedic astrologer — like a knowledgeable friend who truly "
        f"knows this person's chart. Write the reading in {lang_instruction}. "
        f"Speak directly to the person using 'you' and 'your'. "
        f"Use plain, natural language; briefly explain any Vedic term you use. "
        f"Each section must be exactly 4–5 bullet points starting with '- '. "
        f"Each bullet: 1–2 short sentences. No long paragraphs. No academic tone.\n",

        "── D1 BIRTH CHART (Lagna — Overall Life & Personality) ──",
        f"- Ascendant (Lagna): {asc['sign']} ({asc['degree']:.1f}°, {asc['nakshatra']} nakshatra)",
        f"- Moon Sign (Rashi): {moon_sign}",
        f"- Sun Sign: {sun_sign}",
    ]

    for p in chart["planets"]:
        parts = [p["sign"]]
        dignity = get_dignity(p["name"], p["sign_index"])
        if dignity:
            parts.append(dignity)
        if p.get("retrograde"):
            parts.append("retrograde")
        parts.append(f"house {p['house']}")
        lines.append(f"- {p['name']}: {', '.join(parts)}")

    md = dasha["current_mahadasha"]
    ad = dasha.get("current_antardasha")
    if ad:
        lines.append(
            f"- Current Dasha: {md['planet']} Mahadasha → "
            f"{ad['planet']} Antardasha (ends {ad['end']})"
        )
    else:
        lines.append(f"- Current Dasha: {md['planet']} Mahadasha (ends {md['end']})")

    # ── Divisional charts (ordered by life area) ──────────────────────────

    nav_planets = chart.get("navamsa_planets", [])
    if nav_planets:
        lines.append(_format_planets(
            nav_planets,
            "── D9 NAVAMSHA (Marriage, Dharma & Spiritual Strength) ──",
        ))

    _DIV_LABELS = {
        2:  "── D2 HORA (Wealth & Financial Potential) ──",
        3:  "── D3 DREKKANA (Siblings, Courage & Short Journeys) ──",
        4:  "── D4 CHATURTHAMSHA (Property, Home & Fixed Assets) ──",
        6:  "── D6 SHASHTHAMSHA (Health, Enemies & Disease) ──",
        7:  "── D7 SAPTAMSHA (Children & Progeny) ──",
        10: "── D10 DASHAMSHA (Career, Profession & Public Life) ──",
        12: "── D12 DWADASHAMSHA (Parents & Ancestral Lineage) ──",
        16: "── D16 SHODASHAMSHA (Vehicles, Luxury & Comforts) ──",
        20: "── D20 VIMSHAMSHA (Spiritual Practices & Worship) ──",
        24: "── D24 CHATURVIMSHAMSHA (Education, Skills & Learning) ──",
        27: "── D27 NAKSHATRAMSHA (Physical Strength & Vitality) ──",
        30: "── D30 TRIMSHAMSHA (Misfortunes & Evils) ──",
        60: "── D60 SHASHTIAMSHA (Past-life Karma & Soul's Journey) ──",
    }
    for div_num in sorted(div_charts):
        if div_num in _DIV_LABELS:
            lines.append(_format_planets(
                div_charts[div_num]["planets"],
                _DIV_LABELS[div_num],
            ))

    # ── Section instructions ──────────────────────────────────────────────
    chart_guide = "\n".join(
        f"- '{name}': {guide}"
        for name, guide in _SECTION_CHART_GUIDE.items()
    )

    section_instructions = (
        "Return ONLY a valid JSON object (no markdown, no extra text) with this structure:\n"
        "{\n"
        + ",\n".join(
            f'  "{name}": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"]'
            for name in _SECTION_NAMES
        )
        + "\n}\n\n"
        "Rules for every bullet:\n"
        "- 1–2 short sentences max\n"
        "- 'you'/'your' — speak directly to the person\n"
        "- Plain language; explain Vedic terms briefly\n"
        "- Warm, direct, like a knowledgeable friend\n\n"
        "Which chart to use per section:\n"
        + chart_guide + "\n\n"
        f"For 'Chart Overview': first 2 bullets state Ascendant, Moon sign, "
        f"Sun sign, nakshatra, and current Dasha "
        f"({md['planet']} Mahadasha"
        + (f" → {ad['planet']} Antardasha ending {ad['end']}" if ad
           else f" ending {md['end']}")
        + "). Last 2 bullets give overall personality in plain language."
    )
    lines.append(f"\n{section_instructions}")

    return "\n".join(lines)


def parse_sections(raw: str) -> list[dict]:
    import json
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}
    sections = []
    for name in _SECTION_NAMES:
        bullets = data.get(name, [])
        if isinstance(bullets, str):
            bullets = [s.strip() for s in re.split(r'(?<=[.!?])\s+', bullets) if s.strip()]
        content = "\n".join(str(b).strip() for b in bullets if b)
        sections.append({"title": name, "icon": _SECTION_ICONS[name], "content": content})
    return sections


def _call_claude(messages: list[dict], json_mode: bool = False) -> str:
    """
    Call Claude — via OpenRouter if OPENROUTER_API_KEY is set, otherwise
    directly via the Anthropic SDK using ANTHROPIC_API_KEY.
    Raises ValueError if neither key is set, or any exception on API error.
    """
    openrouter_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if openrouter_key:
        return _call_claude_via_openrouter(messages, openrouter_key, json_mode)

    import anthropic as _anthropic
    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("Neither OPENROUTER_API_KEY nor ANTHROPIC_API_KEY is set")
    client = _anthropic.Anthropic(api_key=api_key)
    kwargs: dict = {
        "model": _CLAUDE_MODEL,
        "max_tokens": 4096,
        "messages": messages,
    }
    if json_mode:
        # Instruct Claude to return only JSON via output_config
        kwargs["output_config"] = {"format": {"type": "json_object"}}
    resp = client.messages.create(**kwargs)
    for block in resp.content:
        if block.type == "text":
            return block.text
    return ""


def _call_claude_via_openrouter(
    messages: list[dict],
    api_key: str,
    json_mode: bool = False,
) -> str:
    """
    Call Claude via OpenRouter. Raises RuntimeError (not HTTPException) on
    any failure so _call_llm's fallback to Groq always triggers correctly.
    Credit exhaustion (402/403) is logged explicitly before raising.
    """
    payload: dict = {"model": _OPENROUTER_MODEL, "messages": messages, "max_tokens": 4096}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://starjyotish.app"),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "Star Jyotish"),
            },
            json=payload,
            timeout=60,
        )
        if resp.status_code in (402, 403):
            # 402 = insufficient credits, 403 = forbidden (bad key / model access)
            try:
                detail = resp.json().get("error", {}).get("message", resp.text[:200])
            except Exception:
                detail = resp.text[:200]
            logger.warning(
                "OpenRouter %s — %s. Falling back to Groq.",
                resp.status_code,
                detail,
            )
            raise RuntimeError(f"OpenRouter {resp.status_code}: {detail}")
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except RuntimeError:
        raise  # re-raise our own RuntimeError unchanged
    except Exception as exc:
        logger.warning("OpenRouter request failed (%s: %s). Falling back to Groq.", type(exc).__name__, exc)
        raise RuntimeError(f"OpenRouter error: {exc}") from exc


def _call_groq(
    messages: list[dict],
    json_mode: bool = False,
    retries: int = 3,
) -> str:
    """Call Groq/Llama API with retry on 429."""
    import time
    api_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured")
    payload: dict = {"model": _GROQ_MODEL, "messages": messages}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(retries):
        try:
            resp = requests.post(
                _GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            if resp.status_code == 429:
                last_exc = RuntimeError(f"rate limited (HTTP 429) after {attempt + 1}/{retries} attempts")
                logger.warning("Groq rate limited (attempt %d/%d), retrying…", attempt + 1, retries)
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except HTTPException:
            raise
        except Exception as exc:
            last_exc = exc
            logger.warning("Groq attempt %d/%d failed: %s: %s", attempt + 1, retries, type(exc).__name__, exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise HTTPException(status_code=503, detail=f"Groq API error: {last_exc}") from last_exc


def _call_llm(messages: list[dict], json_mode: bool = False) -> tuple[str, str]:
    """
    Primary: Claude (claude-sonnet-4-6), via OpenRouter if OPENROUTER_API_KEY
    is set, else directly via ANTHROPIC_API_KEY.
    Fallback: Groq/Llama when neither key is set or Claude returns an error.
    Returns (text, provider_label) — provider_label reflects whichever one
    actually served this specific request, since the fallback can kick in
    silently and a hardcoded "Powered by Claude" in the UI would be wrong
    whenever that happens.
    """
    claude_reason = None
    try:
        return _call_claude(messages, json_mode), "Claude"
    except ValueError as exc:
        claude_reason = str(exc)  # e.g. "Neither OPENROUTER_API_KEY nor ANTHROPIC_API_KEY is set"
    except Exception as exc:
        claude_reason = f"{type(exc).__name__}: {exc}"
        logger.warning("Claude API error (%s), falling back to Groq", exc)

    try:
        return _call_groq(messages, json_mode), "Groq · Llama"
    except HTTPException as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI unavailable — Claude: {claude_reason}; Groq: {exc.detail}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI unavailable — Claude: {claude_reason}; Groq: {exc}",
        ) from exc


_PREDICTION_BANNED = [
    "debilitated", "weak", "enemy sign", "afflicted", "challenging",
    "malefic", "difficult placement", "combust", "fallen", "neecha",
    "6th house", "8th house", "12th house", "bad", "struggle",
    "obstacle", "problem", "inauspicious",
]


def clean_prediction(text: str) -> str:
    """Remove any sentence containing banned jargon / negative terms."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = [
        s for s in sentences
        if not any(w.lower() in s.lower() for w in _PREDICTION_BANNED)
    ]
    return ' '.join(cleaned)


def build_prediction_prompt(
    chart: dict,
    dasha: dict,
    language: str,
    active_yogas: Optional[list] = None,
    focus_topic: Optional[str] = None,
) -> str:
    """Build the Jyotish Guru genuine-value free prediction prompt."""
    asc = chart["ascendant"]
    planets = chart["planets"]
    active_yogas = active_yogas or []
    current_year = 2026

    moon = next((p for p in planets if p["name"] == "Moon"), None)
    sun  = next((p for p in planets if p["name"] == "Sun"), None)
    moon_sign = (
        f"{moon['sign']} ({moon.get('nakshatra', '')} nakshatra)" if moon else "unknown"
    )
    sun_sign = sun["sign"] if sun else "unknown"

    planet_lines = []
    for p in planets:
        dignity = get_dignity(p["name"], p["sign_index"])
        retro = " (R)" if p.get("retrograde") else ""
        line = f"  {p['name']}{retro}: {p['sign']} H{p['house']}"
        if dignity:
            line += f" — {dignity}"
        planet_lines.append(line)

    md = dasha.get("current_mahadasha") or {}
    ad = dasha.get("current_antardasha") or {}
    full_seq = dasha.get("full_sequence") or []

    next_dasha_str = "an upcoming powerful period"
    for entry in full_seq:
        start_str = str(entry.get("start", ""))
        try:
            start_year = int(start_str[:4])
        except (ValueError, IndexError):
            start_year = 0
        if start_year > current_year and entry.get("planet") != md.get("planet"):
            next_dasha_str = f"{entry['planet']} period beginning {start_str[:7]}"
            break

    yoga_summary = "\n".join(
        f"  - {y['name']}: {y.get('description', '')}"
        for y in active_yogas
    ) or "  (identify from planetary dignities and house placements — look for Panch Mahapurusha yogas, Gaja Kesari, Budh Aditya, Chandra Mangal, Neecha Bhanga, Viparita Raj, etc.)"

    # Small, remedy-free reference excerpt (house meanings, planet dignities,
    # nakshatra lords) for interpretive accuracy. Deliberately excludes the
    # remedies section below it — see "KEEP LOCKED" rules further down.
    from services.skill_loader import get_kundli_interpretation_tables
    reference_tables = get_kundli_interpretation_tables()
    reference_block = (
        f"\n═══════════════════════════════════\n"
        f"REFERENCE (for interpretive accuracy — do not quote verbatim, do not mention remedies):\n"
        f"═══════════════════════════════════\n{reference_tables}\n"
    ) if reference_tables else ""

    lang_note = (
        "LANGUAGE RULE — NON-NEGOTIABLE: Write EVERY SINGLE WORD in Hindi (Devanagari script). "
        "This includes all section content, yoga names (translate them to Hindi), "
        "timeline descriptions, character descriptions, bullet points, and all closing messages. "
        "Do NOT write any English words anywhere in your output — pure Hindi only."
    ) if language == "hi" else (
        "LANGUAGE RULE: Write entirely in English. Every word must be in English."
    )
    ad_line = f"\n  Sub-period: {ad.get('planet', '')} (ends {ad.get('end', '')})" if ad else ""

    _TOPIC_FOCUS = {
        "career":       "career, profession, business, and professional growth",
        "relationship": "marriage, partnership, and relationship compatibility",
        "health":       "health, vitality, and general wellbeing",
        "finance":      "wealth, financial stability, and prosperity",
    }
    topic_note = (
        f"\nFOCUS: This person came here specifically with {_TOPIC_FOCUS[focus_topic]} on their mind. "
        f"Give that area noticeably more depth and concrete detail than the others — lead with it where "
        f"natural — but still cover every section; don't drop or shortchange the rest of the reading.\n"
        if focus_topic in _TOPIC_FOCUS else ""
    )

    return f"""You are Jyotish Guru — a master Vedic astrologer giving a genuine, warm, and deeply insightful FREE career reading to someone who just shared their birth details for the first time.

Your job is to give REAL VALUE — actual chart findings, real yoga names, genuine predictions — so the person feels: "This is accurate. This person truly knows my chart. I need the full report."

{lang_note}
{topic_note}
═══════════════════════════════════
CHART DATA (use this as your basis):
═══════════════════════════════════
  Ascendant (Lagna): {asc.get('sign', '?')} ({asc.get('degree', 0):.1f}°, {asc.get('nakshatra', '')} nakshatra)
  Moon Sign: {moon_sign}
  Sun Sign : {sun_sign}

Planets:
{chr(10).join(planet_lines)}

  Current life period: {md.get('planet', '?')} (ends {md.get('end', '?')}){ad_line}
  Upcoming period: {next_dasha_str}

Raj Yogas detected:
{yoga_summary}
{reference_block}
═══════════════════════════════════
ABSOLUTE RULES — NEVER BREAK:
═══════════════════════════════════
✗ NEVER say: "10th lord", "D10", "Mahadasha" (say "life period" instead), "debilitated", "enemy sign", "afflicted", "combust", "neecha", or any house number
✓ Translate Sanskrit → plain English on first use. Format:
  "Gaja Kesari Yoga — what Vedic astrologers call the Wisdom-Power Combination — is present in your chart."
✓ Speak directly: YOU, YOUR, YOU ARE — every 2 sentences minimum
✓ Warm mentor tone — like someone who deeply believes in this person

GIVE FREE (real diagnosis, real findings):
✓ Name REAL Raj Yogas by Sanskrit name + plain translation + what they actually produce
✓ Give REAL career direction based on dominant planet
✓ Name the current life period lord — say something genuinely positive about it
✓ Give a genuine specific positive prediction for the next 2-3 years

KEEP LOCKED (the treatment plan = paid report):
✗ No gemstone, mantra, activation ritual, or remedy details
✗ No Mahadasha dates or action plan for each period
✗ No Job vs Business answer — save for paid report
✗ No D10 / Dasamsa analysis — save for paid report

═══════════════════════════════════
OUTPUT FORMAT — WRAP EACH SECTION IN THESE EXACT TAGS:
═══════════════════════════════════

<identity>
4-5 sentences. Open by naming their Lagna sign and what it specifically means for professional personality (be precise — not generic). Example for Aries rising: "You were born under Aries rising — the Lagna of pioneers, initiators, and people who are meant to START things, not maintain them. Your professional energy is fastest at the beginning of projects, in new ventures, in roles where someone needs to take the first bold step." Then 1-2 sentences about their Moon sign and what emotional energy drives their work and ambition. End with exactly: "That quiet inner sense that you are meant for something significant — that is not ego. That is your chart speaking."
</identity>

<strengths>
4-5 sentences. Based on the dominant planet (strongest dignity or career karaka position): name the planet and its natural career domain in plain language. Example: "Your chart is strongly influenced by Saturn — the planet of discipline, systems, and long-term building. This makes you naturally suited to careers that reward patience, structure, and reliability: engineering, law, administration, finance, or any field where serious people do serious work." Then add 1-2 sentences about a specific hidden professional strength from this planet's placement (translate to plain language — no house numbers).
</strengths>

<currentperiod>
3-4 sentences. Name the current life period lord ({md.get('planet', '?')}). Give a genuinely positive reading of what this period is building toward. Do NOT give dates or action plan. Example: "You are currently in your Saturn life period — a time when the universe is asking you to build foundations that will last. The work you do now — quietly, seriously, without immediate applause — is exactly what this period is designed to produce."
</currentperiod>

<prediction>
4-5 sentences. Genuine specific positive prediction based on upcoming transits and sub-period ({ad.get('planet', '?')} sub-period, next period: {next_dasha_str}). Structure: what energy is building (specific, based on planets) → what kind of opportunity or recognition is likely → what they should be doing right now to prepare → one genuinely exciting statement about what is possible.
</prediction>

<health>
4-5 sentences STRICTLY POSITIVE. Based on Moon sign ({moon_sign}), Sun placement, and ascendant ({asc.get('sign', '?')}): describe what this person's constitution naturally excels at and their inherent vitality strengths. Then give a specific positive prediction about health energy in the next 2 years — when they will feel strongest, most energetic, most vital. NEVER use any negative health words or warnings. Use language like "your constitution is built for...", "your body naturally responds well to...", "the period ahead brings renewed vitality and..." End with one uplifting sentence about the excellent health energy coming in the years ahead.
</health>

<relationships>
4-5 sentences STRICTLY POSITIVE. Based on Moon sign and Venus placement: describe what makes this person naturally magnetic and what unique warmth or depth they bring to relationships. Then give a specific positive prediction about relationships and social connections in the next 2 years — when connection energy peaks, what kind of meaningful relationship or deep friendship is entering their life. NEVER use any negative relationship words. Use "your capacity for love...", "the relationships you attract...", "the coming period brings deeply fulfilling connections..." End with a warm, uplifting sentence about the beautiful relationships ahead in their life.
</relationships>

<bridge>
3 sentences exactly. "Your chart holds answers to questions your full report will address in complete detail: exactly which career field your chart analysis points to, whether your chart favors building a business or excelling in a career role, and the single most powerful remedy — specific to your chart, not generic advice — that can accelerate everything above. These are not small questions. They are the questions whose answers, once known, change how you make every career decision going forward."
</bridge>

<teasers>
{{
  "teaser1": "Activation Ritual for Your [Yoga Name/s — use plain translation]",
  "teaser2": "Your Peak Career Window: [year range from period analysis]",
  "teaser3": "Job or Business? What Your Chart Actually Says"
}}
</teasers>

TOTAL LENGTH: 500-560 words across all 7 sections. Every sentence must feel specific to THIS chart, not a template.
"""


_PREDICTION_SECTIONS = ['identity', 'strengths', 'currentperiod', 'prediction', 'health', 'relationships', 'bridge']


def parse_prediction(raw: str) -> tuple[dict, dict]:
    """Parse the prediction response into (sections_dict, teasers_dict)."""
    import json as _json

    # Extract teasers
    teasers: dict = {}
    teaser_match = re.search(r'<teasers>(.*?)</teasers>', raw, re.DOTALL)
    if teaser_match:
        try:
            teasers = _json.loads(teaser_match.group(1).strip())
        except Exception:
            pass

    # Extract named sections
    sections: dict = {}
    for name in _PREDICTION_SECTIONS:
        m = re.search(rf'<{name}>(.*?)</{name}>', raw, re.DOTALL)
        if m:
            sections[name] = clean_prediction(m.group(1).strip())

    # Fallback: paragraph split if no tags found
    if not sections:
        cleaned = clean_prediction(raw)
        paras = [p.strip() for p in re.split(r'\n{2,}', cleaned) if p.strip()]
        for i, name in enumerate(_PREDICTION_SECTIONS):
            if i < len(paras):
                sections[name] = paras[i]

    return sections, teasers


def generate_reading(
    chart: dict,
    dasha: dict,
    language: str,
    div_charts: Optional[dict] = None,
    active_yogas: Optional[list] = None,
    focus_topic: Optional[str] = None,
) -> dict:
    """
    Generate the free Jyotish Guru prediction.
    Returns dict with keys: sections, prediction_text, prediction_sections, teasers.
    """
    prompt = build_prediction_prompt(chart, dasha, language, active_yogas, focus_topic)
    try:
        raw, provider = _call_llm([{"role": "user", "content": prompt}], json_mode=False)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM error: {exc}") from exc

    pred_sections, teasers = parse_prediction(raw)
    prediction_text = "\n\n".join(pred_sections.values())

    return {
        "sections": [],
        "prediction_text": prediction_text,
        "prediction_sections": pred_sections,
        "teasers": teasers,
        "llm_provider": provider,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Ask prompt
# ─────────────────────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────────────────────
# Chart Highlight — per-chart AI insight (2-3 sentences, light/quick)
# ─────────────────────────────────────────────────────────────────────────────

_CHART_HIGHLIGHT_META = {
    "D1":  ("Lagna Chart (D1)",       "overall personality, health, and life path"),
    "D2":  ("Hora Chart (D2)",        "wealth accumulation, income sources, and financial karma"),
    "D3":  ("Drekkana Chart (D3)",    "courage, siblings, communication, and short journeys"),
    "D4":  ("Chaturthamsha (D4)",     "fixed assets, home, property, and general fortune"),
    "D6":  ("Shashthamsha (D6)",      "health, immunity, service, and enemies"),
    "D7":  ("Saptamsha (D7)",         "children, creativity, and progeny"),
    "D9":  ("Navamsha Chart (D9)",    "marriage, dharma, deeper soul purpose, and post-30 life"),
    "D10": ("Dashamsha Chart (D10)",  "career, profession, public reputation, and ambition"),
    "D12": ("Dwadashamsha (D12)",     "parents, ancestral karma, and lineage"),
    "D16": ("Shodashamsha (D16)",     "vehicles, comforts, and material pleasures"),
    "D20": ("Vimshamsha (D20)",       "spiritual progress and religious inclinations"),
    "D24": ("Siddhamsha (D24)",       "education, learning, and intellectual capacity"),
    "D27": ("Nakshatramsha (D27)",    "physical strength, vitality, and fighting spirit"),
    "D30": ("Trimshamsha (D30)",      "misfortunes, chronic issues, and karmic debts"),
    "D40": ("Khavedamsha (D40)",      "auspicious and inauspicious patterns from the mother's lineage"),
    "D45": ("Akshavedamsha (D45)",    "general well-being and character"),
    "D60": ("Shashtiamsha (D60)",     "past-life karma and deep soul imprints"),
}


def generate_chart_highlight(
    chart: dict,
    chart_type: str,
    language: str = "en",
) -> tuple[str, str]:
    """
    Generate a 2-3 sentence insight for a specific divisional chart.
    chart_type: "D1", "D9", "D10", etc.
    Returns (highlight_text, provider_label).
    """
    meta = _CHART_HIGHLIGHT_META.get(chart_type, (chart_type, "this area of your life"))
    chart_name, life_area = meta

    asc = chart.get("ascendant", {})
    planets = chart.get("planets", [])

    # Build a concise planet summary for the prompt
    planet_lines = []
    for p in planets:
        if not p.get("name"):
            continue
        dignity = ""
        sign_idx = p.get("sign_index", -1)
        pname = p.get("name", "")
        exalted_signs = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
        debil_signs   = {"Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0}
        if exalted_signs.get(pname) == sign_idx:
            dignity = " (Exalted)"
        elif debil_signs.get(pname) == sign_idx:
            dignity = " (Debilitated)"
        planet_lines.append(f"  {pname} in {p.get('sign','?')} H{p.get('house','?')}{dignity}")

    planet_summary = "\n".join(planet_lines[:10]) if planet_lines else "  (no planet data)"

    lang_instruction = (
        "Respond in Hindi (Devanagari script)." if language.startswith("hi")
        else "Respond in clear, warm English."
    )

    prompt = f"""You are Jyotish Guru, a wise and encouraging Vedic astrology guide on Star Jyotish.

A user is viewing their {chart_name}, which reveals {life_area}.

Chart ascendant: {asc.get("sign", "Unknown")} ({asc.get("degree", 0):.1f}°)
Key planets in this chart:
{planet_summary}

Write exactly 2-3 sentences that:
1. Identify the single most important pattern or standout placement in this specific chart
2. Explain what it means for the user in plain, non-jargon language about {life_area}
3. End with one gentle, actionable or hopeful note

Rules:
- No bullet points. Pure flowing prose.
- Warm, personal, second-person ("your chart shows…", "you carry…")
- Never use the words: debilitated, weak, afflicted, malefic, neecha, fallen, bad, difficult, 6th house, 8th house, 12th house
- Keep under 80 words total
- {lang_instruction}"""

    text, provider = _call_llm([{"role": "user", "content": prompt}])
    return text.strip(), provider

def ask_chart(
    chart: dict,
    dasha: dict,
    question: str,
    language: str,
    transit: Optional[dict] = None,
    conversation_history: Optional[list[dict]] = None,
    user_memory: Optional[str] = None,
) -> tuple[str, str]:
    """
    Answer a kundli question using the full available chart context.
    Returns (answer, provider_label) — see _call_llm for why the provider
    needs to be tracked per-request rather than assumed.

    conversation_history: prior {question, answer} turns in this same
    session (see services/ask_sessions.py), oldest first. Lets the model
    correlate a follow-up like "and what about marriage timing?" with what
    was actually asked/answered before, instead of treating every question
    as if it arrived with no context. Empty/None for the first question of
    a session — handled the same as "no history" below, not as an error.

    user_memory: the signed-in user's rolling distilled memory from
    previous conversations (see services/user_memory.py) — what they've
    shared about their life, not chart facts. None for anonymous callers
    or a first-ever conversation.

    Chart data passed in (from the route):
      chart['planets']          — D1 placements
      chart['navamsa_planets']  — D9 placements (always)
      chart['divisional_chart'] — primary topic-specific chart (auto-detected)
      chart['div_charts']       — dict of all pre-calculated divisional charts
                                  {div_num: {planets: [...], ascendant: {...}}}
      transit                   — current transit positions from calculate_transit()
                                  {transit_date, transit_planets, natal_asc_sign_index}

    Skill knowledge is loaded from astro-skills/ and cross-references are
    resolved per index.md's "Skill Compatibility" table.
    """
    lang_instruction = "Hindi" if language == "hi" else "English"
    asc  = chart["ascendant"]
    moon = next((p for p in chart["planets"] if p["name"] == "Moon"), None)
    md   = dasha["current_mahadasha"]
    ad   = dasha.get("current_antardasha")

    # Primary divisional chart detected for this question
    division = _detect_division(question)
    div_name = _DIVISION_NAMES.get(division, f"D{division}")

    # ── Chart context ─────────────────────────────────────────────────────

    d1_text = _format_planets(chart["planets"], "D1 Birth Chart (Overall Life)")

    nav_planets = chart.get("navamsa_planets", [])
    d9_text = (
        _format_planets(nav_planets, "D9 Navamsha (Marriage & Dharma)")
        if nav_planets else ""
    )

    # All pre-calculated divisional charts beyond D1/D9
    extra_div_parts = []
    seen_divs = {1, 9}

    # Primary detected chart (may have been pre-calculated by route)
    primary_div_data = chart.get("divisional_chart", {})
    if primary_div_data and division not in seen_divs:
        extra_div_parts.append(
            _format_planets(primary_div_data.get("planets", []), div_name)
        )
        seen_divs.add(division)

    # Any additional pre-calculated charts stored in chart['div_charts']
    for div_num, div_data in sorted(chart.get("div_charts", {}).items()):
        if div_num not in seen_divs and div_data.get("planets"):
            label = _DIVISION_NAMES.get(div_num, f"D{div_num}")
            extra_div_parts.append(
                _format_planets(div_data["planets"], label)
            )
            seen_divs.add(div_num)

    extra_div_text = "".join(extra_div_parts)

    # ── Transit positions (when question is transit-related) ──────────────
    transit_text = ""
    q_lower_transit = question.lower()
    if transit and any(kw in q_lower_transit for kw in _TRANSIT_KEYWORDS):
        transit_planets = transit.get("transit_planets", [])
        if transit_planets:
            transit_text = _format_planets(
                transit_planets,
                f"CURRENT TRANSIT POSITIONS (as of {transit.get('transit_date', 'today')})",
            )

    # ── Skill knowledge ───────────────────────────────────────────────────
    skill_text = _load_skill_content(question)

    # ── Assemble prompt ───────────────────────────────────────────────────
    charts_listed = ", ".join(
        _DIVISION_NAMES.get(d, f"D{d}").split(" ")[0]
        for d in sorted(seen_divs)
    )
    if transit_text:
        charts_listed += ", Transit"

    # ── Long-term memory (signed-in users only) ────────────────────────────
    memory_text = ""
    if user_memory:
        memory_text = (
            f"\n\nWHAT YOU REMEMBER ABOUT THIS PERSON (from earlier "
            f"conversations — weave it in naturally where relevant, e.g. "
            f"connect today's answer to a concern they raised before; never "
            f"recite this list back, and never claim to remember anything "
            f"not written here):\n{user_memory}\n"
        )

    # ── Prior conversation turns (if any) ──────────────────────────────────
    history_text = ""
    if conversation_history:
        turns = "\n".join(
            f"Q{i+1}: {turn['question']}\nA{i+1}: {turn['answer']}"
            for i, turn in enumerate(conversation_history)
        )
        history_text = (
            f"\n\nEARLIER IN THIS CONVERSATION (for context — the person may "
            f"be following up on one of these, e.g. \"what about X instead\" "
            f"or \"why is that\"; don't repeat an earlier answer verbatim, "
            f"build on it):\n{turns}\n"
        )

    prompt = (
        f"You are an expert Vedic astrologer. Answer the following question "
        f"in {lang_instruction}. "
        f"Use ALL chart data provided below ({charts_listed}). "
        f"The primary chart for this question is: {div_name}. "
        f"Keep your answer to 4-6 sentences. Be warm, specific, and direct. "
        f"Speak to the person using 'you' and 'your'. "
        f"If the question is unrelated to astrology, say: "
        f"'I can only answer questions about your birth chart and Vedic astrology.'\n\n"
        f"BIRTH DETAILS:\n"
        f"Ascendant: {asc['sign']} ({asc.get('nakshatra', '')} nakshatra)\n"
        f"Moon sign: {moon['sign'] if moon else 'unknown'}\n"
        f"Current Dasha: {md['planet']} Mahadasha"
        + (f" → {ad['planet']} Antardasha" if ad else "")
        + f"\n"
        + d1_text
        + d9_text
        + extra_div_text
        + transit_text
        + skill_text
        + memory_text
        + history_text
        + f"\n\nQUESTION: {question}"
    )

    try:
        answer, provider = _call_llm([{"role": "user", "content": prompt}])
        return answer.strip(), provider
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM error: {exc}") from exc
