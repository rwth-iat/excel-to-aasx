"""SessionStart: inject a compact map of the project.

A session opens knowing the shape and the standing decisions, instead of discovering both by
globbing. Budget: ~60 lines of output. If it grows past that it stops being read.
"""

import json
import re
import subprocess
import sys
from typing import Any

from lib.config import REPO_ROOT, is_in_scope, load_architecture

MAX_FILES_LISTED = 24
DECISIONS_DIR = REPO_ROOT / "docs" / "decisions"


def loc_of(rel_path: str) -> int:
    try:
        return len((REPO_ROOT / rel_path).read_text(encoding="utf-8").splitlines())
    except OSError:
        return 0


def module_map(arch: dict[str, Any]) -> list[str]:
    src = REPO_ROOT / "src"
    files = sorted(
        rel
        for p in src.rglob("*.py")
        if is_in_scope(rel := p.relative_to(REPO_ROOT).as_posix(), arch)
    )
    if not files:
        return ["  (no source files yet - skeleton only)"]

    soft, hard = arch["budgets"]["fileLocSoft"], arch["budgets"]["fileLocHard"]
    sized = sorted(((loc_of(f), f) for f in files), reverse=True)
    rows = []
    for loc, f in sized[:MAX_FILES_LISTED]:
        flag = (
            "  <-- OVER HARD BUDGET"
            if loc > hard
            else "  <-- over soft budget"
            if loc > soft
            else ""
        )
        rows.append(f"  {loc:>4}  {f}{flag}")
    if len(files) > MAX_FILES_LISTED:
        rows.append(
            f"  ...   {len(files) - MAX_FILES_LISTED} more (largest {MAX_FILES_LISTED} shown)"
        )
    return rows


def decisions() -> list[str]:
    if not DECISIONS_DIR.is_dir():
        return ["  (none recorded yet)"]
    entries = sorted(p for p in DECISIONS_DIR.iterdir() if re.match(r"^\d{4}-.*\.md$", p.name))
    if not entries:
        return ["  (none recorded yet)"]

    rows = []
    for path in entries:
        title, status = path.name, "?"
        try:
            text = path.read_text(encoding="utf-8")
            if found := re.search(r"^#\s+(.+)$", text, re.MULTILINE):
                title = found.group(1).strip()
            if found := re.search(
                r"^[*\-\s]*Status[:*\s]+(.+)$", text, re.MULTILINE | re.IGNORECASE
            ):
                status = found.group(1).replace("*", "").strip()
        except OSError:
            pass
        flag = (
            "  <-- revisit" if re.search(r"provisional|proposed|superseded", status, re.I) else ""
        )
        rows.append(f"  {title}  [{status}]{flag}")
    return rows


def git_state() -> list[str]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else ""

    branch = git("branch", "--show-current")
    if not branch and not git("rev-parse", "--git-dir"):
        return ["  (not a git repository yet)"]
    changed = git("status", "--short").splitlines()
    rows = [f"  branch {branch or '(detached)'}, {len(changed)} changed path(s)"]
    rows += [f"  {line}" for line in git("log", "--oneline", "-5").splitlines()]
    return rows


def main() -> None:
    arch = load_architecture()
    lines = [
        "PROJECT MAP (auto-injected; prefer this over globbing)",
        "",
        "excel-to-aasx: Excel -> AASX converter (reference: AASX Package Explorer importer);",
        "later AASX -> AsciiDoc + web editor with live PDF preview. Scope: CLAUDE.md.",
        "Rules: CLAUDE.md - Layer config: .claude/architecture.json",
        "Imports point inward: domain <- ports <- app <- adapters <- main.py",
        "",
        "SOURCE (lines, largest first):",
        *module_map(arch),
        "",
        "DECISIONS ON RECORD (docs/decisions/):",
        *decisions(),
        "",
        "GIT:",
        *git_state(),
    ]
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    main()
