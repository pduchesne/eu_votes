import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m pipeline",
        description="EU Parliament votes pipeline. See docs/data-source.md for provenance.",
    )
    parser.add_argument(
        "stage",
        choices=["fetch", "etl", "validate", "spotcheck", "all"],
        help="pipeline stage to run ('spotcheck' needs roll-call XML in data/spotcheck/)",
    )
    parser.add_argument(
        "--tag",
        help="pin a specific source release tag (default: latest). "
        "Required to reproduce a past build, since 'latest' moves weekly.",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    if args.stage in ("fetch", "all"):
        from .fetch import fetch

        print("fetch:")
        fetch(args.data_dir, args.tag)

    if args.stage in ("etl", "all"):
        from .etl import load

        print("etl:")
        load(args.data_dir)

    if args.stage in ("validate", "all"):
        from .validate import validate

        print("validate:")
        if validate(args.data_dir):
            raise SystemExit(1)

    if args.stage == "spotcheck":
        from .spotcheck import spotcheck

        print("spotcheck:")
        raise SystemExit(1 if spotcheck(args.data_dir) else 0)


if __name__ == "__main__":
    main()
