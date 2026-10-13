"""Load the reviewed eight-file example after checking its immutable sources."""

import hashlib
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "skills/specviz/scripts"))

from specviz.core import validate_model
from specviz.discovery import discover


def load_fixture(project=None):
    fixture = REPOSITORY / "tests/fixtures/diagram-first"
    project = Path(project) if project else fixture / "project"
    expected = json.loads((fixture / "content-hashes.json").read_text(encoding="utf-8"))
    actual = {path.relative_to(project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(project.rglob("*")) if path.is_file()}
    if actual != expected:
        raise AssertionError("Diagram fixture changed; review the interpretation before rebinding its snapshot")
    inventory = discover(project)
    model = json.loads((REPOSITORY / "examples/diagram-first/model.json").read_text(encoding="utf-8"))
    model["snapshot"] = inventory["snapshot"]
    validate_model(model, inventory)
    return inventory, model
