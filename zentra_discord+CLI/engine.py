import asyncio
import json

from logger import log
from memory import build_prompt, save_to_memory, USER_ID
from ollama import query_ollama
from parser import extract_json
from dispatcher import dispatch_action


async def process_message(user_input: str, user_id: int = 0) -> str:
    prompt = build_prompt(user_id, user_input)

    try:
        raw_output = await query_ollama(prompt)
    except (ConnectionError, TimeoutError, RuntimeError) as exc:
        log.error(f"Ollama error: {exc}")
        return f"AI Error: {exc}"

    try:
        parsed = extract_json(raw_output)
        log.info(f"Parsed JSON:\n{json.dumps(parsed, indent=2)[:500]}")
    except ValueError as exc:
        log.error(f"JSON parse failure: {exc}")
        preview = raw_output[:800]
        return (
            f"Couldn't parse the AI's response as JSON.\n"
            f"Raw output:\n```\n{preview}\n```"
        )

    try:
        result, file_content = await dispatch_action(parsed)
    except Exception as exc:
        log.error(f"Dispatch error: {exc}", exc_info=True)
        return f"Action failed: {exc}"

    if file_content:
        filename = parsed.get("filename", "file")
        followup_prompt = (
            f"{user_input}\n\n"
            f"[ZENTRA NOTE: The file '{filename}' was read successfully. "
            f"Here is its content for you to reason about:]\n\n"
            f"```\n{file_content}\n```\n\n"
            f"Now answer the user's question about this file."
        )
        try:
            raw2    = await query_ollama(followup_prompt)
            parsed2 = extract_json(raw2)
            result2, _ = await dispatch_action(parsed2)
            result  = result + "\n\n" + result2
        except Exception as exc:
            log.warning(f"read_file follow-up failed: {exc}")
            result += "\n\nFile contents loaded into context."

    summary = (parsed.get("reply") or result)[:300]
    save_to_memory(user_id, user_input, summary)
    return result
