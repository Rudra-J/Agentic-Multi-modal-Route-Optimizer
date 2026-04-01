# LLM-First Intent Parsing Design

**Date:** 2026-04-01  
**Status:** Approved

---

## Goal

Remove the three post-LLM rule-based guards in `brain_agent.think()` that silently override the LLM's output, and move their logic into the system prompt as examples and instructions. The LLM becomes the single decision-maker; `_fallback_decision()` remains only as a last-resort safety net for complete LLM failures.

---

## Problem

`think()` currently applies three overrides **after** a valid LLM response is parsed:

1. `_is_question()` guard on `"plan"` action → redirects to `"explain"`
2. `_detect_global_preference()` guard on `"plan"` action → overrides with `"update_preferences"`
3. `_rule_based_override_decision()` guard on `"plan"` action → can replace any result
4. `_is_question()` guard on `"edit_leg"` action → redirects to `"explain"`

These fire silently (without setting `reason="fallback_rule"`), making them invisible to the eval. They reduce LLM autonomy and cause intent classification (70%) and mode extraction (60%) failures because the LLM never gets a chance to learn these patterns from its own outputs.

---

## Changes

### 1. `agents/brain_agent.py` — Strip guards from `think()`

**Before:**
```python
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
                if _is_question(user_message.lower()):
                    return {"action": "explain", "reason": "question_guard"}
                global_preference = _detect_global_preference(user_message)
                if global_preference is not None:
                    return global_preference
                rule_override = _rule_based_override_decision(user_message)
                if rule_override is not None:
                    return rule_override

            if normalized.get("action") == "edit_leg":
                if _is_question(user_message.lower()):
                    return {"action": "explain", "reason": "question_guard"}

            return normalized
        except Exception:
            continue
    return _fallback_decision(user_message)
```

**After:**
```python
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
            if normalized is not None:
                return normalized
        except Exception:
            continue
    return _fallback_decision(user_message)
```

`_fallback_decision()`, `_is_question()`, `_detect_global_preference()`, and `_rule_based_override_decision()` are kept in the file (they are still used by `_fallback_decision()`).

### 2. `agents/brain_agent.py` — Strengthen `SYSTEM_PROMPT`

Add three categories of examples to the existing prompt:

**Question vs command disambiguation:**
```
User: are we using a cab from Powai to BKC?
Output: {"action":"explain"}

User: is the Bandra to CST leg using train?
Output: {"action":"explain"}

User: use cab from Powai to BKC
Output: {"action":"edit_leg","from_location":"Powai","to_location":"BKC","transport_mode":"cab"}
```

**Global preference detection (no locations mentioned):**
```
User: I hate trains
Output: {"action":"update_preferences","avoid_modes":["train"]}

User: avoid all cabs today
Output: {"action":"update_preferences","avoid_modes":["cab"]}

User: no buses for me
Output: {"action":"update_preferences","avoid_modes":["bus"]}
```

**Mode extraction from natural phrasing:**
```
User: take an uber from Bandra to CST
Output: {"action":"edit_leg","from_location":"Bandra","to_location":"CST","transport_mode":"cab"}

User: get me an ola from BKC to Bandra
Output: {"action":"edit_leg","from_location":"BKC","to_location":"Bandra","transport_mode":"cab"}

User: no public transport on the Andheri to Dadar leg
Output: {"action":"avoid_mode_on_leg","from_location":"Andheri","to_location":"Dadar","avoid_modes":["train","metro","bus"]}
```

**Add explicit instruction rules at the bottom of the prompt:**
```
- If the user's message ends with "?" or uses question words (is, are, was, which, what, how), return action="explain". Do NOT treat questions as commands.
- If the user expresses dislike or avoidance for a mode WITHOUT mentioning specific locations, return action="update_preferences".
- "uber", "ola", "taxi" all map to transport_mode="cab".
```

---

## Success Criteria

Run `python -m eval.run_eval --area intent` after changes.

- Intent classification accuracy: target ≥ 85% (currently 70%)
- Mode extraction accuracy: target ≥ 85% (currently 60%)
- Fallback rate: should remain low (≤ 10%)
- Parse success rate: should remain 100%
