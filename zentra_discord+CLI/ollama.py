import asyncio
import json
import requests

from config import (
    OLLAMA_ENDPOINT, OLLAMA_MODEL, OLLAMA_TEMPERATURE,
    OLLAMA_VISION_MODEL, SYSTEM_PROMPT,
)
from logger import log


def _query_ollama_sync(prompt: str) -> str:
    payload = {
        "model":      OLLAMA_MODEL,
        "stream":     True,
        "keep_alive": -1,
        "options": {
            "temperature":    OLLAMA_TEMPERATURE,
            "num_predict":    -1,
            "num_ctx":        16384,
            "top_p":          0.9,
            "repeat_penalty": 1.1,
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    }
    try:
        resp = requests.post(
            f"{OLLAMA_ENDPOINT}/api/chat",
            json=payload,
            timeout=600,
            stream=True,
        )
        resp.raise_for_status()

        full_content = []
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                full_content.append(delta)
            if chunk.get("done", False):
                break

        raw = "".join(full_content)
        log.info(f"Ollama raw (first 300 chars): {raw[:300]}")
        return raw

    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Cannot connect to Ollama — is it running?\n"
            f"Start it with:  ollama run {OLLAMA_MODEL}"
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("Ollama timed out after 600 s.")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"Ollama HTTP error: {exc}")


def ollama_raw_sync(system: str, user: str, max_tokens: int = 300) -> str:
    payload = {
        "model":      OLLAMA_MODEL,
        "stream":     False,
        "keep_alive": -1,
        "options": {"temperature": 0.3, "num_predict": max_tokens},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user[:4000]},
        ],
    }
    try:
        r = requests.post(f"{OLLAMA_ENDPOINT}/api/chat", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as exc:
        log.warning(f"ollama_raw_sync failed: {exc}")
        return user[:200] + "…"


def ollama_vision_sync(image_b64: str, prompt: str, max_tokens: int = 1000) -> str:
    payload = {
        "model":      OLLAMA_VISION_MODEL,
        "stream":     False,
        "keep_alive": -1,
        "options": {
            "temperature": 0.1,
            "num_predict": max_tokens,
            "num_ctx":     8192,
        },
        "messages": [
            {
                "role":    "user",
                "content": prompt,
                "images":  [image_b64],
            }
        ],
    }
    try:
        r = requests.post(f"{OLLAMA_ENDPOINT}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except Exception as exc:
        log.warning(f"Vision model call failed: {exc}")
        return ""


async def query_ollama(prompt: str) -> str:
    return await asyncio.to_thread(_query_ollama_sync, prompt)
