import shutil
import subprocess
from pathlib import Path

from config import BASE_FOLDER


def handle_github_push(data: dict) -> str:
    git_folder = data.get("git_folder", "").strip() or BASE_FOLDER
    commit_msg = data.get("git_message", "").strip() or "ZENTRA auto-commit"

    repo_path = Path(git_folder)
    if not repo_path.exists():
        return f"git folder not found: `{git_folder}`"
    if not shutil.which("git"):
        return "`git` is not installed or not on PATH."

    def run_git(*args):
        r = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, cwd=str(repo_path),
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    steps = []

    code, out, err = run_git("add", ".")
    if code != 0:
        return f"`git add` failed:\n```\n{err or out}\n```"
    steps.append("`git add .`")

    code, out, err = run_git("commit", "-m", commit_msg)
    if code != 0:
        msg = (out + err).lower()
        if "nothing to commit" in msg:
            return "Nothing to commit — working tree is already clean."
        return f"`git commit` failed:\n```\n{err or out}\n```"
    steps.append(f"`git commit` — \"{commit_msg}\"")

    code, out, err = run_git("push")
    if code != 0:
        return "\n".join(steps) + f"\n`git push` failed:\n```\n{err or out}\n```"
    steps.append("`git push`")

    return "\n".join(steps) + "\n\nCode pushed successfully!"
