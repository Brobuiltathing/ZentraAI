import asyncio
import json
import re

from zentra.logger import log
from zentra.ollama import ollama_raw_sync


_saved_workflows: dict[str, list[dict]] = {}


def _parse_workflow_sync(user_text: str) -> list[dict]:
    raw = ollama_raw_sync(
        "You are a workflow planner. Break the user's request into sequential steps.\n"
        "Each step is an action ZENTRA can perform.\n"
        "Reply ONLY with a raw JSON array, no markdown:\n"
        '[{"step": 1, "action": "shell", "command": "npm test", "folder": "./myproject", '
        '"on_fail": "stop", "description": "run tests"},\n'
        ' {"step": 2, "action": "shell", "command": "git add . && git commit -m \\"auto\\"", '
        '"on_fail": "stop", "description": "commit changes"}]\n\n'
        "Available actions: shell, create_file, run_file, open_app, close_app, "
        "gmail_send, github_push, calendar_add, clipboard_read\n"
        "on_fail options: stop, skip, retry\n"
        "Include ALL relevant fields for each action type.",
        user_text,
        max_tokens=800,
    )
    try:
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    log.warning(f"Could not parse workflow: {raw[:300]}")
    return []


async def handle_workflow_run(data: dict, dispatch_fn=None) -> str:
    user_text = (data.get("reply") or data.get("content") or "").strip()
    if not user_text:
        return "workflow: no description provided."

    steps = await asyncio.to_thread(_parse_workflow_sync, user_text)
    if not steps:
        return "Could not plan a workflow from your description. Try being more specific."

    parts = [f"**Workflow** ({len(steps)} steps)\n"]

    for i, step in enumerate(steps):
        desc = step.get("description", f"step {i+1}")
        action = step.get("action", "shell")
        on_fail = step.get("on_fail", "stop")
        parts.append(f"  [{i+1}/{len(steps)}] {desc}...")

        action_data = {
            "action": action,
            "content": step.get("command", step.get("content", "")),
            "filename": step.get("filename", ""),
            "folder": step.get("folder", ""),
            "reply": step.get("reply", step.get("command", "")),
            "app": step.get("app", ""),
            "git_folder": step.get("git_folder", ""),
            "git_message": step.get("git_message", ""),
            "patches": step.get("patches", []),
            "files": step.get("files", []),
            "run_args": step.get("run_args", []),
            "app_path": "",
            "screen_goal": "",
            "screen_actions": [],
        }

        try:
            if dispatch_fn:
                result, _ = await dispatch_fn(action_data)
            else:
                from zentra.dispatcher import dispatch_action
                result, _ = await dispatch_action(action_data)

            is_error = "error" in result.lower()[:50] or "failed" in result.lower()[:50]

            if is_error:
                parts.append(f"    FAILED: {result[:200]}")
                if on_fail == "stop":
                    parts.append(f"\n  Workflow stopped at step {i+1} (on_fail=stop)")
                    break
                elif on_fail == "retry":
                    parts.append("    retrying once...")
                    try:
                        result2, _ = await dispatch_fn(action_data) if dispatch_fn else await dispatch_action(action_data)
                        parts.append(f"    retry: {result2[:200]}")
                    except Exception as exc2:
                        parts.append(f"    retry also failed: {exc2}")
                        break
            else:
                summary = result[:150].replace("\n", " ")
                parts.append(f"    OK: {summary}")

        except Exception as exc:
            parts.append(f"    ERROR: {exc}")
            if on_fail == "stop":
                parts.append(f"\n  Workflow stopped at step {i+1}")
                break

    parts.append(f"\n**Workflow complete.**")
    return "\n".join(parts)


def handle_workflow_save(data: dict) -> str:
    reply = (data.get("reply") or "").strip()
    name = (data.get("app") or "").strip()
    if not name:
        return "workflow_save: provide a name in the 'app' field."
    if not reply:
        return "workflow_save: provide the workflow description in 'reply'."

    steps = _parse_workflow_sync(reply)
    if not steps:
        return "Could not parse workflow steps."

    _saved_workflows[name] = steps
    step_descs = [s.get("description", f"step {i+1}") for i, s in enumerate(steps)]
    return f"Saved workflow **{name}** ({len(steps)} steps):\n" + "\n".join(f"  {i+1}. {d}" for i, d in enumerate(step_descs))


def handle_workflow_list(data: dict) -> str:
    if not _saved_workflows:
        return "No saved workflows."
    lines = ["**Saved Workflows:**\n"]
    for name, steps in _saved_workflows.items():
        lines.append(f"  **{name}** ({len(steps)} steps)")
    return "\n".join(lines)


async def handle_workflow_replay(data: dict, dispatch_fn=None) -> str:
    name = (data.get("app") or "").strip()
    if not name or name not in _saved_workflows:
        available = ", ".join(_saved_workflows.keys()) if _saved_workflows else "none"
        return f"Workflow '{name}' not found. Available: {available}"

    steps = _saved_workflows[name]
    data["reply"] = json.dumps(steps)
    return await handle_workflow_run(data, dispatch_fn)
