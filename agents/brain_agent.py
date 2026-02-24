import json
import re
from difflib import get_close_matches
from services.llm import ask_llm
from data.mumbai_routes import get_all_locations

SYSTEM_PROMPT = """
You are an autonomous mobility planning agent.

Return ONLY valid JSON.

Allowed actions:
- plan
- update_preferences
- replan
- edit_leg
- clear_leg_override
- avoid_mode_on_leg
- explain

Schema:

{
 "action": "...",
 "avoid_modes": [],
 "from_location": "",
 "to_location": "",
 "transport_mode": "",
 "reason": ""
}

Examples:

User: plan my day
Output:
{"action":"plan"}

User: I hate buses
Output:
{"action":"update_preferences","avoid_modes":["bus"]}

User: I don't wanna take the train in the bandra to cst route
Output:
{"action":"avoid_mode_on_leg","from_location":"Bandra","to_location":"CST","avoid_modes":["train"],"reason":"user preference"}

User: use metro from Andheri to BKC
Output:
{"action":"edit_leg","from_location":"Andheri","to_location":"BKC","transport_mode":"metro","reason":"user prefers scenic metro route"}

User: clear override from Andheri to BKC
Output:
{"action":"clear_leg_override","from_location":"Andheri","to_location":"BKC"}

User: replan
Output:
{"action":"replan"}

User: why this route?
Output:
{"action":"explain"}
"""



KNOWN_MODES = ["cab", "metro", "train", "bus"]
LOCATION_ALIASES = {
    "bkc": "BKC",
    "cst": "CST",
    "csmt": "CST",
    "csv": "CST",
}


def _build_location_token_map():
    token_map = {k.lower(): v for k, v in LOCATION_ALIASES.items()}
    for location in get_all_locations():
        token_map[location.lower()] = location
    return token_map


LOCATION_TOKEN_MAP = _build_location_token_map()


def _canonicalize_location(raw: str):
    if not raw:
        return None

    value = raw.strip().lower()
    value = re.sub(r"[^a-z\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    if value in LOCATION_ALIASES:
        return LOCATION_ALIASES[value]

    locations = get_all_locations()
    loc_map = {loc.lower(): loc for loc in locations}

    if value in loc_map:
        return loc_map[value]

    match = get_close_matches(value, list(loc_map.keys()), n=1, cutoff=0.75)
    if match:
        return loc_map[match[0]]

    return None


def _extract_leg(text: str):
    def canonical_pair(from_raw: str, to_raw: str):
        from_loc = _canonicalize_location(from_raw)
        to_loc = _canonicalize_location(to_raw)
        return from_loc, to_loc

    # Highest-confidence parse: explicit "from X to Y"
    explicit = re.search(r"\bfrom\s+([a-z\s]+?)\s+to\s+([a-z\s]+)", text)
    if explicit:
        from_loc, to_loc = canonical_pair(explicit.group(1).strip(), explicit.group(2).strip())
        if from_loc and to_loc:
            return from_loc, to_loc

    normalized = re.sub(r"[^a-z\s]", " ", text.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    mentions = []
    for token, canonical in sorted(LOCATION_TOKEN_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        pattern = rf"\b{re.escape(token)}\b"
        for m in re.finditer(pattern, normalized):
            mentions.append((m.start(), m.end(), canonical))

    if not mentions:
        return None, None

    mentions.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    filtered = []
    for start, end, canonical in mentions:
        if filtered and start < filtered[-1][1]:
            continue
        filtered.append((start, end, canonical))

    if len(filtered) < 2:
        return None, None

    to_match = re.search(r"\bto\b", normalized)
    if to_match:
        to_idx = to_match.start()
        before = [m for m in filtered if m[0] < to_idx]
        after = [m for m in filtered if m[0] > to_idx]
        if before and after:
            return before[-1][2], after[0][2]

    return filtered[0][2], filtered[1][2]


def _extract_mode(text: str):
    for mode in KNOWN_MODES:
        if re.search(rf"\b{re.escape(mode)}\b", text):
            return mode
    if "taxi" in text:
        return "cab"
    if "uber" in text or "ola" in text:
        return "cab"
    return None


def _fallback_decision(user_message: str):
    text = (user_message or "").lower()
    from_loc, to_loc = _extract_leg(text)
    mode = _extract_mode(text)

    avoid_markers = ["avoid", "don't", "dont", "do not", "no ", "not use", "not take"]

    if from_loc and to_loc and mode and any(k in text for k in avoid_markers):
        return {
            "action": "avoid_mode_on_leg",
            "from_location": from_loc,
            "to_location": to_loc,
            "avoid_modes": [mode],
            "reason": "fallback_rule"
        }

    if from_loc and to_loc and mode:
        return {
            "action": "edit_leg",
            "from_location": from_loc,
            "to_location": to_loc,
            "transport_mode": mode,
            "reason": "fallback_rule"
        }

    if "replan" in text:
        return {"action": "replan", "reason": "fallback_rule"}

    if "why" in text or "explain" in text:
        return {"action": "explain", "reason": "fallback_rule"}

    if "avoid" in text and "bus" in text:
        return {
            "action": "update_preferences",
            "avoid_modes": ["bus"],
            "reason": "fallback_rule"
        }

    return {"action": "plan", "reason": "fallback_rule"}


def _rule_based_override_decision(user_message: str):
    text = (user_message or "").lower()
    from_loc, to_loc = _extract_leg(text)
    mode = _extract_mode(text)

    if not (from_loc and to_loc):
        return None

    avoid_markers = ["avoid", "don't", "dont", "do not", "not use", "not take", "no "]
    if mode and any(k in text for k in avoid_markers):
        return {
            "action": "avoid_mode_on_leg",
            "from_location": from_loc,
            "to_location": to_loc,
            "avoid_modes": [mode],
            "reason": "rule_override"
        }

    if mode and any(k in text for k in ["use", "take", "via", "by", "want", "wanna", "prefer"]):
        return {
            "action": "edit_leg",
            "from_location": from_loc,
            "to_location": to_loc,
            "transport_mode": mode,
            "reason": "rule_override"
        }

    return None


def think(user_message):
    # Deterministic override for explicit leg-level instructions to avoid
    # accidental "plan" responses from the LLM.
    forced = _rule_based_override_decision(user_message)
    if forced is not None:
        return forced

    try:
        reply = ask_llm(SYSTEM_PROMPT, user_message)

        start = reply.find("{")
        end = reply.rfind("}") + 1
        if start == -1 or end <= start:
            return _fallback_decision(user_message)

        return json.loads(reply[start:end])
    except Exception:
        return _fallback_decision(user_message)
