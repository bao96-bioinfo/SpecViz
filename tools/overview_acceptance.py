"""Exercise an ordinary installed overview in an isolated coding-host project.

Explicit live check only: this can use the reader's configured agent account.
Review the recorded chat response; process success is not readability evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from install import install

ROOT = Path(__file__).resolve().parents[1]


def snapshot(project):
    return {
        p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in project.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host", choices=("codex", "claude-code", "antigravity"), required=True
    )
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    workspace = (
        args.workspace or Path(tempfile.mkdtemp(prefix="specviz-overview-"))
    ).resolve()
    if workspace.exists() and any(workspace.iterdir()):
        parser.error("Select a new empty workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    project = workspace / "project"
    shutil.copytree(ROOT / "tests/fixtures/large-project/project", project)
    install(project, [args.host], user_dir=workspace / "installer-home")
    results = workspace / "results"
    results.mkdir()
    prefix = "$specviz" if args.host == "codex" else "/specviz"
    prompt = (
        f"{prefix} overview\n\nUse the installed skill in this project. "
        "Show the full overview, continuing its parts so I can choose a file from the complete key. "
        "Keep specification files unchanged. Put temporary interpretation records under "
        f"{results}; use --state-dir {workspace / 'state'} for helper state. "
        "Use only this project and the installed skill; no external examples or expected outputs."
    )
    (results / "request.txt").write_text(prompt, encoding="utf-8")
    if args.host == "codex":
        command = [
            "codex",
            "-a",
            "never",
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--add-dir",
            str(workspace),
            "-",
        ]
    elif args.host == "claude-code":
        config = results / "empty-mcp.json"
        config.write_text('{"mcpServers":{}}')
        command = [
            "claude",
            "--print",
            "--allowedTools",
            "Skill(specviz),Read,Write,Bash(python3 *)",
            "--strict-mcp-config",
            "--mcp-config",
            str(config),
            "--add-dir",
            str(workspace),
            "--output-format",
            "stream-json",
            "--verbose",
            prompt,
        ]
    else:
        command = [
            "agy",
            "--print",
            prompt,
            "--mode",
            "accept-edits",
            "--sandbox",
            "--add-dir",
            str(workspace),
            "--output-format",
            "json",
            "--print-timeout",
            f"{args.timeout}s",
        ]
    before = snapshot(project)
    started = time.monotonic()
    code = None
    error = None
    with (
        (results / "stdout.txt").open("w") as stdout,
        (results / "stderr.txt").open("w") as stderr,
    ):
        try:
            code = subprocess.run(
                command,
                input=prompt if args.host == "codex" else "",
                text=True,
                cwd=project,
                env=dict(
                    os.environ,
                    SPECVIZ_STATE_DIR=str(workspace / "state"),
                    PYTHONDONTWRITEBYTECODE="1",
                ),
                stdout=stdout,
                stderr=stderr,
                timeout=args.timeout,
            ).returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = type(exc).__name__
    after = snapshot(project)
    result = {
        "host": args.host,
        "returncode": code,
        "error": error,
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "source_changes": sorted(
            p for p in set(before) | set(after) if before.get(p) != after.get(p)
        ),
        "review_required": True,
        "workspace": str(workspace),
    }
    (results / "run.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if code == 0 and not result["source_changes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
