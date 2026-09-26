"""Emit the published data bundles the UI consumes (IF-PUBLISHED-DATA).

The boundary this module defends: mining produces models, publishing shapes them for
delivery. Nothing here fits a model or decides a method; it aggregates, sizes, and
labels — and it refuses to ship figures whose ballots did not verify (FR02).

Every vote carries the URL of Parliament's own document, because the platform's
authority is europarl.europa.eu rather than whichever dataset we happened to load.
"""

import json
from pathlib import Path

import duckdb

from .archive import DOC_URL, DOC_URL_T8, document_url
from .provenance import now, script_version


def _write(out: Path, name: str, payload) -> None:
    path = out / name
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n")
    print(f"    {name}: {path.stat().st_size / 1024:.0f} KB")


def _rows(con, sql: str, params=None) -> list[dict]:
    cursor = con.execute(sql, params or [])
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def publish(data_dir: Path) -> None:
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"), read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")
    out = data_dir / "published"
    out.mkdir(parents=True, exist_ok=True)

    verification = con.execute(
        "SELECT summary FROM _verification ORDER BY checked_at DESC LIMIT 1"
    ).fetchone()
    if verification is None:
        raise SystemExit("nothing verified yet — run `archive` then `verify` (FR02)")
    summary = json.loads(verification[0])
    # FR02 blocks the *affected* figures, not the whole publication: mining already
    # excludes unverified votes, and each vote below carries its own status, so a
    # reader can see exactly what is and is not backed by Parliament's record.
    print(
        f"    {summary['votes_verified']:,}/{summary['votes_in_store']:,} votes verified;"
        f" {summary['discrepancies']:,} excluded as unverified"
    )

    meps = _rows(
        con,
        """
        SELECT m.id, m.first_name, m.last_name, m.country_code,
               m.gender, m.constituency, m.photo_url, m.ep_url,
               list(DISTINCT c.group_code) AS groups,
               list(DISTINCT c.term) AS terms
        FROM members m JOIN mep_cohesion c ON c.member_id = m.id
        GROUP BY ALL ORDER BY m.last_name
        """,
    )
    by_id = {m["id"]: m for m in meps}
    for mep in meps:
        mep["record"] = {}

    for row in _rows(
        con,
        """
        SELECT c.member_id, c.term, c.group_code, c.votes_cast, round(c.loyalty, 4) AS loyalty,
               c.main_votes_cast, round(c.main_loyalty, 4) AS main_loyalty,
               p.pc1, p.pc2, p.pc3
        FROM mep_cohesion c
        LEFT JOIN mep_positions p ON p.member_id = c.member_id AND p.term = c.term
        """,
    ):
        entry = by_id.get(row.pop("member_id"))
        if entry is not None:
            term = row.pop("term")
            pcs = [row.pop("pc1"), row.pop("pc2"), row.pop("pc3")]
            row["position"] = None if pcs[0] is None else [round(v, 3) for v in pcs]
            entry["record"][str(term)] = row
    _write(out, "meps.json", meps)

    _write(
        out,
        "groups.json",
        _rows(
            con,
            """
            SELECT g.code, g.label, g.short_label, gc.term, gc.meps,
                   gc.votes_cast, round(gc.cohesion, 4) AS cohesion,
                   round(gc.main_cohesion, 4) AS main_cohesion
            FROM group_cohesion gc JOIN groups g ON g.code = gc.group_code
            ORDER BY gc.term, gc.main_cohesion DESC
            """,
        ),
    )

    _write(
        out,
        "topics.json",
        _rows(
            con,
            """
            WITH group_position AS (
                SELECT t.subject_code AS topic_code, t.subject_label AS topic_label,
                       v.term, mv.group_code,
                       mv.vote_id,
                       arg_max(mv.position, mv.n) AS majority
                FROM (
                    SELECT vote_id, group_code, position, count(*) n
                    FROM member_votes
                    WHERE position <> 'DID_NOT_VOTE' AND group_code IS NOT NULL
                    GROUP BY 1, 2, 3
                ) mv
                JOIN vote_topics t ON t.vote_id = mv.vote_id
                -- The 8th term's source carries no main-vote flag, so its figures cover
                -- all roll-call votes. That is stated per row rather than quietly
                -- mixing two different bases into one column.
                JOIN votes v ON v.id = mv.vote_id
                             AND (v.is_main OR v.term = 8)
                GROUP BY 1, 2, 3, 4, 5
            )
            SELECT topic_code, topic_label, term, group_code,
                   count(*) AS votes,
                   CASE WHEN term = 8 THEN 'all votes' ELSE 'substantive votes' END AS basis,
                   round(avg(CASE WHEN majority = 'FOR' THEN 1.0 ELSE 0.0 END), 4) AS support
            FROM group_position
            GROUP BY 1, 2, 3, 4, 6
            HAVING count(*) >= 15
            ORDER BY topic_code, term, group_code
            """,
        ),
    )

    terms = [r[0] for r in con.execute("SELECT DISTINCT term FROM votes ORDER BY term").fetchall()]
    for term in terms:
        rows = _rows(
                con,
                f"""
                SELECT v.id, strftime(v.timestamp, '%Y-%m-%d') AS date, v.display_title AS title,
                       v.procedure_reference, v.is_main, v.result,
                       v.count_for, v.count_against, v.count_abstention, v.count_did_not_vote,
                       list_filter(list(DISTINCT t.subject_label), x -> x IS NOT NULL) AS topics,
                       -- How strongly this vote separates members along each axis. No
                       -- political direction: component sign and rotation are arbitrary.
                       any_value([round(vc.pc1, 5), round(vc.pc2, 5), round(vc.pc3, 5)]) AS components,
                       coalesce(ver.verified, false) AS verified,
                       coalesce(ver.partial, false) AS partially_verified
                FROM votes v
                LEFT JOIN vote_topics t ON t.vote_id = v.id
                LEFT JOIN vote_verification ver ON ver.vote_id = v.id
                LEFT JOIN vote_components vc ON vc.vote_id = v.id
                WHERE v.term = ?
                  AND NOT EXISTS (SELECT 1 FROM vote_duplicate d WHERE d.vote_id = v.id)
                GROUP BY ALL ORDER BY date, v.id
                """,
                [term],
        )
        # Each vote cites the document it was verified against. The 8th term predates
        # the doceo scheme, so the URL is built per term rather than templated.
        for row in rows:
            row["source"] = document_url(term, row["date"])
        _write(out, f"votes-t{term}.json", rows)

    source = json.loads(
        con.execute("SELECT source FROM _provenance LIMIT 1").fetchone()[0]
    )
    mining = json.loads(con.execute("SELECT pca FROM _mining LIMIT 1").fetchone()[0])
    _write(
        out,
        "meta.json",
        {
            "generated_at": now(),
            "script": script_version(),
            "reference_of_record": {
                "name": "European Parliament plenary minutes (roll-call votes)",
                "url_templates": {"terms 9+": DOC_URL, "term 8": DOC_URL_T8},
                "note": "Every vote links to the document it was verified against.",
            },
            "ingest_source": source,
            "verification": summary,
            "analysis": mining,
            "terms": terms,
            "caveats": [
                "The 8th term (2014-2019) comes from a different source and is not"
                " equivalent: it records only MEPs who actually voted, and carries no"
                " main-vote flag and no subject tags. Participation, substantive-vote"
                " and topic figures cover 2019 onwards only.",
                "Figures cover roll-call votes only. Votes by show of hands or secret"
                " ballot are not recorded per MEP by anyone, including Parliament.",
                "'Did not vote' is not published by Parliament; it is derived from the"
                " sitting roster. Participation figures are roll-call participation.",
                "Principal component axes have no inherent direction or meaning: sign"
                " and rotation are arbitrary, and only relative positions are"
                " interpretable.",
                "Group loyalty over all votes largely reflects procedural discipline;"
                " the main-vote figure is the one that speaks to substantive"
                " disagreement.",
            ],
        },
    )
    con.close()
