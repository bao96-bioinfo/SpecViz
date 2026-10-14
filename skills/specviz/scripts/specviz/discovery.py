"""Read-only specification discovery with explicit project and document scope.

Adapters call :class:`InventoryBuilder` methods; they never execute project
configuration or treat a discovered document as implementation evidence.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib
from urllib.parse import unquote, urlparse

from .core import project_identity, snapshot_file, source_path


class DiscoveryError(ValueError):
    """A requested project or selection is absent or ambiguous."""


EXCLUDED = frozenset({
    ".git", ".hg", ".svn", ".agents", ".agent", ".claude", ".gemini",
    "node_modules", "vendor", ".venv", "venv", "__pycache__", ".specviz",
    ".cache", "dist", "build", "site-packages",
})
MARKERS = (".git", "openspec", ".specify", "_bmad", ".kiro", "docs/superpowers")
FRAMEWORK_LAYOUTS = {
    "openspec": {"id": "openspec/repository", "version": 1, "upstream_commit": "9111a7654d7800391459431fff4eaf66e33a3d2e"},
    "spec-kit": {"id": "spec-kit/features", "version": 1, "upstream_commit": "6c62e10d5ab1d676c557eb2d0cee86be52c893d2"},
    "bmad": {"id": "bmad/toml-ticket-tree", "version": 1, "upstream_commit": "9f1987169a2e5626e5ccb31bb9cee051fdb3df20"},
    "superpowers": {"id": "superpowers/designs-and-plans", "version": 1, "upstream_commit": "bb92a77741419a4ab5f06e711a283343f1ada0c3"},
    "kiro": {"id": "kiro/feature-specs", "version": 1, "upstream_version": "IDE 0.12"},
    "generic": {"id": "markdown/generic", "version": 1},
}


def _id(*parts):
    return hashlib.sha256("\0".join(map(str, parts)).encode()).hexdigest()[:24]


def _inside(path, root):
    return path == root or root in path.parents


def resolve_project(project=None, cwd=None):
    """Resolve an explicit root or the nearest repository/framework boundary.

    No feature pointer or active initiative is used to reduce project scope.
    Without a known ancestor, the working directory is an explicit local root.
    """
    working = Path(cwd or Path.cwd()).expanduser().resolve()
    chosen = project if project is not None else os.environ.get("SPECIFY_INIT_DIR")
    if chosen is not None:
        path = Path(chosen).expanduser()
        path = path if path.is_absolute() else working / path
        path = path.resolve()
        if not path.is_dir():
            raise DiscoveryError(f"Project directory unavailable: {path}")
        return path
    if not working.is_dir():
        raise DiscoveryError(f"Working directory unavailable: {working}")
    for ancestor in (working, *working.parents):
        if any((ancestor / marker).exists() for marker in MARKERS):
            return ancestor
    # A bare specs/ directory is a weaker signal than an actual project marker;
    # OpenSpec change directories also contain specs/, but are not projects.
    for ancestor in (working, *working.parents):
        if (ancestor / "specs").is_dir() and any(
            p.is_dir() and (p / "spec.md").is_file()
            for p in (ancestor / "specs").iterdir()
        ):
            return ancestor
    return working


def _yaml_scalars(path, fields, warnings):
    """Read only documented top-level scalar/list fields; preserve limitations.

    This deliberately is not a YAML implementation. Irrelevant context/rules
    are not interpreted; relevant aliases, tags, mappings and block values are
    reported rather than expanded or evaluated.
    """
    result = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        warnings.append(f"Configuration unreadable: {path}: {exc}")
        return result
    list_key = None
    for line_number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([\w-]+):\s*(.*?)\s*$", line)
        if match:
            list_key = None
            key, value = match.groups()
            if key not in fields:
                continue
            if not value:
                result[key] = []
                list_key = key
                continue
        elif list_key and re.match(r"^\s+-\s+", line):
            key = list_key
            value = re.sub(r"^\s+-\s+", "", line).strip()
        else:
            continue
        try:
            if value.startswith(("|", ">", "&", "*", "!", "[", "{")):
                raise ValueError("non-scalar YAML construct")
            if value.startswith(("'", '"')):
                parsed = ast.literal_eval(value)
                if not isinstance(parsed, str):
                    raise ValueError("non-string value")
            else:
                parsed = re.split(r"\s+#", value, maxsplit=1)[0].strip()
            if isinstance(result.get(key), list):
                result[key].append(parsed)
            else:
                result[key] = parsed
        except (SyntaxError, ValueError):
            warnings.append(f"Unsupported configuration syntax: {path}:{line_number} ({key})")
    return result


def _load_json(path, warnings):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("expected an object")
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        warnings.append(f"Configuration unreadable or unsupported: {path}: {exc}")
        return {}


def _expand_path(value, root):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected a nonempty path string")
    value = value.replace("{project-root}", str(root))
    if "{" in value or "}" in value:
        raise ValueError("unsupported path substitution")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def _spec_target(line):
    """Accept the upstream **Spec:** field and plain documented references."""
    match = re.match(r"^\s*(?:\*\*)?Spec(?:ification)?(?::\*\*|\*\*:|:)\s*(.+?)\s*$", line, re.I)
    if not match:
        return None
    value = match.group(1)
    if value.startswith("`") and "`" in value[1:]:
        return value[1:value.index("`", 1)]
    if value.startswith("<") and ">" in value:
        return value[1:value.index(">")]
    link = re.match(r"\[[^\]]+\]\((?:<([^>]+)>|([^\s)]+))\)", value)
    if link:
        return link.group(1) or link.group(2)
    if value.startswith(('"', "'")):
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, str) else None
        except (ValueError, SyntaxError):
            return None
    return value if Path(value).suffix.lower() in {".md", ".markdown"} else None


class InventoryBuilder:
    """Adapter-facing collector. Stable records retain source content and roles."""

    def __init__(self, root, selections=None):
        self.root = root
        self.warnings = []
        self.documents = {}
        self.groups = {}
        self.relationships = []
        self.allowed_roots = {root}
        self.frameworks = set()
        self.historical_roots = set()
        self.history = {}
        self.selections = [path for _, path in _selected_paths(root, selections)]

    def historical(self, path):
        return path in self.history or any(path == root or _inside(path, root) for root in self.historical_roots)

    def historical_selected(self, path):
        return any(self.historical(selected) and
                   (path == selected or _inside(path, selected)) for selected in self.selections)

    def root_path(self, value, label):
        try:
            path = _expand_path(value, self.root)
        except ValueError as exc:
            self.warnings.append(f"Unsupported {label}: {value!r}: {exc}")
            return None
        self.allowed_roots.add(path)
        if not path.is_dir():
            self.warnings.append(f"Incomplete discovery: {label} unavailable: {path}")
            return None
        return path

    def group(self, framework, key, label, lifecycle="current", purpose="Purpose unspecified"):
        identity = _id(project_identity(self.root), framework, key)
        self.groups.setdefault(identity, {
            "id": identity, "label": label, "framework": framework,
            "lifecycle": lifecycle, "purpose": purpose, "key": key,
            "layout": copy.deepcopy(FRAMEWORK_LAYOUTS.get(framework, {"id": framework, "version": 1})),
        })
        self.frameworks.add(framework)
        return identity

    def add(self, path, framework, group, role, lifecycle="current", **extra):
        path = Path(path)
        if path.suffix.lower() not in {".md", ".markdown", ".toml"}:
            return None
        resolved = path.resolve()
        if not any(_inside(resolved, allowed) for allowed in self.allowed_roots):
            self.warnings.append(f"External symlink excluded; select it explicitly: {path} -> {resolved}")
            return None
        if lifecycle == "archived" or self.historical(resolved):
            self.history.setdefault(resolved, {
                "path": source_path(resolved, self.root), "absolute_path": str(resolved),
                "framework": framework, "lifecycle": "archived", **extra,
            })
            if not self.historical_selected(resolved):
                return None
            lifecycle = "archived"
        if resolved in self.documents:
            document = self.documents[resolved]
            if framework != document["framework"]:
                alias = {"framework": framework, "group": group, "role": role}
                if alias not in document.setdefault("memberships", []):
                    document["memberships"].append(alias)
                self.relationship(group, document["id"], "containment", "Contains document")
            return document
        try:
            document = snapshot_file(resolved, self.root)
        except (OSError, UnicodeError, ValueError) as exc:
            self.warnings.append(f"Incomplete discovery: document unreadable: {path}: {exc}")
            return None
        if not _inside(resolved, self.root):
            document["external_root"] = str(next(
                allowed for allowed in sorted(self.allowed_roots, key=lambda p: len(p.parts), reverse=True)
                if _inside(resolved, allowed)
            ))
        document.update(framework=framework, group=group, role=role,
                        lifecycle=lifecycle, implementation="unknown", **extra)
        self.documents[resolved] = document
        self.relationship(group, document["id"], "containment", "Contains document")
        return document

    def relationship(self, origin, destination, kind, label, inferred=False, **extra):
        if isinstance(origin, dict):
            origin = origin["id"]
        if isinstance(destination, dict):
            destination = destination["id"]
        record = {"from": origin, "to": destination, "type": kind, "label": label,
                  "inferred": inferred, **extra}
        if record not in self.relationships:
            self.relationships.append(record)

    def walk(self, root, suffixes=(".md", ".markdown"), explicit=False):
        if not root.is_dir():
            return
        resolved = root.resolve()
        if not any(_inside(resolved, allowed) for allowed in self.allowed_roots):
            self.warnings.append(f"External specification root not scanned without declaration: {root} -> {resolved}")
            return
        def inaccessible(error):
            self.warnings.append(f"Incomplete discovery: directory unreadable: {error.filename}: {error}")
        for current, directories, files in os.walk(root, followlinks=False, onerror=inaccessible):
            retained = []
            for directory in directories:
                if not explicit and directory in EXCLUDED:
                    continue
                child = Path(current) / directory
                if child.is_symlink():
                    self.warnings.append(f"Symlink directory not scanned automatically; select it explicitly: {child}")
                    continue
                retained.append(directory)
            directories[:] = sorted(retained)
            for name in sorted(files):
                if Path(name).suffix.lower() in suffixes:
                    yield Path(current) / name

    def document_reference(self, origin, target_text, line_number, label="Document reference", inferred=False):
        text = unquote(target_text.split("#", 1)[0]).strip()
        if not text or urlparse(text).scheme or text.startswith("//"):
            return
        path = Path(text)
        candidates = [path] if path.is_absolute() else [Path(origin["absolute_path"]).parent / path, self.root / path]
        target = next((self.documents.get(p.resolve()) for p in candidates if p.resolve() in self.documents), None)
        if target is None:
            existing = next((p.resolve() for p in candidates if p.is_file()), None)
            if any(self.historical(p.resolve()) for p in candidates):
                # Known history is neither current context nor a missing link.
                return
            if existing and _inside(existing, self.root) and not any(part in EXCLUDED for part in existing.relative_to(self.root).parts):
                group = self.group("generic", "references", "Referenced documents", purpose="Source-linked supporting context; framework behavior unknown")
                target = self.add(existing, "generic", group, "document", "unknown")
        if target:
            self.relationship(origin, target, "reference", label, inferred,
                              source={"path": origin["path"], "line": line_number})
        elif Path(text).suffix.lower() in {".md", ".markdown", ".toml"}:
            self.relationship(origin, None, "reference", label, inferred,
                              unresolved=text, source={"path": origin["path"], "line": line_number})
            self.warnings.append(f"Unresolved reference: {origin['path']}:{line_number} -> {text}")

    def references(self):
        processed = set()
        while unprocessed := [d for d in self.documents.values() if d["id"] not in processed]:
            document = unprocessed[0]
            processed.add(document["id"])
            fenced = False
            fence_char = ""
            for line_number, line in enumerate(document["text"].splitlines(), 1):
                fence = re.match(r"^\s*(`{3,}|~{3,})", line)
                if fence:
                    char = fence.group(1)[0]
                    if not fenced:
                        fenced, fence_char = True, char
                    elif char == fence_char:
                        fenced = False
                    continue
                if fenced:
                    continue
                for match in re.finditer(r"\[[^\]]+\]\((?:<([^>]+)>|([^\s)]+)(?:\s+[^)]*)?)\)", line):
                    self.document_reference(document, match.group(1) or match.group(2), line_number)
                spec = _spec_target(line)
                if spec:
                    self.document_reference(document, spec, line_number, "Plan specification")


def _open_spec(builder):
    base = builder.root / "openspec"
    if not base.is_dir():
        return
    configuration = next((p for p in (base / "config.yaml", base / "config.yml") if p.is_file()), None)
    metadata = _yaml_scalars(configuration, {"schema", "store", "references"}, builder.warnings) if configuration else {}
    for field in ("schema", "store"):
        if field in metadata and not isinstance(metadata[field], str):
            builder.warnings.append(f"Unsupported OpenSpec configuration: {field} must be a scalar string: {configuration}")
            metadata.pop(field)
    if "references" in metadata and not isinstance(metadata["references"], list):
        builder.warnings.append(f"Unsupported OpenSpec configuration: references must be a list: {configuration}")
        metadata.pop("references")
    roots = [base]
    declared_store = metadata.get("store")
    if declared_store and ((base / "specs").is_dir() or (base / "changes").is_dir()):
        builder.warnings.append(f"OpenSpec store declaration ignored beside local specs or changes: {declared_store!r}; use references for read-only store context")
        declared_store = None
    declared = [declared_store, *metadata.get("references", [])]
    declared = [value for value in declared if value]
    if declared:
        registry = {}
        if shutil.which("openspec"):
            try:
                result = subprocess.run(["openspec", "store", "list", "--json"], capture_output=True,
                                        text=True, timeout=5, check=False)
                data = json.loads(result.stdout)
                for item in data.get("stores", []):
                    if isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("root"), str):
                        registry[item["id"]] = item["root"]
            except (OSError, ValueError, subprocess.TimeoutExpired):
                builder.warnings.append("OpenSpec store registry unavailable; registered external roots were not resolved")
        for name in declared:
            location = registry.get(name)
            if location:
                store = builder.root_path(str(Path(location) / "openspec"), f"OpenSpec store {name}")
                if store and store not in roots:
                    roots.append(store)
            else:
                builder.warnings.append(f"Incomplete discovery: OpenSpec store {name!r} unavailable; register it or select its folder explicitly")
    schema = metadata.get("schema", "spec-driven")
    if schema != "spec-driven":
        builder.warnings.append(f"OpenSpec schema {schema!r} is not supported for workflow dependencies; document views remain available")
    for root in roots:
        root_schema = schema
        namespace = ""
        if root != base:
            namespace = f"store-{_id(str(root))}/"
            external_config = next((p for p in (root / "config.yaml", root / "config.yml") if p.is_file()), None)
            external_metadata = _yaml_scalars(external_config, {"schema"}, builder.warnings) if external_config else {}
            root_schema = external_metadata.get("schema", "spec-driven")
            if root_schema != "spec-driven":
                builder.warnings.append(f"OpenSpec store schema {root_schema!r} unsupported for workflow dependencies: {root}")
        main_by_capability = {}
        for path in builder.walk(root / "specs"):
            relative = path.relative_to(root / "specs")
            capability = relative.parent.as_posix()
            group = builder.group("openspec", f"{root}/main/{capability}", capability.replace("-", " ").capitalize(), "current", "Existing documented behavior")
            document = builder.add(path, "openspec", group, "specification" if path.name == "spec.md" else "supporting", capability=capability, lineage=f"openspec/{namespace}main/{capability}")
            if document and path.name == "spec.md":
                main_by_capability[capability] = document
        change_base = root / "changes"
        if not change_base.is_dir():
            continue
        changes = [(p, "proposed") for p in sorted(change_base.iterdir()) if p.is_dir() and p.name != "archive"]
        archive = change_base / "archive"
        builder.historical_roots.add(archive.resolve())
        if archive.is_dir():
            changes.extend((p, "archived") for p in sorted(archive.iterdir()) if p.is_dir())
        for change, lifecycle in changes:
            logical_name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", change.name)
            group = builder.group("openspec", f"{root}/change/{logical_name}/{lifecycle}", logical_name.replace("-", " ").capitalize(), lifecycle,
                                  "Proposed behavior changes" if lifecycle == "proposed" else "Completed change history; implementation evidence separate")
            members = []
            for path in builder.walk(change):
                relative = path.relative_to(change)
                is_delta = len(relative.parts) > 2 and relative.parts[0] == "specs"
                role = "delta specification" if is_delta else {"proposal.md": "proposal", "design.md": "design", "tasks.md": "tasks"}.get(path.name, "supporting")
                capability = relative.parent.relative_to("specs").as_posix() if is_delta else None
                document = builder.add(path, "openspec", group, role, lifecycle,
                                       change=logical_name, lineage=f"openspec/{namespace}change/{logical_name}/{relative.as_posix()}", capability=capability,
                                       **({"active_path": source_path(change_base / logical_name / relative, builder.root)} if lifecycle == "archived" else {}))
                if document:
                    members.append(document)
                    if capability in main_by_capability:
                        builder.relationship(document, main_by_capability[capability], "reference", "Change to current capability", True)
            if root_schema == "spec-driven":
                proposal = next((d for d in members if d["role"] == "proposal"), None)
                tasks = next((d for d in members if d["role"] == "tasks"), None)
                for document in members:
                    if document["role"] in {"design", "delta specification"}:
                        if proposal:
                            builder.relationship(proposal, document, "workflow", "Planning dependency", True)
                        if tasks:
                            builder.relationship(document, tasks, "workflow", "Informs implementation tasks", True)


def _spec_kit(builder):
    standard = builder.root / "specs"
    marker = builder.root / ".specify"
    if not marker.is_dir() and not (standard.is_dir() and any((p / "spec.md").exists() for p in standard.iterdir() if p.is_dir())):
        return
    roots = [p for p in sorted(standard.iterdir()) if p.is_dir()] if standard.is_dir() else []
    pointer = marker / "feature.json"
    config = _load_json(pointer, builder.warnings) if pointer.exists() else {}
    values = [config.get("feature_directory"), os.environ.get("SPECIFY_FEATURE_DIRECTORY")]
    for value in values:
        if value is not None:
            path = builder.root_path(value, "Spec Kit feature root")
            if path and path not in roots:
                roots.append(path)
    constitution = marker / "memory" / "constitution.md"
    if constitution.is_file():
        group = builder.group("spec-kit", "constitution", "Project principles", purpose="Shared project rules")
        builder.add(constitution, "spec-kit", group, "rules")
    roles = {"spec.md": "specification", "plan.md": "design", "tasks.md": "tasks", "research.md": "research", "data-model.md": "data model", "quickstart.md": "quickstart"}
    for feature in roots:
        group = builder.group("spec-kit", str(feature), re.sub(r"^\d+-", "", feature.name).replace("-", " ").capitalize(), "proposed", "Feature requirements and implementation plan")
        documents = {}
        for path in builder.walk(feature):
            role = "contract" if "contracts" in path.relative_to(feature).parts else roles.get(path.name, "supporting")
            document = builder.add(path, "spec-kit", group, role, "proposed")
            if document:
                documents[path.name] = document
        for left, right in (("spec.md", "plan.md"), ("plan.md", "tasks.md")):
            if left in documents and right in documents:
                builder.relationship(documents[left], documents[right], "workflow", "Planning dependency", True)


def _bmad(builder):
    installation = builder.root / "_bmad"
    default = builder.root / "_bmad-output"
    if not installation.is_dir() and not default.is_dir():
        return
    for legacy in (installation / "bmm" / "config.yaml", installation / "config.yaml"):
        if legacy.exists():
            builder.warnings.append(f"Incomplete discovery: legacy BMAD YAML configuration is unsupported: {legacy}; use current TOML configuration or select the planning folder explicitly")
    values = {}
    for path in (installation / "config.toml", installation / "custom" / "config.toml", installation / "custom" / "config.user.toml"):
        if path.is_file():
            try:
                content = tomllib.loads(path.read_text(encoding="utf-8"))
                core = content.get("core", {})
                if not isinstance(core, dict):
                    raise ValueError("core must be a table")
                values.update(core)
            except (OSError, UnicodeError, ValueError) as exc:
                builder.warnings.append(f"Unsupported BMAD configuration: {path}: {exc}")
    output = builder.root_path(values.get("output_folder", str(default)), "BMAD output root")
    if output is None:
        return
    for path in builder.walk(output, suffixes=(".md", ".markdown", ".toml")):
        relative = path.relative_to(output)
        if path.name.endswith(".toml") and path.name != "tickets.toml":
            continue
        owner = next((p for p in reversed(path.parent.parents) if p != output and _inside(p, output) and p.name.startswith("epic-")), None)
        if path.parent.name.startswith("epic-"):
            owner = path.parent
        if owner is None:
            owner = output / relative.parts[0] if len(relative.parts) > 1 else output
        group = builder.group("bmad", str(owner), owner.name.replace("-", " ").capitalize(), "proposed", "Planning and story tracking")
        stem = path.stem.lower()
        role = "tickets" if path.name == "tickets.toml" else "story plan" if stem.endswith("-plan") or stem.startswith("plan-") else "brief" if stem.startswith("brief-") else "specification" if stem.startswith(("spec-", "prd-", "epic-", "initiative-")) else "story" if stem.startswith(("story-", "bug-", "spike-")) else "supporting"
        status = re.search(r"(?m)^status:\s*[\"']?([\w-]+)", path.read_text(encoding="utf-8")) if path.suffix == ".md" else None
        builder.add(path, "bmad", group, role, "proposed", reported_status=status.group(1) if status else "unknown")
    for group in list(builder.groups.values()):
        if group["framework"] != "bmad":
            continue
        documents = [d for d in builder.documents.values() if d["group"] == group["id"]]
        for plan in (d for d in documents if d["role"] == "story plan"):
            for source in (d for d in documents if d["role"] in {"specification", "tickets"}):
                builder.relationship(source, plan, "workflow", "Story planning context", True)


def _superpowers(builder):
    base = builder.root / "docs" / "superpowers"
    if not base.is_dir():
        return
    def feature_key(path, kind):
        stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", path.stem)
        return re.sub(r"-design$", "", stem) if kind == "design" else stem
    for folder, role in (("specs", "design"), ("plans", "plan")):
        for path in builder.walk(base / folder):
            key = feature_key(path, role)
            group = builder.group("superpowers", key, key.replace("-", " ").capitalize(), "proposed", "Design and implementation plan")
            document = builder.add(path, "superpowers", group, role, "proposed")
            if document and role == "plan":
                # A plan's explicit Spec: field can name an agreed alternate
                # in-project location, without opening unrelated external trees.
                for line in document["text"].splitlines():
                    reference = _spec_target(line)
                    if not reference:
                        continue
                    raw = Path(reference)
                    candidates = [raw] if raw.is_absolute() else [builder.root / raw, path.parent / raw]
                    target = next((p.resolve() for p in candidates if p.is_file()), None)
                    if target and _inside(target, builder.root) and not any(p in EXCLUDED for p in target.relative_to(builder.root).parts):
                        builder.add(target, "superpowers", group, "design", "proposed", alternate_location=True)


def _kiro(builder):
    base = builder.root / ".kiro" / "specs"
    if not base.is_dir():
        return
    for feature in sorted(p for p in base.iterdir() if p.is_dir()):
        config_path = feature / ".config.kiro"
        metadata = _load_json(config_path, builder.warnings) if config_path.exists() else {}
        mode = metadata.get("workflowType")
        if mode is not None and mode not in ("requirements-first", "design-first"):
            builder.warnings.append(f"Unsupported Kiro workflow {mode!r}: {config_path}; no document order inferred")
        specification_id = metadata.get("specId")
        if specification_id is not None and not isinstance(specification_id, str):
            builder.warnings.append(f"Unsupported Kiro specification identity: {config_path}; expected a string")
            specification_id = None
        group = builder.group("kiro", specification_id or str(feature), feature.name.replace("-", " ").capitalize(), "proposed", "Feature requirements, design, and tasks")
        documents = {}
        for path in builder.walk(feature):
            role = {"requirements.md": "specification", "bugfix.md": "bug description", "design.md": "design", "tasks.md": "tasks"}.get(path.name, "supporting")
            document = builder.add(path, "kiro", group, role, "proposed", workflow=mode or "unknown")
            if document:
                documents[path.name] = document
        requirements = documents.get("requirements.md") or documents.get("bugfix.md")
        design = documents.get("design.md")
        tasks = documents.get("tasks.md")
        if requirements and design and mode in ("requirements-first", "design-first"):
            source, target = (design, requirements) if mode == "design-first" else (requirements, design)
            builder.relationship(source, target, "workflow", f"{mode.replace('-', ' ').capitalize()} workflow", False,
                                 source={"path": str(config_path.relative_to(builder.root)), "line": 1})
        if tasks:
            for source in (requirements, design):
                if source:
                    builder.relationship(source, tasks, "workflow", "Informs implementation tasks", True)


ADAPTERS = {"openspec": _open_spec, "spec-kit": _spec_kit, "bmad": _bmad,
            "superpowers": _superpowers, "kiro": _kiro}


def specification_paths(inventory):
    """Exclude both presented specifications and indexed history from code drift."""
    return sorted({d["path"] for d in inventory["documents"] + inventory.get("history", [])})


def register_adapter(name, discoverer):
    """Register a local adapter callable(builder); never load remote code."""
    if not isinstance(name, str) or not name or not callable(discoverer):
        raise ValueError("Adapter name and callable are required")
    if name in ADAPTERS:
        raise ValueError(f"Adapter already registered: {name}")
    ADAPTERS[name] = discoverer


def _selected_paths(root, selections):
    if isinstance(selections, (str, Path)):
        selections = [selections]
    paths = []
    for selection in selections or []:
        raw = str(selection)
        path = Path(raw[len("external::"):] if raw.startswith("external::") else raw).expanduser()
        path = (path if path.is_absolute() else root / path).resolve()
        paths.append((str(selection), path))
    return paths


def select_inventory(inventory, selections, _discover_missing=True):
    """Set analysis scope and one-hop context; preserve the project inventory."""
    result = copy.deepcopy(inventory)
    if not selections:
        result["scope"] = [document["id"] for document in result["documents"]]
        result["context"] = []
        return result
    selected = set()
    root = Path(result["project"]["root"])
    for selection, path in _selected_paths(root, selections):
        matched = [d for d in result["documents"] if Path(d["absolute_path"]) == path or _inside(Path(d["absolute_path"]), path)]
        if not matched:
            if path.is_dir() and any(Path(p) == path or _inside(Path(p), path)
                                      for p in result.get("historical_roots", [])):
                continue  # A broad current-work scope can legitimately be empty.
            matched = [d for d in result["documents"] if d["path"] == selection or Path(d["path"]).name == selection]
            if len(matched) > 1:
                raise DiscoveryError(f"Ambiguous file name {selection!r}; select a full path: " + ", ".join(d["path"] for d in matched))
        if not matched:
            if _discover_missing and path.exists():
                existing = [d["absolute_path"] for d in inventory["documents"] if d["framework"] == "generic"]
                refreshed = discover(root, [*existing, *(str(p) for _, p in _selected_paths(root, selections))])
                return select_inventory(refreshed, selections, _discover_missing=False)
            raise DiscoveryError(f"No specification documents selected by {selection!r}; choose an existing Markdown file or specification folder")
        selected.update(d["id"] for d in matched)
    context = set()
    for relationship in result["relationships"]:
        if relationship["type"] == "containment":
            continue
        if relationship["from"] in selected and relationship["to"] not in selected:
            context.add(relationship["to"])
        if relationship["to"] in selected and relationship["from"] not in selected:
            context.add(relationship["from"])
    document_ids = {d["id"] for d in result["documents"]}
    result["scope"] = [d["id"] for d in result["documents"] if d["id"] in selected]
    result["context"] = [d["id"] for d in result["documents"] if d["id"] in context & document_ids]
    return result


def discover(project=None, selections=None, cwd=None):
    """Return a source-backed inventory for one project and optional local scope."""
    root = resolve_project(project, cwd)
    builder = InventoryBuilder(root, selections)
    for name, adapter in list(ADAPTERS.items()):
        try:
            adapter(builder)
        except (OSError, UnicodeError, ValueError) as exc:
            builder.warnings.append(f"Incomplete {name} discovery: {exc}")
    for selection, path in _selected_paths(root, selections):
        if not path.exists():
            # Bare names may be resolved against already discovered files.
            if not any(Path(d["path"]).name == selection or d["path"] == selection for d in builder.documents.values()):
                raise DiscoveryError(f"Selected path unavailable: {path}")
            continue
        builder.allowed_roots.add(path if path.is_dir() else path.parent)
        paths = builder.walk(path, explicit=True) if path.is_dir() else [path]
        for document_path in paths:
            if document_path.resolve() in builder.documents:
                continue
            if builder.historical(document_path.resolve()) and not builder.historical_selected(document_path.resolve()):
                continue
            group = builder.group("generic", str(path if path.is_dir() else path.parent), "Selected documents", purpose="Unfamiliar document hierarchy; framework behavior unknown")
            document = builder.add(document_path, "generic", group, "document", "unknown")
            if document:
                builder.warnings.append(f"Generic document view: {document['path']}; framework-specific behavior and implementation status unknown")
    builder.references()
    documents = sorted(builder.documents.values(), key=lambda d: d["path"])
    if not documents:
        builder.warnings.append("Specification inventory is empty. Select a Markdown file or specification folder explicitly.")
    readme = root / "README.md"
    purpose = "Purpose unspecified"
    name = root.name
    if readme.is_file():
        try:
            intro = snapshot_file(readme, root)
            name, purpose = intro.get("title") or name, intro.get("purpose") or purpose
        except (OSError, UnicodeError, ValueError):
            builder.warnings.append("Project README could not be read; project purpose unspecified")
    snapshot = hashlib.sha256(json.dumps(
        {"documents": [(d["id"], d["hash"]) for d in documents],
         "relationships": builder.relationships}, sort_keys=True).encode()).hexdigest()
    inventory = {
        "schema_version": 1, "project": {"root": str(root), "id": project_identity(root), "name": name, "purpose": purpose},
        "snapshot": snapshot, "documents": documents,
        "groups": sorted((g for g in builder.groups.values() if any(
            d["group"] == g["id"] or any(m["group"] == g["id"] for m in d.get("memberships", []))
            for d in documents)), key=lambda g: (g["framework"], g["lifecycle"], g["label"])),
        "history": sorted(builder.history.values(), key=lambda d: d["path"]),
        "historical_roots": sorted(str(p) for p in builder.historical_roots),
        "relationships": builder.relationships, "warnings": list(dict.fromkeys(builder.warnings)),
        "scope": [d["id"] for d in documents], "context": [],
    }
    return select_inventory(inventory, selections, _discover_missing=False)
