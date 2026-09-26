import json
from pathlib import Path

import requests

from .provenance import now, script_version, sha256

REPO = "HowTheyVote/data"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET_URL = "https://github.com/{repo}/releases/download/{tag}/{name}"

TABLES = [
    "members",
    "member_votes",
    "votes",
    "groups",
    "group_memberships",
    "countries",
    "committees",
    "responsible_committee_votes",
    "eurovoc_concepts",
    "eurovoc_concept_votes",
    "oeil_subjects",
    "oeil_subject_votes",
    "geo_areas",
    "geo_area_votes",
]


def resolve_latest_tag() -> str:
    r = requests.get(API_LATEST, timeout=60)
    r.raise_for_status()
    return r.json()["tag_name"]


def _download(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.replace(dest)


def fetch(data_dir: Path, tag: str | None = None) -> Path:
    tag = tag or resolve_latest_tag()
    out = data_dir / "raw" / tag
    out.mkdir(parents=True, exist_ok=True)

    files = {}
    for table in TABLES:
        name = f"{table}.csv.gz"
        dest = out / name
        if not dest.exists():
            print(f"  fetching {name}")
            _download(ASSET_URL.format(repo=REPO, tag=tag, name=name), dest)
        else:
            print(f"  have {name}")
        files[name] = {"sha256": sha256(dest), "bytes": dest.stat().st_size}

    provenance = {
        "source": {
            "name": "HowTheyVote.eu dataset",
            "repo": f"https://github.com/{REPO}",
            "release_tag": tag,
            "licence": "ODbL",
            "upstream": "European Parliament plenary minutes and Legislative Observatory",
        },
        "fetched_at": now(),
        "script": script_version(),
        "files": files,
    }
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"  release {tag}: {len(files)} tables in {out}")
    return out
