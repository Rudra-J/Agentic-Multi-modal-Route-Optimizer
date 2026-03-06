from models.world_state import WorldState
from agents.brain_agent import think
from agents.action_agent import execute
from agents.planner_agent import plan_day
from data.mumbai_routes import get_all_locations, get_route_info
import re


class MobilityAgent:

    def __init__(self):
        self.state = WorldState()

    def _extract_mode(self, text: str):
        value = (text or "").lower()
        if "cab" in value or "taxi" in value or "uber" in value or "ola" in value:
            return "cab"
        if "metro" in value:
            return "metro"
        if "train" in value:
            return "train"
        if "bus" in value:
            return "bus"
        return None

    def _extract_leg(self, text: str):
        cleaned = re.sub(r"[^a-z\s]", " ", (text or "").lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        locations = get_all_locations()
        mentions = []
        for loc in locations:
            m = re.search(rf"\b{re.escape(loc.lower())}\b", cleaned)
            if m:
                mentions.append((m.start(), loc))
        mentions.sort(key=lambda x: x[0])
        if len(mentions) < 2:
            return None, None

        to_match = re.search(r"\bto\b", cleaned)
        if to_match:
            to_idx = to_match.start()
            before = [m for m in mentions if m[0] < to_idx]
            after = [m for m in mentions if m[0] > to_idx]
            if before and after:
                return before[-1][1], after[0][1]

        return mentions[0][1], mentions[1][1]

    def _to_minutes(self, hm: str):
        match = re.match(r"(\d+)h(\d+)m", hm or "")
        if not match:
            return 0
        return int(match.group(1)) * 60 + int(match.group(2))

    def _find_section(self, plan: dict, from_loc: str, to_loc: str):
        for section in plan.get("sections", []):
            if section.get("from") == from_loc and section.get("to") == to_loc:
                return section
        return None

    def _extract_single_location(self, text: str):
        """Extract a single location mention from text."""
        cleaned = re.sub(r"[^a-z\s]", " ", (text or "").lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        locations = get_all_locations()
        mentions = []
        for loc in locations:
            m = re.search(rf"\b{re.escape(loc.lower())}\b", cleaned)
            if m:
                mentions.append((m.start(), loc))
        mentions.sort(key=lambda x: x[0])
        if len(mentions) == 1:
            return mentions[0][1]
        return None

    def _is_plan_schedule_question(self, message: str):
        """Detect questions about departure/arrival times at a specific location."""
        text = (message or "").lower().strip()
        if not text.endswith("?"):
            return False
        loc = self._extract_single_location(text)
        if not loc:
            return False
        time_markers = [
            "what time", "when do", "when should", "when will",
            "leave from", "depart from", "start from",
            "arrive at", "reach", "get to",
            "have to leave", "need to leave", "should i leave",
            "have to be at", "need to be at",
        ]
        return any(marker in text for marker in time_markers)

    def _build_plan_schedule_answer(self, message: str):
        """Answer time/schedule questions about a specific location in the plan."""
        if not self._is_plan_schedule_question(message):
            return None
        if not self.state.last_plan or not isinstance(self.state.last_plan, dict):
            return {
                "status": "plan_query",
                "message": "No plan available yet. Ask me to 'plan my day' first."
            }
        loc = self._extract_single_location(message)
        if not loc:
            return None
        text = (message or "").lower()
        sections = self.state.last_plan.get("sections", [])

        # Determine if asking about departure or arrival
        arrive_markers = ["arrive at", "reach", "get to", "be at"]
        is_arrival = any(am in text for am in arrive_markers)

        if is_arrival:
            # Find section where to == loc
            for section in sections:
                if section.get("to", "").lower() == loc.lower():
                    return {
                        "status": "plan_query",
                        "message": f"You'll arrive at **{loc}** by **{section.get('section_end', '?')}** ({section.get('section_time', '')} travel).",
                        "from": section.get("from"),
                        "to": loc
                    }
            return {
                "status": "plan_query",
                "message": f"I don't see {loc} as a destination in any section of the current plan."
            }
        else:
            # Departure — find section where from == loc
            for section in sections:
                if section.get("from", "").lower() == loc.lower():
                    return {
                        "status": "plan_query",
                        "message": f"You need to leave **{loc}** by **{section.get('section_start', '?')}** to reach {section.get('to', '?')} on time ({section.get('section_time', '')} travel).",
                        "from": loc,
                        "to": section.get("to")
                    }
            return {
                "status": "plan_query",
                "message": f"I don't see {loc} as a departure point in any section of the current plan."
            }

    def _is_what_if_question(self, message: str):
        text = (message or "").lower()
        markers = ["how much", "extra time", "what if", "would it", "if i take", "if i use"]
        return any(marker in text for marker in markers)

    def _is_current_plan_question(self, message: str):
        """Detect questions about what mode/transport the current plan uses on a leg."""
        text = (message or "").lower().strip()
        if not text.endswith("?"):
            return False
        from_loc, to_loc = self._extract_leg(text)
        if not from_loc or not to_loc:
            return False
        query_markers = [
            "what are we", "what is", "what's", "what mode", "which mode",
            "what transport", "how are we", "how do we", "are we using",
            "are we taking", "are we going", "what are using",
            "what will we", "which way", "what route",
        ]
        return any(marker in text for marker in query_markers)

    def _build_current_plan_leg_answer(self, message: str):
        """Answer questions about what mode the current plan uses on a specific leg."""
        if not self._is_current_plan_question(message):
            return None
        if not self.state.last_plan or not isinstance(self.state.last_plan, dict):
            return {
                "status": "plan_query",
                "message": "No plan available yet. Ask me to 'plan my day' first, then you can ask about specific legs."
            }
        from_loc, to_loc = self._extract_leg(message)
        if not from_loc or not to_loc:
            return None
        section = self._find_section(self.state.last_plan, from_loc, to_loc)
        if not section:
            return {
                "status": "plan_query",
                "message": f"I don't see a {from_loc} \u2192 {to_loc} section in the current plan."
            }
        legs = section.get("legs", [])
        if not legs:
            return {
                "status": "plan_query",
                "message": f"The {from_loc} \u2192 {to_loc} section has no route legs in the current plan."
            }
        modes = [leg.get("mode", "unknown") for leg in legs]
        time_str = section.get("section_time", "")
        cost = section.get("section_cost", 0)
        if len(modes) == 1:
            return {
                "status": "plan_query",
                "message": f"The current plan uses **{modes[0]}** from {from_loc} to {to_loc} ({time_str}, \u20b9{cost}).",
                "from": from_loc,
                "to": to_loc
            }
        mode_list = " \u2192 ".join(modes)
        return {
            "status": "plan_query",
            "message": f"The current plan uses {mode_list} from {from_loc} to {to_loc} ({time_str}, \u20b9{cost}).",
            "from": from_loc,
            "to": to_loc
        }

    def _is_route_availability_question(self, message: str):
        text = (message or "").lower()
        markers = ["is there", "are there", "do we have", "available", "can i take"]
        if not any(marker in text for marker in markers):
            return False
        if " to " in text:
            return True
        # contextual reference with a known last query
        if self.state.last_route_query:
            context_markers = [
                "that route", "that leg", "this route", "this leg",
                "in that", "on that", "for that",
                "other option", "other way", "other mode", "alternative",
                "else", "different",
            ]
            if any(cm in text for cm in context_markers):
                return True
        return False

    def _is_itinerary_mode_list_request(self, message: str):
        text = (message or "").lower()
        mode = self._extract_mode(text)
        if not mode:
            return False

        list_markers = ["list", "all", "available", "show", "what are"]
        scope_markers = ["itinerary", "route", "routes", "day", "plan"]
        return any(marker in text for marker in list_markers) and any(marker in text for marker in scope_markers)

    def _build_itinerary_mode_list_answer(self, message: str, meetings):
        if not self._is_itinerary_mode_list_request(message):
            return None

        mode = self._extract_mode(message)
        if not mode:
            return None

        if not meetings or len(meetings) < 2:
            return {
                "status": "itinerary_mode_list",
                "mode": mode,
                "matches": [],
                "message": "I need at least two meetings to list route options for an itinerary."
            }

        matches = []
        for i in range(len(meetings) - 1):
            from_loc = meetings[i].get("location")
            to_loc = meetings[i + 1].get("location")
            if not from_loc or not to_loc:
                continue

            options = get_route_info(from_loc, to_loc, mode=mode)
            if not options:
                continue

            fastest = min(options, key=lambda r: r[2])
            matches.append({
                "from": from_loc,
                "to": to_loc,
                "mode": mode,
                "duration_minutes": fastest[2],
                "cost": fastest[4],
                "reliability": fastest[5]
            })

        if not matches:
            return {
                "status": "itinerary_mode_list",
                "mode": mode,
                "matches": [],
                "message": f"No direct {mode} routes are available between consecutive meetings in this itinerary."
            }

        lines = [f"Available direct {mode} options in your itinerary:"]
        for item in matches:
            lines.append(
                f"- {item['from']} → {item['to']}: {item['duration_minutes']} min, ₹{item['cost']}"
            )

        return {
            "status": "itinerary_mode_list",
            "mode": mode,
            "matches": matches,
            "message": "\n".join(lines)
        }

    def _is_followup_apply_request(self, message: str):
        text = (message or "").lower()
        # Exclude obvious questions — those should go to route_check instead
        question_markers = ["is there", "are there", "do we have", "available"]
        if any(qm in text for qm in question_markers):
            return False
        mode = self._extract_mode(text)
        markers = ["then", "that route", "that leg", "instead", "can i take",
                   "i'll take", "i will take", "can i use", "use that",
                   "take that", "do that", "let's do", "let's use",
                   "switch to that", "apply that", "go with that"]
        if mode:
            return any(marker in text for marker in markers)
        # No explicit mode — allow if last_route_query carries a mode
        if self.state.last_route_query and self.state.last_route_query.get("mode"):
            return any(marker in text for marker in markers)
        return False

    def _build_route_availability_answer(self, message: str):
        if not self._is_route_availability_question(message):
            return None

        mode = self._extract_mode(message)
        from_loc, to_loc = self._extract_leg(message)
        # Fall back to last discussed leg for contextual references
        if (not from_loc or not to_loc) and self.state.last_route_query:
            from_loc = self.state.last_route_query.get("from")
            to_loc = self.state.last_route_query.get("to")
        if not from_loc or not to_loc:
            return {
                "status": "route_check",
                "message": "I couldn't identify both locations in your question. Please ask like: 'Is there a train from Powai to BKC?'"
            }

        direct_any = get_route_info(from_loc, to_loc, mode="any")
        if mode:
            direct_mode = get_route_info(from_loc, to_loc, mode=mode)
            if direct_mode:
                fastest = min(direct_mode, key=lambda r: r[2])
                return {
                    "status": "route_check",
                    "message": f"Yes — there is a direct {mode} route from {from_loc} to {to_loc} (about {fastest[2]} min, ₹{fastest[4]}).",
                    "from": from_loc,
                    "to": to_loc,
                    "mode": mode,
                    "available": True
                }

            alternatives = sorted({r[3] for r in direct_any})
            if alternatives:
                return {
                    "status": "route_check",
                    "message": f"No direct {mode} route exists from {from_loc} to {to_loc}. Direct alternatives: {', '.join(alternatives)}.",
                    "from": from_loc,
                    "to": to_loc,
                    "mode": mode,
                    "available": False,
                    "alternatives": alternatives
                }

            return {
                "status": "route_check",
                "message": f"No direct route exists from {from_loc} to {to_loc} in the current network.",
                "from": from_loc,
                "to": to_loc,
                "mode": mode,
                "available": False
            }

        if direct_any:
            alternatives = sorted({r[3] for r in direct_any})
            return {
                "status": "route_check",
                "message": f"Direct routes from {from_loc} to {to_loc} are available via: {', '.join(alternatives)}.",
                "from": from_loc,
                "to": to_loc,
                "available": True,
                "alternatives": alternatives
            }

        return {
            "status": "route_check",
            "message": f"No direct route exists from {from_loc} to {to_loc} in the current network.",
            "from": from_loc,
            "to": to_loc,
            "available": False
        }

    def _is_confirmation(self, message: str):
        text = (message or "").lower().strip()
        return text in ["yes", "y", "yes please", "do it", "go ahead", "apply", "make the change"]

    def _is_rejection(self, message: str):
        text = (message or "").lower().strip()
        return text in ["no", "n", "no thanks", "cancel", "leave it", "don\u2019t", "dont"]

    def _build_what_if_preview(self, message, meetings):
        if not self._is_what_if_question(message):
            return None

        mode = self._extract_mode(message)
        from_loc, to_loc = self._extract_leg(message)
        if not mode or not from_loc or not to_loc:
            return None

        current_plan = plan_day(
            meetings,
            avoid_modes=self.state.avoid_modes,
            leg_overrides=self.state.leg_overrides,
            leg_avoid_modes=self.state.leg_avoid_modes
        )

        if not isinstance(current_plan, dict) or current_plan.get("status") == "failed":
            return {
                "status": "proposal_preview",
                "message": "I can't estimate the change yet because the current plan is not feasible."
            }

        current_section = self._find_section(current_plan, from_loc, to_loc)
        if not current_section:
            return {
                "status": "proposal_preview",
                "message": f"I couldn't find a direct itinerary section from {from_loc} to {to_loc} in your current plan."
            }

        simulated_overrides = dict(self.state.leg_overrides)
        sim_key = f"{from_loc.strip().lower()}->{to_loc.strip().lower()}"
        simulated_overrides[sim_key] = {"mode": mode, "reason": "what_if_preview"}

        simulated_plan = plan_day(
            meetings,
            avoid_modes=self.state.avoid_modes,
            leg_overrides=simulated_overrides,
            leg_avoid_modes=self.state.leg_avoid_modes
        )

        if not isinstance(simulated_plan, dict) or simulated_plan.get("status") == "failed":
            return {
                "status": "proposal_preview",
                "message": f"If we switch {from_loc} -> {to_loc} to {mode}, the plan becomes infeasible. I have not staged this change."
            }

        simulated_section = self._find_section(simulated_plan, from_loc, to_loc)
        if not simulated_section:
            return {
                "status": "proposal_preview",
                "message": f"I couldn't compute a comparable section for {from_loc} → {to_loc} after switching to {mode}."
            }

        current_time = self._to_minutes(current_section.get("section_time", "0h0m"))
        simulated_time = self._to_minutes(simulated_section.get("section_time", "0h0m"))
        current_cost = int(current_section.get("section_cost", 0))
        simulated_cost = int(simulated_section.get("section_cost", 0))

        delta_time = simulated_time - current_time
        delta_cost = simulated_cost - current_cost
        time_sign = "+" if delta_time >= 0 else ""
        cost_sign = "+" if delta_cost >= 0 else ""

        self.state.set_pending_leg_change(from_loc, to_loc, mode, "confirmed_from_preview")

        return {
            "status": "proposal_preview",
            "message": (
                f"Current {from_loc} → {to_loc}: {current_section.get('section_time')} and ₹{current_cost}. "
                f"If switched to {mode}: {simulated_section.get('section_time')} and ₹{simulated_cost} "
                f"({time_sign}{delta_time} min, {cost_sign}₹{delta_cost}). "
                "Reply 'yes' to apply this change and replan."
            ),
            "proposal": {
                "from": from_loc,
                "to": to_loc,
                "mode": mode
            }
        }

    def chat(self, message, meetings):

        itinerary_mode_list = self._build_itinerary_mode_list_answer(message, meetings)
        if itinerary_mode_list is not None:
            return {
                "decision": {"action": "list_itinerary_mode_routes", "reason": "itinerary_mode_listing"},
                "result": itinerary_mode_list,
                "memory": {
                    "avoid_modes": list(self.state.avoid_modes),
                    "leg_overrides": self.state.leg_overrides,
                    "leg_avoid_modes": self.state.leg_avoid_modes
                }
            }

        if self._is_followup_apply_request(message) and self.state.last_route_query:
            text_lower = (message or "").lower()
            mode_from_text = self._extract_mode(message)
            lrq_mode = self.state.last_route_query.get("mode")
            # "instead of [mode]" — the mentioned mode is the one being replaced,
            # not the one to apply; use last_route_query.mode instead.
            if mode_from_text and lrq_mode and "instead of" in text_lower:
                instead_tail = text_lower[text_lower.index("instead of"):]
                if mode_from_text in instead_tail:
                    follow_mode = lrq_mode
                else:
                    follow_mode = mode_from_text
            else:
                follow_mode = mode_from_text or lrq_mode
            from_loc = self.state.last_route_query.get("from")
            to_loc = self.state.last_route_query.get("to")
            if follow_mode and from_loc and to_loc:
                self.state.set_leg_override(from_loc, to_loc, follow_mode, "followup_from_route_query")
                plan = plan_day(
                    meetings,
                    avoid_modes=self.state.avoid_modes,
                    leg_overrides=self.state.leg_overrides,
                    leg_avoid_modes=self.state.leg_avoid_modes
                )
                if isinstance(plan, dict) and plan.get("status") != "failed":
                    self.state.last_plan = plan
                return {
                    "decision": {"action": "plan", "reason": "followup_route_apply"},
                    "result": plan,
                    "memory": {
                        "avoid_modes": list(self.state.avoid_modes),
                        "leg_overrides": self.state.leg_overrides,
                        "leg_avoid_modes": self.state.leg_avoid_modes
                    }
                }

        if not self.state.pending_leg_change and (self._is_confirmation(message) or self._is_rejection(message)):
            return {
                "decision": {"action": "no_action", "reason": "no_pending_proposal"},
                "result": {"message": "There is no pending route change to confirm right now."},
                "memory": {
                    "avoid_modes": list(self.state.avoid_modes),
                    "leg_overrides": self.state.leg_overrides,
                    "leg_avoid_modes": self.state.leg_avoid_modes
                }
            }

        route_check = self._build_route_availability_answer(message)
        if route_check is not None:
            if route_check.get("from") and route_check.get("to"):
                self.state.last_route_query = {
                    "from": route_check.get("from"),
                    "to": route_check.get("to"),
                    "mode": route_check.get("mode")
                }
            return {
                "decision": {"action": "check_route_availability", "reason": "conversational_route_query"},
                "result": route_check,
                "memory": {
                    "avoid_modes": list(self.state.avoid_modes),
                    "leg_overrides": self.state.leg_overrides,
                    "leg_avoid_modes": self.state.leg_avoid_modes
                }
            }

        if self.state.pending_leg_change:
            pending = self.state.pending_leg_change
            if self._is_confirmation(message):
                self.state.set_leg_override(pending["from"], pending["to"], pending["mode"], pending.get("reason", ""))
                self.state.clear_pending_leg_change()

                plan = plan_day(
                    meetings,
                    avoid_modes=self.state.avoid_modes,
                    leg_overrides=self.state.leg_overrides,
                    leg_avoid_modes=self.state.leg_avoid_modes
                )
                if isinstance(plan, dict) and plan.get("status") != "failed":
                    self.state.last_plan = plan
                return {
                    "decision": {"action": "plan", "reason": "proposal_confirmed"},
                    "result": plan,
                    "memory": {
                        "avoid_modes": list(self.state.avoid_modes),
                        "leg_overrides": self.state.leg_overrides,
                        "leg_avoid_modes": self.state.leg_avoid_modes
                    }
                }

            if self._is_rejection(message):
                self.state.clear_pending_leg_change()
                return {
                    "decision": {"action": "no_action", "reason": "proposal_cancelled"},
                    "result": {"message": "Okay, no changes made."},
                    "memory": {
                        "avoid_modes": list(self.state.avoid_modes),
                        "leg_overrides": self.state.leg_overrides,
                        "leg_avoid_modes": self.state.leg_avoid_modes
                    }
                }

        preview = self._build_what_if_preview(message, meetings)
        if preview is not None:
            return {
                "decision": {"action": "what_if", "reason": "conversational_preview"},
                "result": preview,
                "memory": {
                    "avoid_modes": list(self.state.avoid_modes),
                    "leg_overrides": self.state.leg_overrides,
                    "leg_avoid_modes": self.state.leg_avoid_modes
                }
            }

        plan_leg_answer = self._build_current_plan_leg_answer(message)
        if plan_leg_answer is not None:
            # Track discussed leg for contextual follow-ups
            if plan_leg_answer.get("from") and plan_leg_answer.get("to"):
                self.state.last_route_query = {
                    "from": plan_leg_answer["from"],
                    "to": plan_leg_answer["to"],
                }
            return {
                "decision": {"action": "plan_query", "reason": "current_plan_leg_question"},
                "result": plan_leg_answer,
                "memory": {
                    "avoid_modes": list(self.state.avoid_modes),
                    "leg_overrides": self.state.leg_overrides,
                    "leg_avoid_modes": self.state.leg_avoid_modes
                }
            }

        plan_schedule_answer = self._build_plan_schedule_answer(message)
        if plan_schedule_answer is not None:
            if plan_schedule_answer.get("from") and plan_schedule_answer.get("to"):
                self.state.last_route_query = {
                    "from": plan_schedule_answer["from"],
                    "to": plan_schedule_answer["to"],
                }
            return {
                "decision": {"action": "plan_query", "reason": "plan_schedule_question"},
                "result": plan_schedule_answer,
                "memory": {
                    "avoid_modes": list(self.state.avoid_modes),
                    "leg_overrides": self.state.leg_overrides,
                    "leg_avoid_modes": self.state.leg_avoid_modes
                }
            }

        decision = think(message)

        result = execute(decision, self.state, meetings)

        return {
            "decision": decision,
            "result": result,
            "memory": {
                "avoid_modes": list(self.state.avoid_modes),
                "leg_overrides": self.state.leg_overrides,
                "leg_avoid_modes": self.state.leg_avoid_modes
            }
        }
