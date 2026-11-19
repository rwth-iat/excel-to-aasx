"""PreToolUse(Bash): block commands that destroy irreplaceable data or rewrite history.

Exit 2 blocks the call and returns stderr to Claude. Anything else passes.
"""

import json
import re
import sys

BLOCKED = [
    (
        # `rm` as a command (at the start, after ; & | ( or sudo), not docker's `--rm` flag.
        r"(?:^|[;&|(]\s*|\bsudo\s+)rm\s[^|;&]*\.(xlsx|aasx|pdf)\b",
        "Example Excel/AASX/PDF files are reference fixtures that cannot be regenerated. "
        "Generated output goes to out/ and is removed as a directory. Ask the user first.",
    ),
    (r"\bgit\s+push\b.*(--force|-f\b|--force-with-lease)", "Force-push rewrites shared history."),
    (
        r"\bgit\s+push\b.*\b(main|master)\b",
        "Never push to main. Push the feature branch, merge via PR.",
    ),
    (r"\bgit\s+reset\s+--hard\b", "Hard reset discards work. Ask the user first."),
    (
        r"\bgit\s+clean\b.*-[a-zA-Z]*f",
        "git clean deletes untracked files, fixtures included. Ask the user first.",
    ),
]


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern, reason in BLOCKED:
        if re.search(pattern, command):
            print(f"Blocked by .claude/hooks/guard.py: {reason}", file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
