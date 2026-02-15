import json
from services.llm import ask_llm

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



def think(user_message):

    reply = ask_llm(SYSTEM_PROMPT, user_message)

    # Extract JSON safely
    start = reply.find("{")
    end = reply.rfind("}") + 1

    return json.loads(reply[start:end])
