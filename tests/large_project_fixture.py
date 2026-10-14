"""Load the synthetic large-project interpretation against pinned sources."""

import hashlib
import json
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "skills/specviz/scripts"))
from specviz.core import validate_model
from specviz.discovery import discover


def load_fixture(project=None):
    fixture = REPOSITORY / "tests/fixtures/large-project"
    project = Path(project) if project else fixture / "project"
    expected = json.loads((fixture / "content-hashes.json").read_text(encoding="utf-8"))
    actual = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(project.rglob("*")) if p.is_file()}
    if actual != expected:
        raise AssertionError("Large fixture changed; review its interpretation before rebinding")
    inventory = discover(project)
    model = json.loads((REPOSITORY / "examples/large-project/model.json").read_text(encoding="utf-8"))
    model["snapshot"] = inventory["snapshot"]
    validate_model(model, inventory)
    return inventory, model
