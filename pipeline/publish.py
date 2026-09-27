"""Emit the published data bundles the UI consumes (IF-PUBLISHED-DATA).

The boundary this module defends: mining produces models, publishing shapes them for
delivery. Nothing here fits a model or decides a method; it aggregates, sizes, and
labels — and it refuses to ship figures whose ballots did not verify (FR02).

Every vote carries the URL of Parliament's own document, because the platform's
authority is europarl.europa.eu rather than whichever dataset we happened to load.
"""

import json
import re
from pathlib import Path

import duckdb

from .archive import DOC_URL, DOC_URL_T8, document_url
from .provenance import now, script_version

# Both ingest sources publish under ODbL, which makes our bundles a Derivative Database
# and share-alike applies (docs/licensing.md). The licence travels with the data rather
# than living only in a document nobody downloads.
LICENCE = {
    "published_data": {
        "name": "Open Database License (ODbL) v1.0",
        "url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "note": "These bundles are a Derivative Database of ODbL sources, so they are "
                "published under the same terms. Works built from them - charts, "
                "articles - are Produced Works and are not bound by share-alike, but "
                "must credit the sources below.",
    },
    "attribution": [
        {
            "name": "European Parliament",
            "statement": "© European Union — Source: European Parliament",
            "url": "https://www.europarl.europa.eu/",
            "role": "the record of record: every vote is verified against it",
        },
        {
            "name": "HowTheyVote.eu",
            "licence": "ODbL v1.0",
            "url": "https://github.com/HowTheyVote/data",
            "role": "ingest path for the 9th and 10th terms",
        },
        {
            "name": "Parltrack",
            "licence": "ODbL v1.0",
            "url": "https://parltrack.org/",
            "role": "8th term votes, member details, and procedure titles",
        },
    ],
}


def _write(out: Path, name: str, payload) -> None:
    path = out / name
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n")
    print(f"    {name}: {path.stat().st_size / 1024:.0f} KB")


# Words that appear in almost every procedure title and so distinguish nothing. Kept
# deliberately short: an over-aggressive list hides the vocabulary that actually differs
# between the two ends of an axis.
BOILERPLATE = {
    "the", "of", "and", "for", "on", "to", "in", "a", "an", "as", "at", "by", "with",
    "from", "its", "it", "or", "no", "not", "into", "under", "over", "between",
    "european", "europe", "eu", "union", "parliament", "council", "commission",
    "commission's", "report", "reports", "regulation", "directive", "decision",
    "proposal", "amending", "implementation", "establishing", "rules", "certain",
    "general", "common", "concerning", "regards", "respect", "framework", "measures",
    "objection", "pursuant", "rule", "resolution", "draft", "annual", "year", "years",
    # Budget votes label the Commission's section "III", which says nothing about subject.
    "iii", "iia", "section", "sections",
}


def _keywords(titles: list[str], limit: int = 7) -> list[str]:
    """The vocabulary that characterises one end of an axis."""
    counts: dict[str, int] = {}
    for title in titles:
        for word in re.findall(r"[a-z][a-z'-]{2,}", (title or "").lower()):
            if word in BOILERPLATE:
                continue
            counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [word for word, count in ranked[:limit] if count > 1]


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

    from .stories import collect

    print("    stories:")
    stories = collect(data_dir, Path("stories"))
    if stories:
        _write(out, "stories.json", stories)

    # The landscape only needs the handful of votes that define each axis. Shipping the
    # whole per-term vote list for that meant a visitor downloading up to 9MB to render
    # three short lists.
    axis_votes = _rows(
        con,
        """
        WITH ranked AS (
            SELECT vc.term, axis, v.id, v.display_title AS title,
                   strftime(v.timestamp, '%Y-%m-%d') AS date, coefficient,
                   row_number() OVER (PARTITION BY vc.term, axis ORDER BY abs(coefficient) DESC) AS rank
            FROM vote_components vc
            JOIN votes v ON v.id = vc.vote_id
            CROSS JOIN (VALUES (1), (2), (3)) AS axes(axis)
            CROSS JOIN LATERAL (SELECT CASE axes.axis WHEN 1 THEN vc.pc1 WHEN 2 THEN vc.pc2 ELSE vc.pc3 END AS coefficient) c
        )
        SELECT term, axis, id, title, date, round(coefficient, 5) AS coefficient
        FROM ranked WHERE rank <= 6 ORDER BY term, axis, rank
        """,
    )
    for row in axis_votes:
        row["source"] = document_url(row["term"], row["date"])
    _write(out, "axis-votes.json", axis_votes)

    mining = json.loads(con.execute("SELECT pca FROM _mining LIMIT 1").fetchone()[0])

    # One entry per term and axis, with each end described separately. An axis has no
    # inherent direction, so what makes it readable is knowing which votes a member is
    # voting *for* at each end — that is what the sign of a loading tells you.
    axes = []
    for term in terms:
        variance = mining.get(str(term), {}).get("explained_variance", [])
        span = con.execute(
            "SELECT min(pc1), max(pc1), min(pc2), max(pc2), min(pc3), max(pc3)"
            " FROM mep_positions WHERE term = ?",
            [term],
        ).fetchone()
        for axis in (1, 2, 3):
            entry = {
                "term": term,
                "axis": axis,
                "explained_variance": variance[axis - 1] if len(variance) >= axis else None,
                "span": {"min": span[(axis - 1) * 2], "max": span[(axis - 1) * 2 + 1]},
            }
            for end, order in (("positive", "DESC"), ("negative", "ASC")):
                top = _rows(
                    con,
                    f"""
                    SELECT v.id, coalesce(nullif(v.procedure_title, ''), v.display_title) AS title,
                           strftime(v.timestamp, '%Y-%m-%d') AS date,
                           round(vc.pc{axis}, 5) AS coefficient,
                           (SELECT t.subject_label FROM vote_topics t WHERE t.vote_id = v.id LIMIT 1) AS subject
                    FROM vote_components vc JOIN votes v ON v.id = vc.vote_id
                    WHERE vc.term = ? ORDER BY vc.pc{axis} {order} LIMIT 60
                    """,
                    [term],
                )
                for row in top:
                    row["source"] = document_url(term, row["date"])

                # Amendments on one report share a procedure title, so the strongest
                # loadings are often the same dossier several times over. Keep the
                # strongest instance of each so the list shows five different things.
                seen: set[str] = set()
                distinct = []
                for row in top:
                    key = (row["title"] or "").strip().lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    distinct.append(row)

                # Themes, not dossiers. Parliament's subject codes are hierarchical, and
                # the leaf level ("2024 discharge", "2026 budget") describes individual
                # files rather than what an end of an axis is about. Rolling up one level
                # gives 55 themes instead of 337 leaves — coarse enough to characterise,
                # specific enough to mean something. The taxonomy is Parliament's own, so
                # this needs no inference on our part.
                themes = _rows(
                    con,
                    f"""
                    WITH top AS (
                        SELECT vc.vote_id FROM vote_components vc
                        WHERE vc.term = ? ORDER BY vc.pc{axis} {order} LIMIT 120
                    )
                    SELECT coalesce(mid.label, broad.label, leaf.label) AS theme,
                           count(DISTINCT sv.vote_id) AS votes
                    FROM top
                    JOIN oeil_subject_votes sv ON sv.vote_id = top.vote_id
                    JOIN oeil_subjects leaf ON leaf.code = sv.oeil_subject_code
                    LEFT JOIN oeil_subjects mid
                      ON mid.code = array_to_string(array_slice(str_split(sv.oeil_subject_code, '.'), 1, 2), '.')
                    LEFT JOIN oeil_subjects broad
                      ON broad.code = split_part(sv.oeil_subject_code, '.', 1)
                    GROUP BY theme HAVING theme IS NOT NULL
                    ORDER BY votes DESC LIMIT 4
                    """,
                    [term],
                )
                entry[end] = {
                    "votes": distinct[:6],
                    "keywords": _keywords([r["title"] for r in top]),
                    "themes": themes,
                }
            axes.append(entry)
    _write(out, "axes.json", axes)

    source = json.loads(
        con.execute("SELECT source FROM _provenance LIMIT 1").fetchone()[0]
    )
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
            "licence": LICENCE,
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
    # ODbL asks that the licence travel with the database, so it ships beside it.
    (out / "LICENSE.txt").write_text(
        "The data in this directory is published under the "
        f"{LICENCE['published_data']['name']}.\n{LICENCE['published_data']['url']}\n\n"
        + "\n".join(
            f"- {a['name']}: {a.get('statement') or a.get('licence')} <{a['url']}>"
            for a in LICENCE["attribution"]
        )
        + "\n"
    )
    con.close()
