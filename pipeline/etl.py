import json
from pathlib import Path

import duckdb

from .provenance import now, script_version

# Terms are modelled explicitly rather than left as date arithmetic in every query.
# T9 opened 2019-07-02, T10 on 2024-07-16.
TERMS = [(9, "2019-07-02", "2024-07-15"), (10, "2024-07-16", None)]

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


def _latest_release(data_dir: Path) -> Path:
    releases = sorted((data_dir / "raw").glob("*/provenance.json"))
    if not releases:
        raise SystemExit("no fetched release found — run `fetch` first")
    return releases[-1].parent


def load(data_dir: Path, release: Path | None = None) -> Path:
    release = release or _latest_release(data_dir)
    raw_provenance = json.loads((release / "provenance.json").read_text())

    db_path = data_dir / "eu_votes.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    for table in TABLES:
        src = release / f"{table}.csv.gz"
        if not src.exists():
            raise SystemExit(f"missing {src} — refetch the release")
        con.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=true)",
            [str(src)],
        )
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {n:,} rows")

    # Verification and reconciliation look ballots up per sitting, hundreds of times.
    # Without this each lookup scans all 25M rows, which is what exhausted memory.
    con.execute("CREATE INDEX IF NOT EXISTS idx_member_votes_vote ON member_votes(vote_id)")

    con.execute("CREATE TABLE terms (term INTEGER, start_date DATE, end_date DATE)")
    for term, start, end in TERMS:
        con.execute("INSERT INTO terms VALUES (?, ?, ?)", [term, start, end])

    con.execute("ALTER TABLE votes ADD COLUMN term INTEGER")
    con.execute(
        """
        UPDATE votes SET term = (
            SELECT t.term FROM terms t
            WHERE CAST(votes.timestamp AS DATE) >= t.start_date
              AND (t.end_date IS NULL OR CAST(votes.timestamp AS DATE) <= t.end_date)
        )
        """
    )
    unassigned = con.execute("SELECT count(*) FROM votes WHERE term IS NULL").fetchone()[0]
    if unassigned:
        raise SystemExit(f"{unassigned} votes fall outside all known terms — extend TERMS")

    con.execute("CREATE TABLE _provenance (loaded_at VARCHAR, script JSON, source JSON)")
    con.execute(
        "INSERT INTO _provenance VALUES (?, ?, ?)",
        [now(), json.dumps(script_version()), json.dumps(raw_provenance["source"])],
    )

    by_term = con.execute(
        "SELECT term, count(*) FROM votes GROUP BY term ORDER BY term"
    ).fetchall()
    print("  votes by term: " + ", ".join(f"T{t}={n:,}" for t, n in by_term))
    con.close()
    print(f"  store written to {db_path}")
    return db_path
