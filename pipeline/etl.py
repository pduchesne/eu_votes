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


# The two ingest sources name the same political groups differently: parltrack writes
# PPE, S&D, Verts/ALE, GUE/NGL where the other writes EPP, SD, GREEN_EFA, GUE_NGL. Left
# alone, a group's own history does not join across terms — "the EPP since 2014" would
# silently return nothing for the 8th term.
#
# Only groups that are the *same continuing group* are unified. ALDE is not folded into
# Renew, nor EFDD and ENF into their successors: those were distinct groups, and merging
# them would be a political claim rather than a naming fix.
GROUP_ALIASES = {
    "PPE": "EPP",
    "S&D": "SD",
    "Verts/ALE": "GREEN_EFA",
    "GUE/NGL": "GUE_NGL",
    "GUE_NGL_1995_0": "GUE_NGL",
}

# Groups that existed only in earlier terms still need a readable name.
HISTORICAL_LABELS = {
    "ALDE": "Alliance of Liberals and Democrats for Europe",
    "EFDD": "Europe of Freedom and Direct Democracy",
    "ENF": "Europe of Nations and Freedom",
}


def normalise_groups(con) -> None:
    """Put every term on one group vocabulary, so a group joins to itself over time."""
    for source, canonical in GROUP_ALIASES.items():
        con.execute("UPDATE member_votes SET group_code = ? WHERE group_code = ?", [canonical, source])
        con.execute("UPDATE group_memberships SET group_code = ? WHERE group_code = ?", [canonical, source])
        con.execute("DELETE FROM groups WHERE code = ?", [source])
    for code, label in HISTORICAL_LABELS.items():
        con.execute(
            "UPDATE groups SET label = ?, short_label = ?, official_label = ? WHERE code = ? AND label = code",
            [label, code, label, code],
        )
    remaining = con.execute(
        "SELECT DISTINCT group_code FROM member_votes WHERE group_code IN (SELECT unnest(?))",
        [list(GROUP_ALIASES)],
    ).fetchall()
    if remaining:
        raise SystemExit(f"group aliases not applied: {remaining}")


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

    normalise_groups(con)

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
