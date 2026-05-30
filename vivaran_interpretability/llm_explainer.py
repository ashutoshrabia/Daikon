import requests
import os
from typing import List, Dict, Any


def explain_rules_with_ollama(
    rules: List[str],
    sample_rows: List[Dict[str, Any]],
    progname: str = "adult",
) -> str:

    if not rules:
        return "No rules were learned."

    model = os.getenv("OLLAMA_MODEL", "phi3")

    rules_preview = "\n".join(rules)
    samples_preview = "\n".join(str(r) for r in sample_rows[:20])

    prompt = f"""
You are a data scientist explaining rules mined from the Adult dataset.

Dataset: {progname}

Rules:
{rules_preview}

Example rows:
{samples_preview}

Explain briefly:
1. What patterns these rules show.
2. Some interesting rules in plain English.
3. Any suspicious rules.

Use bullet points.
"""

    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=1000
        )

        response.raise_for_status()
        return response.json()["response"].strip()

    except Exception as e:
        return f"Ollama failed: {e}"