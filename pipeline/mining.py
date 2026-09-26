"""Compute the analysis layer: political positions, group cohesion, topics.

Three deliberate choices, each of which changes what the numbers mean:

1. **PCA runs on all roll-call votes, not just substantive ones.** Positioning wants as
   many observations as possible, and amendment votes carry real ideological signal.
   Cohesion is a different matter — see below.

2. **Cohesion is reported twice**: over all votes, and over `is_main` votes only. 90%
   of rows are amendments and procedure, so a single all-votes loyalty figure largely
   measures procedural discipline. The `is_main` figure is the one to quote about
   substantive disagreement.

3. **Cross-term positions are aligned, not merely computed.** PCA axes are arbitrary up
   to rotation and sign, so two independently fitted terms are not comparable and
   "moved left since 2019" would be meaningless. We fit each term separately — a joint
   fit is the wrong tool, since the vote sets are disjoint and the dominant component
   would just be "which term" — then rotate T10 onto T9's frame using the 340 MEPs who
   served in both.

Ballots encode as FOR=+1, AGAINST=-1, and abstention or non-voting as 0. That treats
an abstention as a neutral position rather than as missing data.
"""

import json
from pathlib import Path

import duckdb
import numpy as np
from sklearn.decomposition import PCA

from .provenance import now, script_version

N_COMPONENTS = 3


def _matrix(con, term: int):
    rows = con.execute(
        """
        SELECT mv.member_id, mv.vote_id,
               CASE mv.position WHEN 'FOR' THEN 1 ELSE -1 END AS value
        FROM member_votes mv
        JOIN votes v ON v.id = mv.vote_id
        WHERE v.term = ? AND mv.position IN ('FOR', 'AGAINST')
        """,
        [term],
    ).fetchnumpy()

    members = np.unique(rows["member_id"])
    votes = np.unique(rows["vote_id"])
    matrix = np.zeros((len(members), len(votes)), dtype=np.float32)
    matrix[
        np.searchsorted(members, rows["member_id"]),
        np.searchsorted(votes, rows["vote_id"]),
    ] = rows["value"]
    return members, votes, matrix


def _align(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Orthogonal Procrustes: the rotation carrying `source` closest onto `target`."""
    u, _, vt = np.linalg.svd(source.T @ target)
    return u @ vt


REFERENCE_TERM = 9


def positions(con) -> dict:
    meta, coords = {}, {}
    terms = [r[0] for r in con.execute("SELECT DISTINCT term FROM votes ORDER BY term").fetchall()]
    for term in terms:
        members, votes, matrix = _matrix(con, term)
        pca = PCA(n_components=N_COMPONENTS)
        fitted = pca.fit_transform(matrix)
        coords[term] = (members, fitted)
        meta[term] = {
            "meps": len(members),
            "votes": len(votes),
            "explained_variance": [round(float(v), 4) for v in pca.explained_variance_ratio_],
        }
        print(
            f"    T{term}: {len(members)} MEPs x {len(votes)} votes,"
            f" PC1-3 explain {pca.explained_variance_ratio_.sum():.1%}"
        )

    # Every term is rotated into one common frame. T9 is the reference because it is
    # the only term overlapping both others, so each alignment rests on real shared
    # MEPs rather than on a chain of approximations.
    reference_members, reference_fitted = coords[REFERENCE_TERM]
    alignment = {"reference_term": REFERENCE_TERM, "method": "orthogonal Procrustes", "shared_meps": {}}
    for term in terms:
        if term == REFERENCE_TERM:
            continue
        members, fitted = coords[term]
        shared = np.intersect1d(reference_members, members)
        if len(shared) < 3:
            raise SystemExit(f"T{term} shares only {len(shared)} MEPs with the reference term")
        rotation = _align(
            fitted[np.searchsorted(members, shared)],
            reference_fitted[np.searchsorted(reference_members, shared)],
        )
        coords[term] = (members, fitted @ rotation)
        alignment["shared_meps"][str(term)] = int(len(shared))
        print(f"    aligned T{term} onto T{REFERENCE_TERM} using {len(shared)} shared MEPs")
    meta["alignment"] = alignment

    con.execute("DROP TABLE IF EXISTS mep_positions")
    con.execute(
        "CREATE TABLE mep_positions (term INTEGER, member_id BIGINT, pc1 DOUBLE, pc2 DOUBLE, pc3 DOUBLE)"
    )
    for term, (members, fitted) in coords.items():
        con.executemany(
            "INSERT INTO mep_positions VALUES (?, ?, ?, ?, ?)",
            [
                [term, int(m), float(p[0]), float(p[1]), float(p[2])]
                for m, p in zip(members, fitted)
            ],
        )
    return meta


COHESION_SQL = """
WITH cast_votes AS (
    SELECT mv.vote_id, mv.member_id, mv.position, mv.group_code, v.term
    FROM member_votes mv
    JOIN votes v ON v.id = mv.vote_id
    WHERE mv.position <> 'DID_NOT_VOTE'
      AND mv.group_code IS NOT NULL AND mv.group_code <> ''
      {main_filter}
),
tally AS (
    SELECT vote_id, group_code, position, count(*) AS n
    FROM cast_votes GROUP BY 1, 2, 3
),
majority AS (
    SELECT vote_id, group_code, arg_max(position, n) AS group_position,
           max(n) AS with_majority, sum(n) AS group_voted
    FROM tally GROUP BY 1, 2
)
SELECT c.term, c.member_id, c.group_code,
       count(*) AS votes_cast,
       sum(CASE WHEN c.position = m.group_position THEN 1 ELSE 0 END) AS votes_with_group
FROM cast_votes c
JOIN majority m ON m.vote_id = c.vote_id AND m.group_code = c.group_code
GROUP BY 1, 2, 3
"""


def cohesion(con) -> None:
    con.execute("DROP TABLE IF EXISTS mep_cohesion")
    con.execute(
        f"""
        CREATE TABLE mep_cohesion AS
        WITH overall AS ({COHESION_SQL.format(main_filter="")}),
             substantive AS ({COHESION_SQL.format(main_filter="AND v.is_main")})
        SELECT o.term, o.member_id, o.group_code,
               o.votes_cast, o.votes_with_group,
               o.votes_with_group::DOUBLE / nullif(o.votes_cast, 0) AS loyalty,
               s.votes_cast AS main_votes_cast,
               s.votes_with_group AS main_votes_with_group,
               s.votes_with_group::DOUBLE / nullif(s.votes_cast, 0) AS main_loyalty
        FROM overall o
        LEFT JOIN substantive s
          ON s.member_id = o.member_id AND s.term = o.term AND s.group_code = o.group_code
        """
    )

    con.execute("DROP TABLE IF EXISTS group_cohesion")
    con.execute(
        """
        CREATE TABLE group_cohesion AS
        SELECT term, group_code,
               count(*) AS meps,
               sum(votes_cast) AS votes_cast,
               sum(votes_with_group)::DOUBLE / nullif(sum(votes_cast), 0) AS cohesion,
               sum(main_votes_with_group)::DOUBLE / nullif(sum(main_votes_cast), 0) AS main_cohesion
        FROM mep_cohesion GROUP BY 1, 2
        """
    )
    n = con.execute("SELECT count(*) FROM mep_cohesion").fetchone()[0]
    print(f"    cohesion computed for {n:,} MEP-term-group rows")


def topics(con) -> None:
    """Topic labels come from Parliament's own OEIL subject codes, not inferred by us.

    The codes are hierarchical ('6.10.04' sits under '6'), so the top level gives a
    citizen-legible set of themes without any clustering or NLP.
    """
    con.execute("DROP TABLE IF EXISTS vote_topics")
    con.execute(
        """
        CREATE TABLE vote_topics AS
        SELECT DISTINCT sv.vote_id,
               split_part(sv.oeil_subject_code, '.', 1) AS topic_code,
               top.label AS topic_label
        FROM oeil_subject_votes sv
        JOIN oeil_subjects top ON top.code = split_part(sv.oeil_subject_code, '.', 1)
        """
    )
    rows = con.execute(
        """
        SELECT topic_label, count(DISTINCT vote_id) n FROM vote_topics
        GROUP BY 1 ORDER BY n DESC LIMIT 5
        """
    ).fetchall()
    total = con.execute("SELECT count(DISTINCT vote_id) FROM vote_topics").fetchone()[0]
    covered = con.execute("SELECT count(*) FROM votes").fetchone()[0]
    print(f"    topics: {total:,} of {covered:,} votes tagged; top: " +
          ", ".join(f"{label} ({n})" for label, n in rows))


def mine(data_dir: Path) -> None:
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    meta = positions(con)
    cohesion(con)
    topics(con)

    con.execute("DROP TABLE IF EXISTS _mining")
    con.execute("CREATE TABLE _mining (computed_at VARCHAR, script JSON, pca JSON)")
    con.execute(
        "INSERT INTO _mining VALUES (?, ?, ?)",
        [now(), json.dumps(script_version()), json.dumps(meta)],
    )
    con.close()
