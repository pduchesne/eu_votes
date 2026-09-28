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
from itertools import combinations
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


def _insert(con, table: str, rows: list[list], width: int, chunk: int = 500) -> None:
    """Bulk insert. `executemany` prepares and executes once per row, which costs minutes
    on the tens of thousands of rows this module writes; one statement per 500 rows does
    the same work in seconds."""
    if not rows:
        return
    placeholders = "(" + ", ".join(["?"] * width) + ")"
    for start in range(0, len(rows), chunk):
        batch = rows[start : start + chunk]
        con.execute(
            f"INSERT INTO {table} VALUES " + ", ".join([placeholders] * len(batch)),
            [value for row in batch for value in row],
        )


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
        # Held as (votes x components) so the same rotation applies to them as to the
        # member scores below.
        loadings[term] = (votes, pca.components_.T)
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
        # Loadings must be rotated with the scores. They are two halves of one
        # factorisation: rotating only the members leaves every vote describing the
        # unrotated axes, so "voting for this moves a member that way" silently becomes
        # false for every term but the reference. Because the rotation is orthogonal,
        # applying it to both sides leaves the reconstruction untouched.
        vote_ids, vote_loadings = loadings[term]
        loadings[term] = (vote_ids, vote_loadings @ rotation)
        alignment["shared_meps"][str(term)] = int(len(shared))
        print(f"    aligned T{term} onto T{REFERENCE_TERM} using {len(shared)} shared MEPs")
    meta["alignment"] = alignment

    _write_components(con, loadings)

    con.execute("DROP TABLE IF EXISTS mep_positions")
    con.execute(
        "CREATE TABLE mep_positions (term INTEGER, member_id BIGINT, pc1 DOUBLE, pc2 DOUBLE, pc3 DOUBLE)"
    )
    for term, (members, fitted) in coords.items():
        _insert(
            con,
            "mep_positions",
            [
                [term, int(m), float(p[0]), float(p[1]), float(p[2])]
                for m, p in zip(members, fitted)
            ],
            5,
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
        _insert(
            con,
            "vote_components",
            [
                [term, int(vote_id), float(row[0]), float(row[1]), float(row[2])]
                for vote_id, row in zip(votes, components)
            ],
            5,
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


# A topic axis needs enough votes to be a measurement rather than an anecdote, and
# enough members for a group distribution to mean anything.
TOPIC_MIN_VOTES = 40
TOPIC_MIN_MEMBERS = 100
TOPIC_MIN_GROUP = 5
# A subject may carry an axis on 40 votes but should not be proposed as one of the three
# framing a 3D view on that evidence. The default frame draws from a higher bar.
FRAME_MIN_VOTES = 150
# More anchors than any view shows: amendments to one report share a procedure title, so
# publishing deduplicates these down to a handful of genuinely different texts.
ANCHORS_PER_END = 16


def _finite(value: float) -> float | None:
    """None rather than NaN: a NaN reaches the published JSON as the literal `NaN`, which
    is not JSON, and takes the whole bundle down with it."""
    return None if value is None or not np.isfinite(value) else round(float(value), 4)


def _direction(space: np.ndarray, score: np.ndarray) -> tuple[np.ndarray, float]:
    """Where a topic axis points in the main three-component space, and how much of it
    lives there at all.

    Least squares rather than three separate correlations: the global components are
    uncorrelated over a whole term but not over the subset of members who voted on one
    subject, and marginal correlations on that subset can sum to more than the whole.
    Coefficients are standardised so no component wins for being on a larger scale.

    The second return value is the share of the subject's axis the three components
    account for. A direction alone would let a subject whose division is mostly
    perpendicular to the whole political space be drawn as confidently as one that lies
    squarely in it, so anything drawing these arrows should scale them by this.
    """
    centred = space - space.mean(axis=0)
    residual = score - score.mean()
    beta, *_ = np.linalg.lstsq(centred, residual, rcond=None)
    fitted = centred @ beta
    total = float((residual ** 2).sum())
    fit = float(1 - ((residual - fitted) ** 2).sum() / total) if total else 0.0
    beta = beta * centred.std(axis=0)
    norm = float(np.linalg.norm(beta))
    return (beta / norm if norm else np.zeros(N_COMPONENTS)), max(0.0, fit)


def _span(directions: list[np.ndarray]) -> float:
    """How much of the main space three topic axes between them cover.

    The determinant of the three unit directions: 1 when they are mutually
    perpendicular, 0 when they are coplanar or collinear. This is the number that decides
    whether a 3D frame is a cloud or a streak — three subjects that all follow the
    chamber's first axis plot the same division three times over.

    Not to be confused with how much of member position the three could *reconstruct*:
    least squares can recover a lot from a badly conditioned basis by amplifying small
    differences, but no amount of amplification makes a collapsed picture readable.
    """
    return float(abs(np.linalg.det(np.array(directions))))


def topic_axes(con) -> dict:
    """One axis per theme: the main line of division inside that subject alone.

    The global axes are the most discriminating description of the chamber but not a
    legible one — "axis 2" is not something a citizen holds an opinion about. Fitting a
    component to one theme's votes gives an axis that can be named, at the cost of
    explaining less.

    What it is not is a for-or-against scale. Each vote enters with a signed loading
    learned from who votes together, so voting *for* a restrictive text and voting *for*
    a permissive one push a member to opposite ends. `support_correlation` records how
    far the axis agrees with the naive reading — the share of the theme's votes a member
    backed — precisely because on many themes it does not.

    Direction is arbitrary in PCA, so each axis is oriented to agree with the term's
    first global component; where that correlation is too weak to decide (|r| < 0.1) the
    most influential vote is made positive instead, which at least makes the choice
    deterministic across runs. Neither rule makes an end "for" or "against" anything:
    only the anchoring votes say what an end means.
    """
    themes = con.execute(
        f"""
        SELECT v.term, t.theme_code, t.theme_label, count(DISTINCT t.vote_id) AS votes
        FROM vote_topics t
        JOIN votes v ON v.id = t.vote_id
        JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
        GROUP BY 1, 2, 3 HAVING count(DISTINCT t.vote_id) >= {TOPIC_MIN_VOTES}
        ORDER BY 1, votes DESC
        """
    ).fetchall()

    reference = {
        (term, member): np.array(components)
        for term, member, *components in con.execute(
            "SELECT term, member_id, pc1, pc2, pc3 FROM mep_positions"
        ).fetchall()
    }
    group_of = {
        (term, member): code
        for term, member, code in con.execute(
            """SELECT term, member_id, group_code FROM mep_cohesion
               WHERE group_code IS NOT NULL AND group_code <> ''"""
        ).fetchall()
    }

    for table, columns in (
        (
            "topic_axes",
            "term INTEGER, theme_code VARCHAR, theme_label VARCHAR, votes INTEGER,"
            " members INTEGER, explained_variance DOUBLE, global_alignment DOUBLE,"
            " support_correlation DOUBLE, low_group VARCHAR, high_group VARCHAR,"
            " dir1 DOUBLE, dir2 DOUBLE, dir3 DOUBLE, space_fit DOUBLE",
        ),
        (
            # The three subjects proposed as a default frame, and how well they span.
            "topic_frame",
            "term INTEGER, slot INTEGER, theme_code VARCHAR, span DOUBLE",
        ),
        ("topic_positions", "term INTEGER, theme_code VARCHAR, member_id BIGINT, score DOUBLE"),
        (
            # `side` rather than `end`, and `ordinal` rather than `rank`: both of the
            # obvious names are reserved words in SQL.
            "topic_axis_votes",
            "term INTEGER, theme_code VARCHAR, vote_id BIGINT, loading DOUBLE,"
            " side VARCHAR, ordinal INTEGER, low_group_for DOUBLE, high_group_for DOUBLE",
        ),
    ):
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"CREATE TABLE {table} ({columns})")

    kept, skipped = 0, 0
    directions: dict[int, dict[str, tuple]] = {}
    for term, code, label, _ in themes:
        rows = con.execute(
            """
            SELECT mv.member_id, mv.vote_id,
                   CASE mv.position WHEN 'FOR' THEN 1 ELSE -1 END AS value
            FROM member_votes mv
            JOIN votes v ON v.id = mv.vote_id
            JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
            JOIN vote_topics t ON t.vote_id = v.id AND t.theme_code = ?
            WHERE v.term = ? AND mv.position IN ('FOR', 'AGAINST')
            """,
            [code, term],
        ).fetchnumpy()
        members = np.unique(rows["member_id"])
        votes = np.unique(rows["vote_id"])
        if len(members) < TOPIC_MIN_MEMBERS:
            skipped += 1
            continue
        matrix = np.zeros((len(members), len(votes)), dtype=np.float32)
        matrix[
            np.searchsorted(members, rows["member_id"]),
            np.searchsorted(votes, rows["vote_id"]),
        ] = rows["value"]

        pca = PCA(n_components=1)
        score = pca.fit_transform(matrix)[:, 0]
        loading = pca.components_[0]

        space = np.array(
            [reference.get((term, int(m)), np.zeros(N_COMPONENTS)) for m in members]
        )
        alignment = float(np.corrcoef(score, space[:, 0])[0, 1]) if space.any() else 0.0
        flip = (
            alignment < 0
            if abs(alignment) >= 0.1
            else loading[int(np.argmax(np.abs(loading)))] < 0
        )
        if flip:
            score, loading, alignment = -score, -loading, -alignment

        # The naive reading, kept alongside so a view can say when it misleads: on some
        # themes a member who backed most texts sits at one end, on others it inverts.
        cast = np.maximum((matrix != 0).sum(axis=1), 1)
        share_for = (matrix == 1).sum(axis=1) / cast
        support = float(np.corrcoef(score, share_for)[0, 1])

        groups = np.array([group_of.get((term, int(m)), "") for m in members])
        means = {
            g: float(score[groups == g].mean())
            for g in set(groups)
            if g and (groups == g).sum() >= TOPIC_MIN_GROUP
        }
        low = min(means, key=means.get) if means else None
        high = max(means, key=means.get) if means else None

        # Which way this subject's axis points in the main space. Needed to choose a
        # frame that spans it rather than three views of the same division.
        pointing, space_fit = (
            _direction(space, score) if space.any() else (np.zeros(N_COMPONENTS), 0.0)
        )
        directions.setdefault(term, {})[code] = (pointing, len(votes))

        con.execute(
            "INSERT INTO topic_axes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                term, code, label, len(votes), len(members),
                float(pca.explained_variance_ratio_[0]), _finite(alignment),
                _finite(support), low, high,
                *(_finite(v) for v in pointing), _finite(space_fit),
            ],
        )
        _insert(
            con,
            "topic_positions",
            [[term, code, int(m), round(float(s), 3)] for m, s in zip(members, score)],
            4,
        )

        # What each end is about: the votes that pull hardest towards it, with how the
        # two extreme groups actually voted on each. That pairing is what shows the
        # ends are opposed positions rather than two piles of yes-votes.
        order = np.argsort(loading)
        anchors = []
        for side, indices in (
            ("negative", order[:ANCHORS_PER_END]),
            ("positive", order[::-1][:ANCHORS_PER_END]),
        ):
            for ordinal, index in enumerate(indices, start=1):
                shares = []
                for group in (low, high):
                    selection = (groups == group) & (matrix[:, index] != 0)
                    shares.append(
                        _finite((matrix[selection, index] == 1).mean())
                        if group and selection.any()
                        else None
                    )
                anchors.append(
                    [term, code, int(votes[index]), round(float(loading[index]), 6),
                     side, ordinal, *shares]
                )
        _insert(con, "topic_axis_votes", anchors, 8)
        kept += 1

    frames = _choose_frames(con, directions)

    naive = con.execute(
        "SELECT count(*) FROM topic_axes WHERE abs(support_correlation) < 0.7"
    ).fetchone()[0]
    print(
        f"    topic axes: {kept} fitted, {skipped} themes too thinly attended;"
        f" on {naive} of them 'backed most texts' does not track the division"
    )
    return {
        "themes_fitted": kept,
        "themes_skipped": skipped,
        "min_votes": TOPIC_MIN_VOTES,
        "min_members": TOPIC_MIN_MEMBERS,
        "frame_min_votes": FRAME_MIN_VOTES,
        "frames": frames,
        "orientation": "aligned with the term's first global component; "
                       "the most influential vote made positive where |r| < 0.1",
    }


def _choose_frames(con, directions: dict[int, dict[str, tuple]]) -> dict:
    """Pick the three subjects that best span the main space, per term.

    Choosing the busiest subjects instead is the obvious default and the wrong one: in
    the 9th term the three with most votes all follow the chamber's first axis, so the
    3D view plots that one division three times and the other two components never
    appear at all. Spanning is the property a frame needs; volume is a tie-breaker the
    vote floor already handles.

    Exhaustive over the eligible subjects — a few thousand triples — because a greedy
    walk down the components does measurably worse, and on the 8th term worse than not
    choosing at all.
    """
    chosen = {}
    for term, axes in directions.items():
        pool = [code for code, (_, votes) in axes.items() if votes >= FRAME_MIN_VOTES]
        if len(pool) < N_COMPONENTS:
            pool = list(axes)
        if len(pool) < N_COMPONENTS:
            continue
        best = max(
            combinations(pool, N_COMPONENTS),
            key=lambda triple: _span([axes[c][0] for c in triple]),
        )
        span = _span([axes[c][0] for c in best])
        # Each slot takes the subject nearest that component, so the frame stays
        # recognisable against the main landscape rather than arriving in arbitrary order.
        remaining, order = list(best), []
        for slot in range(N_COMPONENTS):
            pick = max(remaining, key=lambda c: abs(axes[c][0][slot]))
            order.append(pick)
            remaining.remove(pick)
        _insert(
            con,
            "topic_frame",
            [[term, slot, code, span] for slot, code in enumerate(order)],
            4,
        )
        chosen[str(term)] = {"topics": order, "span": round(span, 4)}
        print(f"    T{term} frame spans {span:.2f} of the main space: "
              + " / ".join(order))
    return chosen


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
    # Last: it needs the global axes to orient against, the themes to slice by, and the
    # group memberships to describe the ends with.
    meta["topic_axes"] = topic_axes(con)

    con.execute("DROP TABLE IF EXISTS _mining")
    con.execute("CREATE TABLE _mining (computed_at VARCHAR, script JSON, pca JSON)")
    con.execute(
        "INSERT INTO _mining VALUES (?, ?, ?)",
        [now(), json.dumps(script_version()), json.dumps(meta)],
    )
    con.close()
