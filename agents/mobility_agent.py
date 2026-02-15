from models.world_state import WorldState
from agents.brain_agent import think
from agents.action_agent import execute


class MobilityAgent:

    def __init__(self):
        self.state = WorldState()

    def chat(self, message, meetings):

        decision = think(message)

        result = execute(decision, self.state, meetings)

        return {
            "decision": decision,
            "result": result,
            "memory": {
                "avoid_modes": list(self.state.avoid_modes),
                "leg_avoid_modes": self.state.leg_avoid_modes
            }
        }
