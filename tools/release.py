"""Seal a reviewed source bundle; this does not publish or promote a release."""

import argparse
from pathlib import Path

from bundle import BundleError, seal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills/specviz"
    try:
        value = seal(source, args.channel, args.version)
    except BundleError as exc:
        parser.error(str(exc))
    print(f"Sealed {value['channel']} {value['version']}: {value['source_identity']}")


if __name__ == "__main__":
    main()
