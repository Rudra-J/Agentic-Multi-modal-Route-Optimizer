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

    def _normalize(self, name: str):
        if name is None:
            return ""
        return name.strip().lower()

    def add_note(self, note: str):
        self.notes.append(note)

    def set_leg_override(self, from_loc: str, to_loc: str, mode: str, reason: str = ""):
        """Override the transport mode for a specific leg"""
        key = f"{self._normalize(from_loc)}->{self._normalize(to_loc)}"
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
