# Mumbai Mobility Agent

A conversational AI assistant that helps you navigate Mumbai's multi-modal transit network — by simply talking to it.

---

## The Problem

Mumbai has one of the most complex urban transit networks in the world: local trains, metro lines, BEST buses, and cabs all operate in parallel, with overlapping routes, different reliability profiles, and wildly different costs. Planning a multi-stop day across this network is frustrating. You end up juggling apps, second-guessing connections, and manually accounting for your own constraints — "I hate crowded trains", "I can't walk far", "I have a meeting at 10".

No single tool lets you say *"plan my day, but avoid trains and use cab only for the last leg"* and actually get a coherent, time-validated plan back.

---

## What This Does

Mumbai Mobility Agent is a **conversational route optimizer**. You describe your day in natural language — stops, preferences, constraints, times — and the agent figures out the best path through the network.

### What you can ask it

- **Plan a multi-stop day**
  > "I need to go from Andheri to Dadar, then Dadar to Churchgate, then back home by 9 PM"

- **Apply constraints naturally**
  > "Avoid trains today" / "Use only metro and bus" / "No cabs on the Bandra to Dadar leg"

- **Override specific legs**
  > "Force cab from Kurla to BKC — I have luggage"

- **Ask what-if questions**
  > "What if I take cab instead of metro for the first leg?"

- **Check feasibility and timing**
  > "Can I make it from Andheri to CST by 9 AM?"

- **Handle conflicts and follow-ups**
  > The agent remembers your constraints across the conversation and resolves conflicts — for example, if you avoid trains globally but try to force a train on one leg, it surfaces the conflict and asks what you want to do.

- **Export your plan**
  > Download your optimized itinerary as a structured summary.

---

## How Constraints Work

You can set preferences at two levels:

- **Global**: "Avoid trains" applies to your entire day
- **Per-leg**: "Use cab from Bandra to BKC" applies only to that leg

Both persist across the full conversation. When they conflict, the agent surfaces the issue to you rather than silently picking one.

---

## Why No LangChain

This project deliberately avoids LangChain or any other LLM orchestration framework. The entire agent pipeline — intent parsing, decision routing, state management, constraint resolution, and fallback logic — is built from scratch in Python.

This was a conscious choice to deeply understand what LLM orchestration actually requires: how to structure prompts, how to validate and parse structured outputs reliably, how to handle LLM failures gracefully, and how to maintain multi-turn conversational state without a framework doing it for you.

The result is a lean, transparent stack with no hidden abstractions.

---

## Transport Modes

| Mode | Character |
|------|-----------|
| Metro | Fast urban corridors, high reliability |
| Local Train | Long-distance suburban links, low cost |
| Bus | Last-mile and cross-city, most flexible |
| Cab | On-demand, best for luggage or accessibility |

Routes are scored on **duration**, **cost**, and **reliability** — with traffic multipliers per mode.

---

## Setup

```bash
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # Add your OPENROUTER_API_KEY
uvicorn main:app --reload --port 8001
```

Open `http://127.0.0.1:8001/` in your browser.

Get a free API key at [openrouter.ai](https://openrouter.ai).

---

## Eval Results

The system is scored across 7 areas using an offline eval harness (`eval/`). Results below are from the current build using `qwen/qwen3.6-plus-preview:free` via OpenRouter.

| Area | Score | Status |
|------|-------|--------|
| LLM Intent Parsing | 100% | PASS |
| Constraint Application | 100% | PASS |
| Route Optimization | 100% | PASS |
| Schedule Feasibility | 100% | PASS |
| Conversation Flow | 90% | PASS |
| What-If Scenarios | 100% | PASS |
| Route Availability | 100% | PASS |
| **Overall** | **98.6%** | **7/7 areas passing** |

**Per-metric breakdown:**

| Metric | Score |
|--------|-------|
| Intent classification accuracy | 20/20 100% |
| Location extraction accuracy | 16/16 100% |
| Mode extraction accuracy | 10/10 100% |
| LLM fallback rate | 0/20 (zero fallbacks) |
| Global/leg constraint storage | 11/11 100% |
| Conflict detection | 4/4 100% |
| Route validity | 12/12 100% |
| Leg constraint compliance | 2/2 100% |
| Infeasibility detection | 2/2 100% |
| Schedule sort order | 4/4 100% |
| Multi-turn state persistence | 4/5 80% |
| Conflict surfacing | 2/2 100% |
| What-if preview trigger | 1/1 100% |
| What-if pending state | 2/2 100% |
| What-if confirmation | 1/1 100% |
| Route check status | 5/5 100% |
| Route availability flag | 5/5 100% |

Run the eval yourself:

```bash
python -m eval.run_eval          # all areas
python -m eval.run_eval --area intent
python -m eval.run_eval --area whatif
python -m eval.run_eval --area availability
```

---

## Requirements

- Python 3.9+
- An OpenRouter API key (free tier works)
