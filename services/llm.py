import os
import time
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


def ask_llm(system_prompt, user_prompt, max_retries=2, retry_delay_sec=1.0):

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    payload = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            r = requests.post(URL, headers=HEADERS, json=payload, timeout=25)
            r.raise_for_status()

            data = r.json()
            return data["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(retry_delay_sec)
                continue
            break

    raise RuntimeError(f"LLM request failed after retries: {last_error}") from last_error
