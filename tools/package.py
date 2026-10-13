"""Build a portable skill ZIP from the single maintained source."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from bundle import BundleError, CHANNELS, validate


def main():
    parser = argparse.ArgumentParser(description="Package the maintained SpecViz skill")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--channel", choices=CHANNELS, default="stable")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills/specviz"
    try:
        release, files = validate(source, args.channel)
    except BundleError as exc:
        parser.error(str(exc))
    args.output = args.output or Path(f"dist/specviz-{release['version']}.zip")
    if args.output.resolve().is_relative_to(source):
        parser.error("Distribution output must be outside maintained skill source")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo("specviz/" + name, date_time=(2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("LICENSE", date_time=(2020, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        archive.writestr(info, (source.parents[1] / "LICENSE").read_bytes())
    receipt = {key: release[key] for key in ("channel", "version", "source_identity")}
    receipt["sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix(".json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
