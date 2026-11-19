"""Stop: don't call it done while pytest fails.

Runs only when Python files under src/ or tests/ changed (or always, before git init).
Loop-guarded: fires at most once per stop, so a test you cannot fix never traps the session.
"""

import json
import subprocess
import sys

from lib.config import REPO_ROOT
from lib.run_local_bin import run_local_bin


def python_changed() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", "src", "tests"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return True  # not a git repo yet: cannot tell, so check
    return any(line.endswith(".py") for line in result.stdout.splitlines())


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        if payload.get("stop_hook_active") is True:
            return 0
        if not (REPO_ROOT / "tests").is_dir() or not python_changed():
            return 0
        result = run_local_bin("pytest", ["-q", "-x"])
        if not result.installed or result.ok or "no tests ran" in result.output:
            return 0
        tail = "\n".join(result.output.splitlines()[-40:])
        sys.stderr.write(f"Tests failing after your changes:\n\n{tail}\n")
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
