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
   would just be "which term" — then rotate each other term onto T9's frame using the
   MEPs who served in both (307 for T8, 337 for T10). T9 is the reference because it is
   the only term overlapping both others.

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

# FR02: a figure may only be built from ballots verified against Parliament's record.
# Votes that failed verification, or that have no counterpart in the archived record,
# are excluded from every model here rather than being quietly averaged in.
VERIFIED_ONLY = """
    JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
"""


def _matrix(con, term: int | None = None, window: tuple[str, str] | None = None):
    """Ballot matrix for a whole term, or for an arbitrary date window."""
    if window:
        clause, params = "CAST(v.timestamp AS DATE) BETWEEN ? AND ?", list(window)
    else:
        clause, params = "v.term = ?", [term]
    rows = con.execute(
        f"""
        SELECT mv.member_id, mv.vote_id,
               CASE mv.position WHEN 'FOR' THEN 1 ELSE -1 END AS value
        FROM member_votes mv
        JOIN votes v ON v.id = mv.vote_id
        {VERIFIED_ONLY}
        WHERE {clause} AND mv.position IN ('FOR', 'AGAINST')
        """,
        params,
    ).fetchnumpy()
    if len(rows["member_id"]) == 0:
        raise SystemExit("no verified votes in that range")

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
    terms = [
        r[0]
        for r in con.execute(
            """SELECT DISTINCT v.term FROM votes v
               JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
               ORDER BY v.term"""
        ).fetchall()
    ]
    loadings = {}
    for term in terms:
        members, votes, matrix = _matrix(con, term)
        pca = PCA(n_components=N_COMPONENTS)
        fitted = pca.fit_transform(matrix)
        coords[term] = (members, fitted)
        # The loadings say which votes define each axis — the difference between
        # knowing where an MEP sits and being able to say what the axis is about.
        loadings[term] = (votes, pca.components_)
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

    _write_components(con, loadings)

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


def _write_components(con, loadings: dict) -> None:
    """Per-vote coefficient on each component.

    A coefficient says how strongly a vote separates MEPs along an axis. It carries no
    political direction: component sign and rotation are arbitrary, so these rank votes
    by influence, they do not place them on a left-right scale.
    """
    con.execute("DROP TABLE IF EXISTS vote_components")
    con.execute(
        "CREATE TABLE vote_components (term INTEGER, vote_id BIGINT, pc1 DOUBLE, pc2 DOUBLE, pc3 DOUBLE)"
    )
    total = 0
    for term, (votes, components) in loadings.items():
        con.executemany(
            "INSERT INTO vote_components VALUES (?, ?, ?, ?, ?)",
            [
                [term, int(vote_id), float(components[0][i]), float(components[1][i]), float(components[2][i])]
                for i, vote_id in enumerate(votes)
            ],
        )
        total += len(votes)
    print(f"    component loadings stored for {total:,} votes")


COHESION_SQL = """
WITH cast_votes AS (
    SELECT mv.vote_id, mv.member_id, mv.position, mv.group_code, v.term
    FROM member_votes mv
    JOIN votes v ON v.id = mv.vote_id
    JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
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
    # Both levels are kept. The seven top-level areas are the browsable frame; the 414
    # leaf codes are what "votes about asylum" actually needs, and collapsing to the top
    # level threw that away.
    con.execute("DROP TABLE IF EXISTS vote_topics")
    con.execute(
        """
        CREATE TABLE vote_topics AS
        SELECT DISTINCT sv.vote_id,
               split_part(sv.oeil_subject_code, '.', 1) AS topic_code,
               top.label AS topic_label,
               -- The theme: one level down from the broad area, one level up from the
               -- individual file. "Budget of the Union" rather than "2015 discharge".
               -- Defined here so every view speaks the same vocabulary.
               coalesce(mid.code, top.code) AS theme_code,
               coalesce(mid.label, top.label) AS theme_label,
               sv.oeil_subject_code AS subject_code,
               leaf.label AS subject_label
        FROM oeil_subject_votes sv
        JOIN oeil_subjects top ON top.code = split_part(sv.oeil_subject_code, '.', 1)
        JOIN oeil_subjects leaf ON leaf.code = sv.oeil_subject_code
        LEFT JOIN oeil_subjects mid
          ON mid.code = array_to_string(array_slice(str_split(sv.oeil_subject_code, '.'), 1, 2), '.')
        JOIN vote_verification ver ON ver.vote_id = sv.vote_id AND ver.verified
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
    leaves = con.execute("SELECT count(DISTINCT subject_code) FROM vote_topics").fetchone()[0]
    themes = con.execute("SELECT count(DISTINCT theme_code) FROM vote_topics").fetchone()[0]
    print(f"    topics: {total:,} of {covered:,} votes tagged across {themes} themes"
          f" ({leaves} subjects); top: " +
          ", ".join(f"{label} ({n})" for label, n in rows))


def window_positions(data_dir: Path, start: str, end: str) -> None:
    """Fit positions for an arbitrary date window (restores the old temporal_slice).

    Rotated into the same frame as the reference term so a window is comparable with
    everything else rather than floating in its own arbitrary orientation.
    """
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")

    members, votes, matrix = _matrix(con, window=(start, end))
    pca = PCA(n_components=N_COMPONENTS)
    fitted = pca.fit_transform(matrix)
    print(
        f"    {start} to {end}: {len(members)} MEPs x {len(votes)} votes,"
        f" PC1-3 explain {pca.explained_variance_ratio_.sum():.1%}"
    )

    reference = con.execute(
        "SELECT member_id, pc1, pc2, pc3 FROM mep_positions WHERE term = ? ORDER BY member_id",
        [REFERENCE_TERM],
    ).fetchall()
    ref_members = np.array([r[0] for r in reference])
    ref_coords = np.array([[r[1], r[2], r[3]] for r in reference])
    shared = np.intersect1d(ref_members, members)
    if len(shared) >= 3:
        rotation = _align(
            fitted[np.searchsorted(members, shared)],
            ref_coords[np.searchsorted(ref_members, shared)],
        )
        fitted = fitted @ rotation
        print(f"    aligned onto T{REFERENCE_TERM} using {len(shared)} shared MEPs")
    else:
        print("    too few shared MEPs to align — positions are in their own frame")

    con.execute(
        """CREATE TABLE IF NOT EXISTS window_positions (
               start_date DATE, end_date DATE, member_id BIGINT,
               pc1 DOUBLE, pc2 DOUBLE, pc3 DOUBLE)"""
    )
    con.execute("DELETE FROM window_positions WHERE start_date = ? AND end_date = ?", [start, end])
    con.executemany(
        "INSERT INTO window_positions VALUES (?, ?, ?, ?, ?, ?)",
        [[start, end, int(m), float(p[0]), float(p[1]), float(p[2])] for m, p in zip(members, fitted)],
    )
    con.close()
    print(f"    stored {len(members)} positions for the window")


def mine(data_dir: Path) -> None:
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET memory_limit='3GB'")
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
