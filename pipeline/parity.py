"""Check this pipeline against the analysis it replaces (TK17, FR03).

A rewrite that quietly delivers less than its predecessor is a regression however much
better its engineering is. The 8th term is the only term both pipelines cover, so it is
the one place parity can be measured rather than asserted.

The baseline lives in `baseline_2019.json`, derived once from the 2019 pipeline's own
output and committed as a fixture so this check outlives `attic/`.
"""

import json
from pathlib import Path

import duckdb

BASELINE = Path(__file__).parent / "baseline_2019.json"

FAIL, WARN, OK = "FAIL", "WARN", "ok"


def _measure(con, term: int) -> dict:
    one = lambda sql: con.execute(sql, [term]).fetchone()[0]
    # DuckDB binds both branches of a CASE, so a missing table has to be guarded here
    # rather than in SQL. `vote_components` arrives with TK16.
    has_components = con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'vote_components'"
    ).fetchone()[0]
    return {
        "votes": one(
            """SELECT count(*) FROM votes v
               JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
               WHERE v.term = ?"""
        ),
        # Extracted: what we hold as distinct real votes, duplicates excluded. This is
        # the like-for-like comparison with the old pipeline, which verified nothing.
        "votes_extracted": one(
            """SELECT count(*) FROM votes v WHERE v.term = ?
               AND NOT EXISTS (SELECT 1 FROM vote_duplicate d WHERE d.vote_id = v.id)"""
        ) if con.execute(
            "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'vote_duplicate'"
        ).fetchone()[0] else one("SELECT count(*) FROM votes WHERE term = ?"),
        "meps_with_positions": one("SELECT count(*) FROM mep_positions WHERE term = ?"),
        # Why the analysed figure falls short, taken from the data rather than assumed:
        # votes our source and Parliament genuinely disagree about, and results in
        # Parliament's record we hold nothing for.
        "disagree": one(
            """SELECT count(*) FROM vote_verification ver JOIN votes v ON v.id = ver.vote_id
               WHERE v.term = ? AND NOT ver.verified
                 AND coalesce(ver.note, '') NOT LIKE 'vote absent%'"""
        ),
        "absent": one(
            """SELECT count(*) FROM vote_verification ver JOIN votes v ON v.id = ver.vote_id
               WHERE v.term = ? AND coalesce(ver.note, '') LIKE 'vote absent%'"""
        ),
        "vote_component_coefficients": one(
            """SELECT count(DISTINCT vc.vote_id) FROM vote_components vc
               JOIN votes v ON v.id = vc.vote_id WHERE v.term = ?"""
        ) if has_components else 0,
    }


def _mep_fields(con, term: int) -> dict:
    """How completely our MEP records are populated, for MEPs active in this term."""
    columns = [c[0] for c in con.execute("DESCRIBE members").fetchall() if c[0] != "id"]
    population = con.execute(
        f"""
        SELECT {', '.join(f'count({c})' for c in columns)}, count(*)
        FROM members WHERE id IN (
            SELECT DISTINCT mv.member_id FROM member_votes mv
            JOIN votes v ON v.id = mv.vote_id WHERE v.term = ?
        )
        """,
        [term],
    ).fetchone()
    total = population[-1]
    return {c: population[i] / total if total else 0 for i, c in enumerate(columns)}


def check(data_dir: Path):
    baseline = json.loads(BASELINE.read_text())
    term = baseline["term"]
    previous = baseline["previous_analysis"]
    ceiling = baseline["ep_record_rollcall_results"]

    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"), read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")
    now = _measure(con, term)
    fields = _mep_fields(con, term)
    con.close()

    # Parity is against the previous analysis; Parliament's own count is the ceiling
    # neither pipeline can exceed, quoted so the gap is legible.
    yield (
        f"T{term} votes extracted vs 2019 analysis",
        OK if now["votes_extracted"] >= previous["votes"] else FAIL,
        f"{now['votes_extracted']:,} vs {previous['votes']:,} (EP record holds {ceiling:,})",
    )
    # Analysed is the stricter measure and deliberately stays separate: we only analyse
    # votes verified against Parliament's record, which the old pipeline never did.
    yield (
        f"T{term} votes analysed vs 2019 analysis",
        OK if now["votes"] >= previous["votes"] else FAIL,
        f"{now['votes']:,} vs {previous['votes']:,};"
        f" {now['disagree']:,} disagree with the EP record, {now['absent']:,} absent from ours",
    )
    yield (
        f"T{term} MEPs with positions vs 2019 analysis",
        OK if now["meps_with_positions"] >= previous["meps_with_positions"] else FAIL,
        f"{now['meps_with_positions']:,} vs {previous['meps_with_positions']:,}",
    )
    yield (
        f"T{term} per-vote component coefficients",
        OK if now["vote_component_coefficients"] >= previous["vote_component_coefficients"] else FAIL,
        f"{now['vote_component_coefficients']:,} vs {previous['vote_component_coefficients']:,}",
    )

    # The old field set is expressed in its own vocabulary; this maps each of its
    # fields to the column carrying the same information here. A field is absent if we
    # have no such column at all, and sparse if we have one but barely populate it.
    equivalents = {
        "name": "first_name",
        "surname": "last_name",
        "country": "country_code",
        "birthdate": "date_of_birth",
        "email": "email",
        "gender": "gender",
        "picture": "photo_url",
        "eu_homepage": "ep_url",
        "current_constituency": "constituency",
    }
    # Compare fill rate against the old analysis's own fill rate rather than an
    # invented threshold: it did not have an email for every MEP either, because
    # Parliament does not publish one for every MEP.
    old_fill = previous.get("mep_field_fill", {})
    tolerance = 0.02
    missing = sorted(theirs for theirs, ours in equivalents.items() if ours not in fields)
    thin = sorted(
        f"{ours} {fields[ours]:.0%} vs {old_fill[theirs]:.0%}"
        for theirs, ours in equivalents.items()
        if ours in fields and theirs in old_fill and fields[ours] < old_fill[theirs] - tolerance
    )
    yield (
        f"T{term} MEP attributes vs 2019 analysis",
        OK if not thin and not missing else FAIL,
        (f"absent: {', '.join(missing)}" if missing else "")
        + (f"; sparse: {', '.join(thin)}" if thin else ""),
    )


def parity(data_dir: Path) -> int:
    failures = 0
    for name, status, detail in check(data_dir):
        if status == FAIL:
            failures += 1
        print(f"  [{status:^6}] {name:<44} {detail}")
    if failures:
        print(
            f"\n  {failures} parity check(s) FAILED — this pipeline is behind the"
            " analysis it replaces (FR03)."
        )
        print(
            "  Note: the analysed shortfall is votes excluded for contradicting"
            " Parliament's record.\n  The old pipeline included them because it never"
            " checked. Closing it means resolving those\n  disagreements, not admitting"
            " them."
        )
    else:
        print("\n  at least at parity with the 2019 analysis")
    return failures
