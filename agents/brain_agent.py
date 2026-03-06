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
- clear_leg_preference
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

User: can you plan my schedule for today?
Output:
{"action":"plan"}

User: let's get the route sorted
Output:
{"action":"plan"}

User: I hate buses
Output:
{"action":"update_preferences","avoid_modes":["bus"]}

User: no trains for me today
Output:
{"action":"update_preferences","avoid_modes":["train"],"reason":"user dislikes trains"}

User: I'd rather not take the metro at all
Output:
{"action":"update_preferences","avoid_modes":["metro"],"reason":"user wants to avoid metro globally"}

User: I don't wanna take the train in the bandra to cst route
Output:
{"action":"avoid_mode_on_leg","from_location":"Bandra","to_location":"CST","avoid_modes":["train"],"reason":"user preference"}

User: skip the bus between Powai and BKC
Output:
{"action":"avoid_mode_on_leg","from_location":"Powai","to_location":"BKC","avoid_modes":["bus"],"reason":"user wants to avoid bus on this leg"}

User: no metro on the Andheri to Dadar stretch please
Output:
{"action":"avoid_mode_on_leg","from_location":"Andheri","to_location":"Dadar","avoid_modes":["metro"],"reason":"user preference for this leg"}

User: use metro from Andheri to BKC
Output:
{"action":"edit_leg","from_location":"Andheri","to_location":"BKC","transport_mode":"metro","reason":"user prefers metro"}

User: I want to take a cab from BKC to Bandra
Output:
{"action":"edit_leg","from_location":"BKC","to_location":"Bandra","transport_mode":"cab","reason":"user wants cab for this leg"}

User: switch the Powai to BKC leg to bus
Output:
{"action":"edit_leg","from_location":"Powai","to_location":"BKC","transport_mode":"bus","reason":"user requested mode change"}

User: can we do train from Dadar to CST instead?
Output:
{"action":"edit_leg","from_location":"Dadar","to_location":"CST","transport_mode":"train","reason":"user prefers train for this leg"}

User: clear override from Andheri to BKC
Output:
{"action":"clear_leg_override","from_location":"Andheri","to_location":"BKC"}

User: remove the leg preference for BKC to Bandra
Output:
{"action":"clear_leg_override","from_location":"BKC","to_location":"Bandra"}

User: can you remove powai to bkc preference?
Output:
{"action":"clear_leg_preference","from_location":"Powai","to_location":"BKC"}

User: clear all preferences for BKC to Bandra
Output:
{"action":"clear_leg_preference","from_location":"BKC","to_location":"Bandra"}

User: reset the powai to bkc leg
Output:
{"action":"clear_leg_preference","from_location":"Powai","to_location":"BKC"}

User: replan
Output:
{"action":"replan"}

User: can you replan my day?
Output:
{"action":"replan"}

User: redo the route please
Output:
{"action":"replan"}

User: recalculate everything
Output:
{"action":"replan"}

User: why this route?
Output:
{"action":"explain"}

User: can you explain the plan?
Output:
{"action":"explain"}

User: what's the reasoning behind these choices?
Output:
{"action":"explain"}

User: are we using a cab from Powai to BKC?
Output:
{"action":"explain"}

User: is it taking metro from Andheri to BKC?
Output:
{"action":"explain"}

User: which mode is the BKC to Bandra leg using?
Output:
{"action":"explain"}

User: what are we using to go from Powai to BKC?
Output:
{"action":"explain"}

User: how are we getting from Andheri to Dadar?
Output:
{"action":"explain"}

Important behavior rules:
- If the user clearly specifies a leg with a preferred mode (e.g. "from X to Y by cab", "switch the X to Y leg to bus"), return action="edit_leg".
- If the user clearly specifies a leg with a mode to avoid (e.g. "don't take train from X to Y", "skip bus between X and Y"), return action="avoid_mode_on_leg".
- If the user asks to redo, recalculate, or replan the route without specifying a leg, return action="replan".
- If the user expresses a global dislike for a mode without mentioning specific locations, return action="update_preferences".
- If the user asks to remove, clear, or reset preferences/constraints for a specific leg (e.g. "remove powai to bkc preference", "clear the bkc to bandra constraint", "reset the leg from X to Y"), return action="clear_leg_preference".
- Do NOT return "plan" for these explicit leg-level instructions.
- If the user is ASKING a question about the current route (e.g. "are we using cab?", "is it taking metro?", "which mode?"), return action="explain". Do NOT treat questions as commands.
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


def _is_question(text: str):
    """Return True if the text is an interrogative question about the current route,
    not a command to change it."""
    t = text.strip().lower()

    # Must end with a question mark
    if not t.endswith("?"):
        return False

    # Broad interrogative starters (covers virtually all English question forms)
    question_patterns = [
        # wh-words
        r"^what\b", r"^which\b", r"^where\b", r"^when\b", r"^who\b", r"^why\b",
        r"^how\b",
        # auxiliary / modal inversions
        r"^is\b", r"^are\b", r"^was\b", r"^were\b",
        r"^do\b", r"^does\b", r"^did\b",
        r"^can\b", r"^could\b", r"^will\b", r"^would\b",
        r"^shall\b", r"^should\b", r"^may\b", r"^might\b",
        r"^am\b", r"^have\b", r"^has\b", r"^had\b",
    ]

    return any(re.search(p, t) for p in question_patterns)


def _detect_global_preference(user_message: str):
    text = (user_message or "").lower()
    mode = _extract_mode(text)
    if not mode:
        return None

    from_loc, to_loc = _extract_leg(text)
    if from_loc and to_loc:
        return None

    avoid_markers = ["avoid", "don't", "dont", "do not", "not use", "not take", "no ", "hate"]
    if any(marker in text for marker in avoid_markers):
        return {
            "action": "update_preferences",
            "avoid_modes": [mode],
            "reason": "preference_guard"
        }

    return None


def _fallback_decision(user_message: str):
    text = (user_message or "").lower()
    from_loc, to_loc = _extract_leg(text)
    mode = _extract_mode(text)

    global_preference = _detect_global_preference(user_message)
    if global_preference is not None:
        return global_preference

    # Check for "clear/remove preference" before avoid markers
    clear_pref_markers = ["remove", "clear", "reset", "drop", "delete"]
    pref_target_markers = ["preference", "constraint", "override", "setting", "leg"]
    if from_loc and to_loc and not mode and any(k in text for k in clear_pref_markers) and any(k in text for k in pref_target_markers):
        return {
            "action": "clear_leg_preference",
            "from_location": from_loc,
            "to_location": to_loc,
            "reason": "fallback_rule"
        }

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
        if _is_question(text):
            return {"action": "explain", "reason": "fallback_rule"}
        return {
            "action": "edit_leg",
            "from_location": from_loc,
            "to_location": to_loc,
            "transport_mode": mode,
            "reason": "fallback_rule"
        }

    replan_markers = ["replan", "redo", "recalculate", "re-plan", "re plan", "plan again", "reoptimize"]
    if any(marker in text for marker in replan_markers):
        return {"action": "replan", "reason": "fallback_rule"}

    explain_markers = ["why", "explain", "reasoning", "how come"]
    if any(marker in text for marker in explain_markers):
        return {"action": "explain", "reason": "fallback_rule"}

    # If it looks like a question (with or without locations), don't default to plan
    if _is_question(text):
        return {"action": "explain", "reason": "fallback_rule"}

    # Plan-related keywords still get through
    plan_markers = ["plan", "schedule", "route", "get started", "let's go", "optimize"]
    if any(marker in text for marker in plan_markers):
        return {"action": "plan", "reason": "fallback_rule"}

    return {"action": "unclear", "reason": "fallback_rule"}


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
        if _is_question(text):
            return None
        return {
            "action": "edit_leg",
            "from_location": from_loc,
            "to_location": to_loc,
            "transport_mode": mode,
            "reason": "rule_override"
        }

    return None


def _normalize_decision(decision: dict):
    if not isinstance(decision, dict):
        return None

    action = (decision.get("action") or "").strip().lower()
    if not action:
        return None

    normalized = {"action": action}

    if action in ["edit_leg", "avoid_mode_on_leg", "clear_leg_override", "clear_leg_preference"]:
        from_loc = _canonicalize_location(decision.get("from_location", ""))
        to_loc = _canonicalize_location(decision.get("to_location", ""))
        if not from_loc or not to_loc:
            return None
        normalized["from_location"] = from_loc
        normalized["to_location"] = to_loc

    if action == "edit_leg":
        mode = _extract_mode((decision.get("transport_mode") or "").lower())
        if not mode:
            return None
        normalized["transport_mode"] = mode

    if action == "avoid_mode_on_leg":
        avoid_modes = decision.get("avoid_modes", [])
        if not isinstance(avoid_modes, list):
            return None
        filtered = []
        for mode in avoid_modes:
            parsed = _extract_mode(str(mode).lower())
            if parsed:
                filtered.append(parsed)
        if not filtered:
            return None
        normalized["avoid_modes"] = filtered

    if action == "update_preferences":
        avoid_modes = decision.get("avoid_modes", [])
        if isinstance(avoid_modes, list):
            filtered = []
            for mode in avoid_modes:
                parsed = _extract_mode(str(mode).lower())
                if parsed:
                    filtered.append(parsed)
            normalized["avoid_modes"] = filtered

    reason = decision.get("reason")
    if isinstance(reason, str) and reason.strip():
        normalized["reason"] = reason.strip()

    return normalized


def think(user_message):
    max_parse_retries = 2

    for _ in range(max_parse_retries + 1):
        try:
            reply = ask_llm(SYSTEM_PROMPT, user_message)

            start = reply.find("{")
            end = reply.rfind("}") + 1
            if start == -1 or end <= start:
                continue

            parsed = json.loads(reply[start:end])
            normalized = _normalize_decision(parsed)
            if normalized is None:
                continue

            if normalized.get("action") == "plan":
                # Don't let the LLM accidentally plan when user asked a question
                if _is_question(user_message.lower()):
                    return {"action": "explain", "reason": "question_guard"}

                global_preference = _detect_global_preference(user_message)
                if global_preference is not None:
                    return global_preference

                rule_override = _rule_based_override_decision(user_message)
                if rule_override is not None:
                    return rule_override

            if normalized.get("action") == "edit_leg":
                # Don't let the LLM set an override when user is asking a question
                if _is_question(user_message.lower()):
                    return {"action": "explain", "reason": "question_guard"}

            return normalized
        except Exception:
            continue

    return _fallback_decision(user_message)
