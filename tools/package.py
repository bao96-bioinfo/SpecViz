"""Build a portable skill ZIP from the single maintained source."""

import argparse
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Package the maintained SpecViz skill")
    parser.add_argument("--output", type=Path, default=Path("dist/specviz-0.1.0.zip"))
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills/specviz"
    if args.output.resolve().is_relative_to(source):
        parser.error("Distribution output must be outside maintained skill source")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"} and path.name != ".specviz-install.json":
                archive.write(path, Path("specviz") / path.relative_to(source))
    print(args.output)


if __name__ == "__main__":
    main()
