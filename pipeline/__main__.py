import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python3 -m pipeline",
        description="EU Parliament votes pipeline. See docs/data-source.md for provenance.",
    )
    parser.add_argument(
        "stage",
        choices=["fetch", "etl", "term8", "meps", "validate", "archive", "reconcile", "verify", "mine", "parity", "publish", "all"],
        help="pipeline stage to run",
    )
    parser.add_argument(
        "--tag",
        help="pin a specific source release tag (default: latest). "
        "Required to reproduce a past build, since 'latest' moves weekly.",
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--limit", type=int, help="archive: stop after this many sittings"
    )
    args = parser.parse_args()

    if args.stage in ("fetch", "all"):
        from .fetch import fetch

        print("fetch:")
        fetch(args.data_dir, args.tag)

    if args.stage in ("etl", "all"):
        from .etl import load

        print("etl:")
        load(args.data_dir)

    if args.stage in ("term8", "all"):
        from .term8 import ingest

        print("term8:")
        ingest(args.data_dir)

    if args.stage in ("meps", "all"):
        from .mep_details import enrich

        print("meps:")
        enrich(args.data_dir)

    if args.stage in ("validate", "all"):
        from .validate import validate

        print("validate:")
        if validate(args.data_dir):
            raise SystemExit(1)

    if args.stage in ("archive", "all"):
        from .archive import archive

        print("archive:")
        archive(args.data_dir, args.limit)

    if args.stage in ("reconcile", "all"):
        from .reconcile import reconcile

        print("reconcile:")
        reconcile(args.data_dir)

    if args.stage in ("verify", "all"):
        from .verify import verify

        print("verify:")
        if verify(args.data_dir):
            raise SystemExit(1)

    if args.stage in ("mine", "all"):
        from .mining import mine

        print("mine:")
        mine(args.data_dir)

    if args.stage in ("parity", "all"):
        from .parity import parity

        print("parity:")
        parity(args.data_dir)

    if args.stage in ("publish", "all"):
        from .publish import publish

        print("publish:")
        publish(args.data_dir)


if __name__ == "__main__":
    main()
