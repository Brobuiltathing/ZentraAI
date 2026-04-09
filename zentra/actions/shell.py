import subprocess
import platform

from zentra.config import RUN_TIMEOUT_SECONDS
from zentra.logger import log


def handle_shell(data: dict) -> str:
    command = (data.get("content") or data.get("reply") or "").strip()
    cwd = data.get("folder", "").strip() or None

    if not command:
        return "shell: no command provided."

    system = platform.system()
    if system == "Windows":
        shell_cmd = ["powershell", "-NoProfile", "-Command", command]
    else:
        shell_cmd = ["bash", "-c", command]

    log.info(f"Shell exec: {command} (cwd={cwd})")

    try:
        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS * 2,
            cwd=cwd,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        code = result.returncode

        parts = [f"$ {command}"]

        if stdout:
            if len(stdout) > 2000:
                stdout = stdout[:2000] + "\n... (truncated)"
            parts.append(f"\n```\n{stdout}\n```")

        if stderr:
            if len(stderr) > 1000:
                stderr = stderr[:1000] + "\n... (truncated)"
            parts.append(f"\nstderr:\n```\n{stderr}\n```")

        if code != 0:
            parts.append(f"\nexit code: {code}")
        else:
            if not stdout and not stderr:
                parts.append("\n(completed with no output)")

        return "\n".join(parts)

    except subprocess.TimeoutExpired:
        return f"$ {command}\n\nkilled after {RUN_TIMEOUT_SECONDS * 2}s timeout"
    except FileNotFoundError:
        return f"shell not found. command: {command}"
    except Exception as exc:
        log.error(f"Shell exec error: {exc}", exc_info=True)
        return f"shell error: {exc}"
