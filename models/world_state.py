class WorldState:
    """
    Persistent memory of the agent across turns.
    """

    def __init__(self):
        self.avoid_modes = set()
        self.avoid_locations = set()
        self.last_plan = None
        self.notes = []
        self.leg_overrides = {}  # key: "from_loc->to_loc", value: {"mode": "metro", "reason": "..."}
        self.leg_avoid_modes = {}  # key: "from_loc->to_loc", value: {"avoid": ["train", "bus"], "reason": "..."}
        self.pending_leg_change = None  # conversational proposal awaiting user confirmation
        self.last_route_query = None  # last availability question context

    def _normalize(self, name: str):
        if name is None:
            return ""
        return name.strip().lower()

    def add_avoid_mode(self, mode: str):
        """Add a mode to global avoid list and purge any leg overrides forcing that mode."""
        self.avoid_modes.add(mode)
        # Remove any leg override that forces the now-avoided mode
        conflicting_keys = [
            key for key, val in self.leg_overrides.items()
            if val.get("mode") == mode
        ]
        for key in conflicting_keys:
            del self.leg_overrides[key]

    def add_note(self, note: str):
        self.notes.append(note)

    def set_leg_override(self, from_loc: str, to_loc: str, mode: str, reason: str = ""):
        """Override the transport mode for a specific leg"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
        # Clear conflicting avoid entry for the same leg
        if key in self.leg_avoid_modes:
            existing = self.leg_avoid_modes[key]
            if mode in existing.get("avoid", []):
                existing["avoid"].remove(mode)
                if not existing["avoid"]:
                    del self.leg_avoid_modes[key]
        self.leg_overrides[key] = {
            "mode": mode,
            "reason": reason
        }

    def get_leg_override(self, from_loc: str, to_loc: str):
        """Get override for a specific leg, returns None if not set"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
        return self.leg_overrides.get(key)

    def clear_leg_override(self, from_loc: str, to_loc: str):
        """Clear override for a specific leg"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
        if key in self.leg_overrides:
            del self.leg_overrides[key]

    def set_leg_avoid_modes(self, from_loc: str, to_loc: str, avoid_modes: list, reason: str = ""):
        """Set specific modes to avoid for a particular leg"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
        # Clear conflicting force-override if the forced mode is being avoided
        if key in self.leg_overrides:
            forced_mode = self.leg_overrides[key].get("mode")
            if forced_mode in avoid_modes:
                del self.leg_overrides[key]
        self.leg_avoid_modes[key] = {
            "avoid": avoid_modes,
            "reason": reason
        }

    def get_leg_avoid_modes(self, from_loc: str, to_loc: str):
        """Get avoid modes for a specific leg, returns None if not set"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
        return self.leg_avoid_modes.get(key)

    def clear_leg_avoid_modes(self, from_loc: str, to_loc: str):
        """Clear avoid modes for a specific leg"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
        if key in self.leg_avoid_modes:
            del self.leg_avoid_modes[key]

    def set_pending_leg_change(self, from_loc: str, to_loc: str, mode: str, reason: str = ""):
        self.pending_leg_change = {
            "from": from_loc,
            "to": to_loc,
            "mode": mode,
            "reason": reason
        }

    def clear_pending_leg_change(self):
        self.pending_leg_change = None

    def reset(self):
        self.avoid_modes.clear()
        self.avoid_locations.clear()
        self.last_plan = None
        self.notes = []
        self.leg_overrides = {}
        self.leg_avoid_modes = {}
        self.pending_leg_change = None
        self.last_route_query = None
