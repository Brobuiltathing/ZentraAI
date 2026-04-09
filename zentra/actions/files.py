import platform
import shutil
import subprocess
from pathlib import Path

from zentra.config import BASE_FOLDER, LANG_RUNNER, READ_FILE_MAX_CHARS, RUN_TIMEOUT_SECONDS
from zentra.logger import log
from zentra.utils import resolve_file_path, resolve_any_path, ensure_dir, write_file


def handle_create_file(data: dict) -> str:
    content = data.get("content", "").strip()
    if not content:
        content = "# ZENTRA generated file\n"

    base_dir, file_path = resolve_file_path(data)

    err = ensure_dir(base_dir)
    if err:
        return err

    err = write_file(file_path, content)
    if err:
        return err

    log.info(f"File created: {file_path}")
    ext = file_path.suffix.lower()
    return f"File created: `{file_path}`\nLanguage: `{ext or 'unknown'}`"


def handle_run_file(data: dict) -> str:
    content  = data.get("content", "").strip()
    run_args = data.get("run_args", [])
    if not isinstance(run_args, list):
        run_args = []

    if not content:
        return "run_file requires 'content' — no code was provided."

    base_dir, file_path = resolve_file_path(data)

    err = ensure_dir(base_dir)
    if err:
        return err

    err = write_file(file_path, content)
    if err:
        return err

    log.info(f"File written for run: {file_path}")
    ext = file_path.suffix.lower()

    if ext in (".rs", ".java", ".c", ".cpp"):
        return (
            f"File created: `{file_path}`\n\n"
            f"`{ext}` files must be compiled before running."
        )

    if ext == ".bat":
        if platform.system() != "Windows":
            return f"File created: `{file_path}`\n\n`.bat` files only run on Windows."
        cmd = [str(file_path)] + run_args
    elif ext in LANG_RUNNER:
        interpreter = LANG_RUNNER[ext][0]
        if not shutil.which(interpreter):
            return (
                f"File created: `{file_path}`\n\n"
                f"Cannot run — `{interpreter}` not found on PATH."
            )
        cmd = LANG_RUNNER[ext] + [str(file_path)] + run_args
    else:
        return (
            f"File created: `{file_path}`\n\n"
            f"ZENTRA doesn't know how to auto-run `{ext}` files."
        )

    try:
        log.info(f"Running: {' '.join(str(x) for x in cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
            cwd=str(base_dir),
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        code   = result.returncode
        parts  = [f"Created & executed: `{file_path}`"]

        if stdout:
            if len(stdout) > 1200:
                stdout = stdout[:1200] + "\n... (output truncated)"
            parts.append(f"\nOutput:\n```\n{stdout}\n```")

        if stderr:
            if len(stderr) > 800:
                stderr = stderr[:800] + "\n... (truncated)"
            parts.append(f"\nStderr:\n```\n{stderr}\n```")

        if code != 0 and not stderr and not stdout:
            parts.append(f"\nProcess exited with code {code} (no output)")

        return "\n".join(parts)

    except subprocess.TimeoutExpired:
        return (
            f"File created: `{file_path}`\n\n"
            f"Execution killed after {RUN_TIMEOUT_SECONDS} s."
        )
    except FileNotFoundError as exc:
        return f"File created: `{file_path}`\n\nCould not run: {exc}"
    except Exception as exc:
        log.error(f"run_file unexpected error: {exc}", exc_info=True)
        return f"File created: `{file_path}`\n\nUnexpected error: {exc}"


def handle_read_file(data: dict) -> tuple[str, str]:
    filename = data.get("filename", "").strip()
    if not filename:
        return "read_file: no filename provided.", ""

    file_path = resolve_any_path(filename)
    if not file_path.exists():
        return f"File not found: `{file_path}`", ""

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Could not read `{file_path}`: {exc}", ""

    size      = len(content)
    truncated = False
    if size > READ_FILE_MAX_CHARS:
        content   = content[:READ_FILE_MAX_CHARS]
        truncated = True

    lines     = content.count("\n") + 1
    trunc_msg = f"\nFile truncated to {READ_FILE_MAX_CHARS:,} chars for context." if truncated else ""
    msg       = f"Read `{file_path}` — {lines} lines, {size:,} chars{trunc_msg}"
    log.info(f"File read: {file_path} ({size} chars)")
    return msg, content


def handle_edit_file(data: dict) -> str:
    filename = data.get("filename", "").strip()
    patches  = data.get("patches", [])

    if not filename:
        return "edit_file: no filename provided."
    if not patches or not isinstance(patches, list):
        return "edit_file: no patches provided."

    file_path = resolve_any_path(filename)
    if not file_path.exists():
        return f"File not found: `{file_path}`"

    try:
        original = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Could not read `{file_path}`: {exc}"

    content     = original
    applied     = 0
    failed_msgs = []

    for i, patch in enumerate(patches):
        old = patch.get("old", "")
        new = patch.get("new", "")
        if not old:
            failed_msgs.append(f"  Patch {i+1}: empty 'old' field — skipped.")
            continue
        occurrences = content.count(old)
        if occurrences == 0:
            failed_msgs.append(f"  Patch {i+1}: text not found in file — skipped.")
            log.warning(f"edit_file patch {i+1}: text not found: {old[:60]!r}")
            continue
        if occurrences > 1:
            failed_msgs.append(f"  Patch {i+1}: text found {occurrences}x (ambiguous) — skipped.")
            continue
        content = content.replace(old, new, 1)
        applied += 1
        log.info(f"edit_file patch {i+1} applied to {file_path.name}")

    if applied == 0:
        return "No patches could be applied.\n" + "\n".join(failed_msgs)

    err = write_file(file_path, content)
    if err:
        return err

    lines_before = original.count("\n") + 1
    lines_after  = content.count("\n")  + 1
    delta        = lines_after - lines_before
    delta_str    = f"+{delta}" if delta >= 0 else str(delta)

    result = (
        f"Edited `{file_path}`\n"
        f"   {applied}/{len(patches)} patch(es) applied  |  "
        f"{lines_before} -> {lines_after} lines ({delta_str})"
    )
    if failed_msgs:
        result += "\nSome patches failed:\n" + "\n".join(failed_msgs)
    return result


def handle_scaffold_project(data: dict) -> str:
    files  = data.get("files", [])
    folder = data.get("folder", "").strip()

    if not files or not isinstance(files, list):
        return "scaffold_project: no files list provided."

    base_dir = Path(BASE_FOLDER) / folder if folder else Path(BASE_FOLDER)
    created  = []
    errors   = []

    for entry in files:
        if not isinstance(entry, dict):
            continue
        fname     = entry.get("filename", "").strip()
        subfolder = entry.get("folder", "").strip()
        content   = entry.get("content", "")

        if not fname:
            errors.append("  An entry had no filename — skipped.")
            continue

        file_dir  = base_dir / subfolder if subfolder else base_dir
        file_path = file_dir / fname

        err = ensure_dir(file_dir)
        if err:
            errors.append(f"  {fname}: {err}")
            continue

        err = write_file(file_path, content or f"# {fname}\n")
        if err:
            errors.append(f"  {fname}: {err}")
            continue

        created.append(f"  `{file_path.relative_to(Path(BASE_FOLDER))}`")
        log.info(f"Scaffolded: {file_path}")

    summary = (
        f"Project scaffolded in `{base_dir}`\n"
        f"Created {len(created)} file(s):\n"
        + "\n".join(created)
    )
    if errors:
        summary += "\n\nErrors:\n" + "\n".join(errors)
    return summary
