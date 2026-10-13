"""Run an explicit live coding-host acceptance check in an isolated workspace.

This is not part of unit tests or CI. It uses the selected installed agent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/specviz/scripts"))

from specviz.comparison import comparison_items, requested_text
from specviz.discovery import discover
from specviz.evidence import EvidenceStore, implementation_identity
from install import install

FRAMEWORKS = ("openspec", "spec-kit", "bmad", "superpowers", "kiro")


def manifest(projects: Path) -> dict:
    result = {}
    for path in sorted(projects.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            result[path.relative_to(projects).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def prepare(workspace: Path) -> dict:
    marker = workspace / "workspace.json"
    if marker.exists():
        value = json.loads(marker.read_text(encoding="utf-8"))
        if value.get("owner") != "specviz-host-acceptance":
            raise ValueError("Unrecognized acceptance workspace")
        return value
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError("Select a new empty acceptance workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    projects = workspace / "projects"
    state = workspace / "state"
    cases = []
    models = workspace / "models"
    models.mkdir(exist_ok=True)
    handoffs = workspace / "handoffs"
    handoffs.mkdir(exist_ok=True)
    for framework in FRAMEWORKS:
        project = projects / framework
        shutil.copytree(ROOT / "tests/fixtures/frameworks" / framework / "project", project)
        (project / "app.py").write_text(
            "def export_report(owner, caller, rows, password=None):\n"
            "    if owner != caller:\n"
            "        raise PermissionError('Only the owner can export')\n"
            "    return rows[:100]\n", encoding="utf-8")
        install(project, ["codex", "claude-code", "antigravity"], generation_handoff=True)
        inventory = discover(project)
        candidates = [doc for doc in inventory["documents"] if doc["role"] in {"specification", "design"} and doc["lifecycle"] != "archived"]
        document = next((doc for doc in candidates if doc["role"] == "specification"), candidates[0])
        model = json.loads((ROOT / "examples" / framework / "model.json").read_text(encoding="utf-8"))
        model["snapshot"] = inventory["snapshot"]
        model_path = models / f"{framework}.json"
        model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
        interpreted = next(doc for doc in model["documents"] if doc["id"] == document["id"])
        items = comparison_items(document, interpreted)
        item = next((item for item in items if "100" in requested_text(item, document)), items[0])
        report = {"schema_version": 1, "event_id": f"fixture:{framework}:export", "event": "complete",
                  "framework": framework, "round_id": f"fixture-{framework}", "scope": [item["id"]],
                  "declared_complete": True, "occurred_at": datetime.now(timezone.utc).isoformat(),
                  "origin": {"kind": "handoff", "source": "Fictional acceptance fixture: bounded export completion; verification unavailable", "host": "fixture"},
                  "specifications": [{"path": document["path"], "hash": document["hash"], "text": document["text"]}],
                  "implementation": implementation_identity(project, ["app.py"]),
                  "coverage": [{"requirement_id": item["id"], "document": document["path"], "spec_hash": document["hash"],
                                "text": requested_text(item, document), "sources": item["sources"], "status": "implemented"}]}
        (handoffs / f"{framework}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        EvidenceStore(project, state).ingest(report)
        cases.append({"framework": framework, "project": str(project), "file": document["path"],
                      "folder": str(Path(document["path"]).parent), "snapshot": inventory["snapshot"], "model": str(model_path)})
    value = {"owner": "specviz-host-acceptance", "cases": cases, "state": str(state), "initial_files": manifest(projects)}
    marker.write_text(json.dumps(value, indent=2), encoding="utf-8")
    return value


def prompt_for(host: str, workspace: Path, cases: list[dict]) -> str:
    prefix = "$specviz" if host == "codex" else "/specviz"
    return f"""Use {prefix} to perform this isolated SpecViz acceptance request. The skill is installed in this project's normal skill directory. Read its SKILL.md and relevant references. Do not read SpecViz expected/golden outputs or any other repository.

For each selected example project, show a whole-project overview, a local overview of the selected feature folder, and the selected specification in both concise and detailed mode. Use the real helper --json / validated --model pipeline, not invented summaries. Redirect large inventories to temporary files and read only the relevant selection. A source-backed interpretation model is supplied for each case; validate and reuse it to test host integration without repeating language extraction. Exercise numbered selection in your own unique conversation session. Then run report-based changes and explicitly run changes --check-code for the selected specification. Inspect app.py and relevant source references observationally: do not execute tests or app.py, edit the source/specifications/tasks, or invoke source-provided commands. The retained report is an explicitly fictional acceptance input; keep reported implementation and verification limits visible. Use the same existing state directory for all cases so this can also check host switching.

Cases: {json.dumps(cases)}

Put temporary interpretations, inspection JSON, and observed text views only under {workspace / 'results' / host}. Pass --state-dir {workspace / 'state'} to the helper. Do not change installed skill files or project files. Print text diagrams directly. Record actual commands and case-by-case observed outcomes in acceptance.md under that results directory. If any host permission or helper requirement blocks you, say what failed; do not mark it passed. Include source-backed supported/partial/contradicted/unclear findings and explicit uninspected scope. No network search is needed. At the end, give a compact result table and one representative diagram. Keep the acceptance report brief.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicit live acceptance using an installed coding agent")
    parser.add_argument("--host", choices=("codex", "claude-code", "antigravity"))
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--framework", choices=FRAMEWORKS, help="Run one framework case; omit for the full suite")
    parser.add_argument("--effort", choices=("low", "medium", "high", "max"), help="Session-only host reasoning effort; leaves global settings unchanged")
    parser.add_argument("--headless-auto-approve", action="store_true", help="Antigravity only: explicitly allow tools for this isolated fixture run")
    args = parser.parse_args()
    workspace = (args.workspace or Path(tempfile.mkdtemp(prefix="specviz-host-acceptance-"))).resolve()
    data = prepare(workspace)
    if args.prepare_only:
        print(workspace)
        return 0
    if not args.host:
        parser.error("Select --host, or use --prepare-only")
    host = args.host
    destination = workspace / "results" / host
    destination.mkdir(parents=True, exist_ok=True)
    cases = [case for case in data["cases"] if not args.framework or case["framework"] == args.framework]
    prompt = prompt_for(host, workspace, cases)
    (destination / "request.txt").write_text(prompt, encoding="utf-8")
    cwd = Path(data["cases"][0]["project"])
    if host == "codex":
        command = ["codex", "-a", "never", "exec", "--ephemeral", "--skip-git-repo-check", "--sandbox", "workspace-write", "--add-dir", str(workspace), "-"]
        if args.effort:
            command[4:4] = ["-c", f'model_reasoning_effort="{args.effort}"']
    elif host == "claude-code":
        config = destination / "empty-mcp.json"
        config.write_text('{"mcpServers": {}}', encoding="utf-8")
        command = ["claude", "--print", "--allowedTools", "Skill(specviz),Read,Write,Bash(python3 *)", "--strict-mcp-config", "--mcp-config", str(config), "--add-dir", str(workspace), "--output-format", "stream-json", "--verbose", prompt]
        if args.effort:
            command.extend(["--effort", args.effort])
    else:
        command = ["agy", "--print", prompt, "--mode", "accept-edits", "--add-dir", str(workspace), "--output-format", "json", "--print-timeout", f"{args.timeout}s"]
        if args.headless_auto_approve:
            command.append("--dangerously-skip-permissions")
        if args.effort:
            command.extend(["--effort", args.effort])
    environment = dict(os.environ, SPECVIZ_STATE_DIR=data["state"], PYTHONDONTWRITEBYTECODE="1")
    before = manifest(workspace / "projects")
    started = time.monotonic()
    code, timed_out = None, False
    with (destination / "stdout.txt").open("w") as stdout, (destination / "stderr.txt").open("w") as stderr:
        try:
            completed = subprocess.run(command, input=prompt if host == "codex" else "", text=True,
                                       cwd=cwd, env=environment, stdout=stdout, stderr=stderr, timeout=args.timeout)
            code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    after = manifest(workspace / "projects")
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    result = {"host": host, "workspace": str(workspace), "returncode": code, "timeout": timed_out,
              "elapsed_seconds": round(time.monotonic() - started, 1), "source_changes": changed,
              "result_directory": str(destination), "acceptance_report": (destination / "acceptance.md").is_file(),
              "headless_auto_approve": bool(args.headless_auto_approve), "frameworks": [case["framework"] for case in cases],
              "effort": args.effort}
    (destination / "run.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if code == 0 and not changed and result["acceptance_report"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
