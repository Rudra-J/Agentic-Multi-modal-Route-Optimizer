import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

URL = "https://openrouter.ai/api/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost",
    "X-Title": "mobility-agent"
}


def ask_llm(system_prompt, user_prompt):

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=25)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"LLM request failed: {e}") from e

    return r.json()["choices"][0]["message"]["content"]
