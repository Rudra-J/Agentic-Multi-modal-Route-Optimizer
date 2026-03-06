from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import csv
import io

from models.meeting import Meeting
from agents.schedule_agent import schedule

from models.route import RouteRequest
from agents.route_agent import find_route

from models.plan import PlanRequest
from agents.planner_agent import plan_day

from agents.mobility_agent import MobilityAgent
from data.mumbai_routes import get_all_locations, get_location_name

app = FastAPI(title="Mobility Agent API", version="1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return FileResponse("index.html")

@app.get("/health")
def health():
    return {"status": "ok", "city": "Mumbai"}

@app.get("/locations")
def get_locations():
    """Get all available locations"""
    locations = get_all_locations()
    return {
        "count": len(locations),
        "locations": [{
            "name": loc,
            "full_name": get_location_name(loc)
        } for loc in sorted(locations)]
    }

@app.post("/schedule")
def create_schedule(meetings: List[Meeting]):
    return schedule(meetings)

@app.post("/route")
def route(req: RouteRequest):
    return find_route(req.start, req.end, req.transport_mode)

@app.post("/plan_day")
def plan(req: PlanRequest):
    return plan_day(req.meetings, req.transport_mode)

agent = MobilityAgent()
@app.post("/chat")
def chat(req: dict):
    result = agent.chat(
        req["message"],
        req["meetings"]
    )
    
    print("\n[DEBUG main.py /chat endpoint]")
    print(f"  Full response: {result}")
    print(f"  Response has 'result' key: {'result' in result}")
    if 'result' in result and isinstance(result['result'], dict):
        plan = result['result']
        print(f"  Plan has 'route' key: {'route' in plan}")
        if 'route' in plan:
            print(f"  Route type: {type(plan['route'])}")
            print(f"  Route length: {len(plan['route']) if isinstance(plan['route'], list) else 'N/A'}")
        print(f"  Plan keys: {plan.keys()}")
    print()
    
    return result


@app.post("/set_leg_override")
def set_leg_override(req: dict):
    """Set a leg override directly on the agent state (testing helper).

    Payload: {"from": "BKC", "to": "Bandra", "mode": "cab", "reason": "user request"}
    """
    try:
        frm = req.get("from")
        to = req.get("to")
        mode = req.get("mode")
        reason = req.get("reason", "")

        if not frm or not to or not mode:
            return {"error": "from, to and mode are required"}

        agent.state.set_leg_override(frm, to, mode, reason)

        return {
            "status": "ok",
            "from": frm,
            "to": to,
            "mode": mode
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/clear_leg_override")
def clear_leg_override(req: dict):
    """Clear a leg override directly on the agent state (testing/UI helper).

    Payload: {"from": "BKC", "to": "Bandra"}
    """
    try:
        frm = req.get("from")
        to = req.get("to")

        if not frm or not to:
            return {"error": "from and to are required"}

        agent.state.clear_leg_override(frm, to)

        return {
            "status": "ok",
            "from": frm,
            "to": to
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/clear_preferences")
def clear_preferences():
    """Clear global avoid-mode preferences from agent state."""
    try:
        agent.state.avoid_modes.clear()
        return {
            "status": "ok",
            "avoid_modes": []
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/remove_avoid_mode")
def remove_avoid_mode(req: dict):
    """Remove a single global avoid mode.

    Payload: {"mode": "train"}
    """
    try:
        mode = req.get("mode", "").strip().lower()
        if not mode:
            return {"error": "mode is required"}
        agent.state.avoid_modes.discard(mode)
        return {"status": "ok", "avoid_modes": list(agent.state.avoid_modes)}
    except Exception as e:
        return {"error": str(e)}


@app.post("/clear_leg_avoid")
def clear_leg_avoid(req: dict):
    """Clear avoid-mode constraint for a specific leg.

    Payload: {"from": "Bandra", "to": "CST"}
    """
    try:
        frm = req.get("from")
        to = req.get("to")
        if not frm or not to:
            return {"error": "from and to are required"}
        agent.state.clear_leg_avoid_modes(frm, to)
        return {"status": "ok", "from": frm, "to": to}
    except Exception as e:
        return {"error": str(e)}


@app.post("/reset_state")
def reset_state():
    """Reset all conversational memory and constraints."""
    try:
        agent.state.reset()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/upload_itinerary")
async def upload_itinerary(file: UploadFile = File(...)):
    """Upload a CSV file with meetings itinerary.
    
    Expected CSV format:
    location,start_time,duration_minutes
    Powai,10:00,30
    Andheri,11:15,30
    Thane,13:30,30
    """
    try:
        contents = await file.read()
        text = contents.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text))
        
        meetings = []
        for row in reader:
            if not row.get('location') or not row.get('start_time'):
                continue
            
            meeting = {
                'location': row['location'].strip(),
                'start_time': row['start_time'].strip(),
                'duration_minutes': int(row.get('duration_minutes', 30))
            }
            meetings.append(meeting)
        
        if not meetings:
            return {"error": "No valid meetings found in CSV"}
        
        return {
            "success": True,
            "count": len(meetings),
            "meetings": meetings
        }
    
    except Exception as e:
        return {
            "error": f"Failed to parse CSV: {str(e)}"
        }