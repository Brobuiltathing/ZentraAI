import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

from config import (
    PYAUTOGUI_AVAILABLE, SCREENSHOT_FOLDER,
    MAX_SCREEN_ACTIONS, SCREEN_ACTION_DELAY, OLLAMA_VISION_MODEL,
)
from logger import log
from ollama import ollama_vision_sync

if PYAUTOGUI_AVAILABLE:
    import pyautogui
    import PIL.Image
    import PIL.ImageGrab
    import io
    import base64


def _take_screenshot_sync() -> tuple[str, str]:
    Path(SCREENSHOT_FOLDER).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    save_path = os.path.join(SCREENSHOT_FOLDER, f"screen_{timestamp}.png")

    if PYAUTOGUI_AVAILABLE:
        screenshot = pyautogui.screenshot()
    else:
        screenshot = PIL.ImageGrab.grab()

    w, h = screenshot.size
    max_dim = 1280
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        screenshot = screenshot.resize(
            (int(w * ratio), int(h * ratio)),
            PIL.Image.LANCZOS,
        )

    screenshot.save(save_path, "PNG")

    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    log.info(f"Screenshot taken: {save_path} ({w}x{h} -> {screenshot.size})")
    return b64, save_path


def _vision_plan_actions_sync(
    image_b64: str,
    goal: str,
    screen_w: int,
    screen_h: int,
    previous_actions: list[dict] | None = None,
) -> list[dict]:
    prev_str = ""
    if previous_actions:
        prev_str = (
            "\n\nActions already performed:\n"
            + json.dumps(previous_actions, indent=2)
            + "\n\nLook at the current screenshot and decide what to do next."
        )

    prompt = f"""You are a precise screen automation assistant.
Screen resolution: {screen_w}x{screen_h} pixels.
Goal: {goal}{prev_str}

Analyse this screenshot carefully. Return ONLY a raw JSON array of actions — no explanation, no markdown.

Available action types:
  {{"type":"click",        "x":<int>, "y":<int>}}
  {{"type":"double_click", "x":<int>, "y":<int>}}
  {{"type":"right_click",  "x":<int>, "y":<int>}}
  {{"type":"move",         "x":<int>, "y":<int>}}
  {{"type":"drag",         "x1":<int>,"y1":<int>,"x2":<int>,"y2":<int>}}
  {{"type":"scroll",       "x":<int>, "y":<int>, "clicks":<int>}}
  {{"type":"type",         "text":"<string>"}}
  {{"type":"key",          "key":"<pyautogui key>"}}
  {{"type":"hotkey",       "keys":["<key1>","<key2>"]}}
  {{"type":"wait",         "seconds":<float>}}
  {{"type":"screenshot"}}
  {{"type":"done",         "message":"<what was accomplished>"}}

Rules:
- Be precise with coordinates — click the centre of UI elements
- Use "screenshot" to verify state before and after important actions
- Use "wait" after clicks that open menus/dialogs (0.3-1.0 seconds)
- Use "key":"escape" to dismiss unintended popups
- Include "done" as the last action with a description of what was accomplished
- If the goal is already achieved in the screenshot, return [{{"type":"done","message":"Already done: <reason>"}}]
- ONLY return the JSON array, nothing else"""

    raw = ollama_vision_sync(image_b64, prompt, max_tokens=800)
    log.info(f"Vision plan (raw): {raw[:400]}")

    raw_clean = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
    for text in [raw_clean, raw]:
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        m = re.search(r"\[[\s\S]*\]", text)
        if m:
            try:
                parsed = json.loads(m.group(0))
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

    log.warning("Vision model returned no parsable action list.")
    return [{"type": "done", "message": "Could not plan actions from screenshot."}]


def _execute_screen_actions_sync(
    actions: list[dict],
    screen_w: int,
    screen_h: int,
    goal: str,
    use_vision: bool = True,
) -> dict:
    if not PYAUTOGUI_AVAILABLE:
        return {
            "actions_taken": [],
            "screenshots":   [],
            "final_message": "",
            "error": (
                "`pyautogui` is not installed.\n"
                "Run: `pip install pyautogui pillow` then restart ZENTRA."
            ),
        }

    result = {
        "actions_taken": [],
        "screenshots":   [],
        "final_message": "",
        "error":         "",
    }

    def clamp(val: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, val))

    executed_count = 0

    for i, action in enumerate(actions[:MAX_SCREEN_ACTIONS]):
        atype = action.get("type", "").lower()
        log.info(f"Screen action [{i+1}]: {action}")

        try:
            if atype == "done":
                result["final_message"] = action.get("message", "Task completed.")
                result["actions_taken"].append({"type": "done", "message": result["final_message"]})
                break

            elif atype == "click":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.click(x, y)
                result["actions_taken"].append({"type": "click", "x": x, "y": y})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "double_click":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.doubleClick(x, y)
                result["actions_taken"].append({"type": "double_click", "x": x, "y": y})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "right_click":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.rightClick(x, y)
                result["actions_taken"].append({"type": "right_click", "x": x, "y": y})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "move":
                x = clamp(int(action["x"]), 0, screen_w - 1)
                y = clamp(int(action["y"]), 0, screen_h - 1)
                pyautogui.moveTo(x, y, duration=0.2)
                result["actions_taken"].append({"type": "move", "x": x, "y": y})

            elif atype == "drag":
                x1 = clamp(int(action["x1"]), 0, screen_w - 1)
                y1 = clamp(int(action["y1"]), 0, screen_h - 1)
                x2 = clamp(int(action["x2"]), 0, screen_w - 1)
                y2 = clamp(int(action["y2"]), 0, screen_h - 1)
                pyautogui.moveTo(x1, y1, duration=0.15)
                pyautogui.dragTo(x2, y2, duration=0.4, button="left")
                result["actions_taken"].append({"type": "drag", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
                time.sleep(SCREEN_ACTION_DELAY)

            elif atype == "scroll":
                x      = clamp(int(action.get("x", screen_w // 2)), 0, screen_w - 1)
                y      = clamp(int(action.get("y", screen_h // 2)), 0, screen_h - 1)
                clicks = int(action.get("clicks", 3))
                pyautogui.scroll(clicks, x=x, y=y)
                result["actions_taken"].append({"type": "scroll", "x": x, "y": y, "clicks": clicks})
                time.sleep(0.2)

            elif atype == "type":
                text = str(action.get("text", ""))
                pyautogui.typewrite(text, interval=0.03)
                result["actions_taken"].append({"type": "type", "text": text})
                time.sleep(0.1)

            elif atype == "key":
                key = str(action.get("key", ""))
                if key:
                    pyautogui.press(key)
                    result["actions_taken"].append({"type": "key", "key": key})
                    time.sleep(0.1)

            elif atype == "hotkey":
                keys = action.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)
                    result["actions_taken"].append({"type": "hotkey", "keys": keys})
                    time.sleep(0.15)

            elif atype == "wait":
                secs = float(action.get("seconds", 0.5))
                secs = min(secs, 10.0)
                time.sleep(secs)
                result["actions_taken"].append({"type": "wait", "seconds": secs})

            elif atype == "screenshot":
                b64, path = _take_screenshot_sync()
                result["screenshots"].append(path)
                result["actions_taken"].append({"type": "screenshot", "path": path})
                log.info(f"Mid-action screenshot: {path}")

                if use_vision and i < len(actions) - 1:
                    remaining_goal = f"Continue: {goal}"
                    new_plan = _vision_plan_actions_sync(
                        b64, remaining_goal, screen_w, screen_h,
                        previous_actions=result["actions_taken"]
                    )
                    if new_plan:
                        actions = result["actions_taken"] + new_plan
                        log.info(f"Re-planned after screenshot: {len(new_plan)} new action(s)")

            else:
                log.warning(f"Unknown screen action type: {atype}")

            executed_count += 1

        except pyautogui.FailSafeException:
            result["error"] = (
                "PyAutoGUI failsafe triggered — mouse moved to screen corner.\n"
                "Move mouse away from the corner to resume."
            )
            break
        except Exception as exc:
            log.error(f"Screen action error ({atype}): {exc}", exc_info=True)
            result["error"] = f"Action `{atype}` failed: {exc}"
            break

    if not result["final_message"] and not result["error"]:
        result["final_message"] = f"Executed {executed_count} screen action(s)."

    return result


def handle_screen_action_sync(data: dict) -> str:
    if not PYAUTOGUI_AVAILABLE:
        return (
            "Screen automation libraries not installed.\n"
            "Run: `pip install pyautogui pillow` then restart ZENTRA.\n"
            "On Linux you may also need: `sudo apt install python3-tk python3-dev`"
        )

    goal           = (data.get("screen_goal") or data.get("reply") or "").strip()
    preset_actions = data.get("screen_actions", [])
    if not isinstance(preset_actions, list):
        preset_actions = []

    if not goal and not preset_actions:
        return "screen_action: provide a goal or action list."

    screen_w, screen_h = pyautogui.size()
    log.info(f"Screen resolution: {screen_w}x{screen_h}")

    try:
        b64, initial_path = _take_screenshot_sync()
    except Exception as exc:
        return f"Could not take screenshot: {exc}"

    actions = preset_actions
    if not actions and goal:
        log.info("No preset actions — planning via vision model...")
        actions = _vision_plan_actions_sync(b64, goal, screen_w, screen_h)
        if not actions:
            return (
                "Vision model could not plan actions from the screenshot.\n"
                f"Make sure `{OLLAMA_VISION_MODEL}` is pulled: "
                f"`ollama pull {OLLAMA_VISION_MODEL}`"
            )

    log.info(f"Executing {len(actions)} screen action(s) for goal: {goal}")

    exec_result = _execute_screen_actions_sync(
        actions, screen_w, screen_h, goal, use_vision=(not preset_actions)
    )

    try:
        _, final_path = _take_screenshot_sync()
        exec_result["screenshots"].append(final_path)
    except Exception:
        pass

    parts = []

    if goal:
        parts.append(f"**Screen Action** — *{goal}*")
    else:
        parts.append("**Screen Action**")

    parts.append(f"Screen: {screen_w}x{screen_h}")
    parts.append(f"Initial screenshot: `{initial_path}`")

    if exec_result["actions_taken"]:
        action_lines = []
        for act in exec_result["actions_taken"]:
            atype = act.get("type", "?")
            if atype == "click":
                action_lines.append(f"  Click ({act['x']}, {act['y']})")
            elif atype == "double_click":
                action_lines.append(f"  Double-click ({act['x']}, {act['y']})")
            elif atype == "right_click":
                action_lines.append(f"  Right-click ({act['x']}, {act['y']})")
            elif atype == "move":
                action_lines.append(f"  Move -> ({act['x']}, {act['y']})")
            elif atype == "drag":
                action_lines.append(f"  Drag ({act['x1']},{act['y1']}) -> ({act['x2']},{act['y2']})")
            elif atype == "scroll":
                direction = "up" if act["clicks"] > 0 else "down"
                action_lines.append(f"  Scroll {direction} {abs(act['clicks'])}x at ({act['x']},{act['y']})")
            elif atype == "type":
                text_preview = act["text"][:40] + ("..." if len(act["text"]) > 40 else "")
                action_lines.append(f"  Type: `{text_preview}`")
            elif atype == "key":
                action_lines.append(f"  Key: `{act['key']}`")
            elif atype == "hotkey":
                action_lines.append(f"  Hotkey: `{'+'.join(act['keys'])}`")
            elif atype == "wait":
                action_lines.append(f"  Wait {act['seconds']}s")
            elif atype == "screenshot":
                action_lines.append(f"  Screenshot -> `{act.get('path', '?')}`")
            elif atype == "done":
                action_lines.append(f"  Done: {act.get('message', '')}")
        parts.append("**Actions executed:**\n" + "\n".join(action_lines))

    if exec_result["screenshots"]:
        last_ss = exec_result["screenshots"][-1]
        parts.append(f"Final screenshot: `{last_ss}`")

    if exec_result["final_message"]:
        parts.append(f"**Result:** {exec_result['final_message']}")

    if exec_result["error"]:
        parts.append(exec_result["error"])

    return "\n".join(parts)
