from pathlib import Path

import duckdb

# Official maximum seats per term. T9 ran at 751 until the UK's departure in early
# 2020, then 705; T10 at 720. A vote recording more ballots than there are seats means
# the parse is wrong.
SEATS = {9: 751, 10: 720}
BREXIT = "2020-02-01"
POSITIONS = ("FOR", "AGAINST", "ABSTENTION", "DID_NOT_VOTE")

FAIL, WARN, OK, MANUAL = "FAIL", "WARN", "ok", "MANUAL"


def _checks(con: duckdb.DuckDBPyConnection):
    q = lambda sql: con.execute(sql).fetchall()
    one = lambda sql: con.execute(sql).fetchone()[0]

    n = one("SELECT count(*) FROM member_votes mv LEFT JOIN votes v ON v.id=mv.vote_id WHERE v.id IS NULL")
    yield "ballots reference a known vote", (OK if n == 0 else FAIL), f"{n:,} orphans"

    n = one("SELECT count(*) FROM member_votes mv LEFT JOIN members m ON m.id=mv.member_id WHERE m.id IS NULL")
    yield "ballots reference a known MEP", (OK if n == 0 else FAIL), f"{n:,} orphans"

    n = one("SELECT count(*) FROM votes v WHERE NOT EXISTS (SELECT 1 FROM member_votes mv WHERE mv.vote_id=v.id)")
    yield "every vote has ballots", (OK if n == 0 else FAIL), f"{n:,} empty votes"

    bad = one(f"""
        SELECT count(*) FROM votes v JOIN (
            SELECT vote_id,
                   count(*) FILTER (WHERE position='FOR') f,
                   count(*) FILTER (WHERE position='AGAINST') a,
                   count(*) FILTER (WHERE position='ABSTENTION') ab,
                   count(*) FILTER (WHERE position='DID_NOT_VOTE') dnv
            FROM member_votes GROUP BY vote_id) b ON b.vote_id=v.id
        WHERE v.count_for<>b.f OR v.count_against<>b.a
           OR v.count_abstention<>b.ab OR v.count_did_not_vote<>b.dnv
    """)
    yield "counted ballots match published tallies", (OK if bad == 0 else FAIL), f"{bad:,} votes disagree"

    unknown = q(f"SELECT DISTINCT position FROM member_votes WHERE position NOT IN {POSITIONS}")
    yield "ballot positions in known domain", (OK if not unknown else FAIL), f"{[u[0] for u in unknown]}"

    n = one("SELECT count(*) FROM votes WHERE term IS NULL")
    yield "every vote assigned to a term", (OK if n == 0 else FAIL), f"{n:,} unassigned"

    n = one("""
        SELECT count(*) FROM votes v JOIN terms t ON t.term=v.term
        WHERE CAST(v.timestamp AS DATE) < t.start_date
           OR (t.end_date IS NOT NULL AND CAST(v.timestamp AS DATE) > t.end_date)
    """)
    yield "vote dates inside their term", (OK if n == 0 else FAIL), f"{n:,} outside"

    for term, lo, med, hi in q("""
        SELECT v.term, min(n), median(n), max(n) FROM (
            SELECT vote_id, count(*) n FROM member_votes GROUP BY vote_id) b
        JOIN votes v ON v.id=b.vote_id GROUP BY v.term ORDER BY v.term
    """):
        seats = SEATS.get(term)
        status = OK if seats and lo >= 0.85 * seats and hi <= seats else FAIL
        yield f"T{term} ballots per vote within roster", status, f"{lo}-{hi} (median {med:.0f}, {seats} seats)"

    n = one(f"""
        SELECT count(*) FROM member_votes mv JOIN votes v ON v.id=mv.vote_id
        WHERE mv.country_code='GBR' AND CAST(v.timestamp AS DATE) >= DATE '{BREXIT}'
    """)
    yield "no UK ballots after withdrawal", (OK if n == 0 else FAIL), f"{n:,} after {BREXIT}"

    for term, people in q("""
        SELECT v.term, count(DISTINCT mv.member_id) FROM member_votes mv
        JOIN votes v ON v.id=mv.vote_id GROUP BY v.term ORDER BY v.term
    """):
        seats = SEATS.get(term, 0)
        # More people than seats is expected: members are replaced mid-term.
        yield f"T{term} distinct MEPs vs seats", (OK if people >= 0.9 * seats else WARN), f"{people} people, {seats} seats"

    n = one("SELECT count(*) FROM member_votes WHERE group_code IS NULL OR group_code=''")
    total = one("SELECT count(*) FROM member_votes")
    yield "ballots with a political group", (OK if n == 0 else WARN), f"{n:,} of {total:,} lack one"

    yield (
        "spot-check against EP roll-call record",
        MANUAL,
        "per term, against europarl.europa.eu plenary minutes RCV XML",
    )


def validate(data_dir: Path) -> int:
    db = data_dir / "eu_votes.duckdb"
    if not db.exists():
        raise SystemExit("no store found — run `etl` first")
    con = duckdb.connect(str(db), read_only=True)

    failures = 0
    for name, status, detail in _checks(con):
        if status == FAIL:
            failures += 1
        print(f"  [{status:^6}] {name:<44} {detail}")
    con.close()

    if failures:
        print(f"\n  {failures} check(s) FAILED — the store is not fit to publish from")
    else:
        print("\n  all automated checks passed; the MANUAL check is still owed (TK06)")
    return failures
