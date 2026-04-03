import json
import re


def extract_json(raw_text: str) -> dict:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()

    for text in [cleaned, raw_text.strip()]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        m = re.search(r"\{[\s\S]*?\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        no_fences = re.sub(r"```(?:json)?\n?", "", text).replace("```", "").strip()
        try:
            return json.loads(no_fences)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in model output:\n{raw_text[:600]}")
