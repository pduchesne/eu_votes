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


# A theme counts as one a member breaks with their group on when they diverge there
# markedly more than they do generally. An absolute rate would simply rank members by
# how rebellious they are overall and say nothing about which subjects move them.
DIVERGENCE_MIN_VOTES = 20
DIVERGENCE_MARGIN = 0.15
DIVERGENCE_FLOOR = 0.10


# A subject only qualifies as one someone "stands out on" if its axis rests on enough
# votes to be worth standing out on, and if the comparison group is big enough to have a
# spread at all.
STANDOUT_MIN_VOTES = 100
STANDOUT_MIN_GROUP = 8
STANDOUT_SHOWN = 5
# How far from their own usual position a subject must sit to be worth naming, measured
# in that member's or group's own spread across subjects. Self-calibrating on purpose: a
# group is compared against eight or nine peers and a member against several hundred, so
# a fixed number of standard deviations would mean two different things on the two pages.
STANDOUT_MIN_DEPARTURE = 1.0

# Shared by both standout queries: where each group sits on each topic axis, and the
# range of the whole chamber, which is the backdrop every bar is drawn against.
_DISTRIBUTIONS = f"""
WITH member_group AS (
    SELECT term, member_id, group_code FROM mep_cohesion
    WHERE group_code IS NOT NULL AND group_code <> ''
),
eligible AS (
    -- First divisions only. A subject's second division is a real axis but a poor
    -- basis for "where does this member stand out", which wants the subject's main
    -- argument rather than its residual one.
    SELECT term, theme_code, theme_label, low_group, high_group
    FROM topic_axes WHERE votes >= {STANDOUT_MIN_VOTES} AND component = 1
),
chamber AS (
    -- 5th to 95th percentile, not the extremes: one outlier would otherwise squash
    -- every bar into its middle.
    SELECT term, theme_code,
           quantile_cont(score, 0.05) AS lo,
           quantile_cont(score, 0.95) AS hi,
           median(score) AS mid
    FROM topic_positions WHERE component = 1 GROUP BY 1, 2
),
grp AS (
    SELECT tp.term, tp.theme_code, mg.group_code, count(*) AS n,
           avg(tp.score) AS mean, stddev_samp(tp.score) AS sd,
           quantile_cont(tp.score, 0.25) AS q1, median(tp.score) AS q2,
           quantile_cont(tp.score, 0.75) AS q3
    FROM topic_positions tp
    JOIN member_group mg ON mg.term = tp.term AND mg.member_id = tp.member_id
    WHERE tp.component = 1
    GROUP BY 1, 2, 3
)
"""


def _member_standouts(con) -> dict:
    """The subjects on which a member sits furthest from their own group.

    Measured against their group rather than against the chamber deliberately: distance
    from the chamber is very largely a restatement of which group they joined, and would
    hand every member of a group the same five subjects. Distance from the people they
    normally vote with is the part that is about them.

    This is a different question from the divergence list already on the page, which
    counts votes cast against the group majority. A member can follow their group on
    every division and still sit at its edge, and vice versa.
    """
    rows = _rows(
        con,
        f"""
        {_DISTRIBUTIONS},
        placed AS (
            SELECT tp.member_id, tp.term, e.theme_code AS code, e.theme_label AS label,
                   round(tp.score, 2) AS score,
                   (tp.score - g.mean) / nullif(g.sd, 0) AS z,
                   round(c.lo, 2) AS lo, round(c.hi, 2) AS hi, round(c.mid, 2) AS mid,
                   round(g.q1, 2) AS q1, round(g.q2, 2) AS q2, round(g.q3, 2) AS q3,
                   mg.group_code, e.low_group, e.high_group
            FROM topic_positions tp
            JOIN member_group mg ON mg.term = tp.term AND mg.member_id = tp.member_id
            JOIN eligible e ON e.term = tp.term AND e.theme_code = tp.theme_code
            JOIN grp g ON g.term = tp.term AND g.theme_code = tp.theme_code
                       AND g.group_code = mg.group_code
            JOIN chamber c ON c.term = tp.term AND c.theme_code = tp.theme_code
            WHERE g.n >= {STANDOUT_MIN_GROUP} AND tp.component = 1
        ),
        -- Against their own habit, not against zero. Someone who sits at the edge of
        -- their group on everything is not telling you anything by sitting at its edge
        -- here too; the subjects worth naming are the ones where they depart from their
        -- own usual distance. Two steps, because a window function may not be nested
        -- inside another window's ordering.
        based AS (
            SELECT *, avg(z) OVER (PARTITION BY member_id, term) AS baseline,
                   stddev_samp(z) OVER (PARTITION BY member_id, term) AS spread
            FROM placed
        ),
        scored AS (
            SELECT *, (z - baseline) / nullif(spread, 0) AS departure,
                   row_number() OVER (
                       PARTITION BY member_id, term
                       ORDER BY abs(z - baseline) / nullif(spread, 0) DESC
                   ) AS rank
            FROM based
        )
        SELECT member_id, term, code, label, score, round(z, 2) AS z,
               round(baseline, 2) AS baseline, round(departure, 2) AS departure,
               lo, hi, mid, q1, q2, q3, group_code,
               CASE WHEN z >= baseline THEN high_group ELSE low_group END AS toward,
               -- Which group sits at each end, so the bar can label its own scale.
               low_group AS low_end, high_group AS high_end
        FROM scored
        WHERE rank <= {STANDOUT_SHOWN} AND abs(departure) >= {STANDOUT_MIN_DEPARTURE}
        ORDER BY member_id, term, rank
        """,
    )
    standouts: dict[tuple, list] = {}
    for row in rows:
        key = (row.pop("member_id"), row.pop("term"))
        standouts.setdefault(key, []).append(row)
    print(f"    standouts: {len(standouts):,} member-terms with a subject at least"
          f" {STANDOUT_MIN_DEPARTURE}x their own spread from where they usually sit")
    return standouts


def _write_group_pages(con, out: Path) -> None:
    """Per group: where it sits apart from the rest of the chamber's groups.

    The comparison here is between groups, not within one: a group stands out on a
    subject when its position is unlike the other groups' positions on that subject. The
    other groups' medians ship alongside, because "unusual" means nothing without them.
    """
    rows = _rows(
        con,
        f"""
        {_DISTRIBUTIONS},
        spread AS (
            SELECT term, theme_code, avg(mean) AS mean_of_means,
                   stddev_samp(mean) AS sd_of_means, count(*) AS groups
            FROM grp WHERE n >= {STANDOUT_MIN_GROUP} GROUP BY 1, 2
        ),
        placed AS (
            SELECT g.term, g.group_code, e.theme_code AS code, e.theme_label AS label,
                   g.n AS meps, round(g.q2, 2) AS median,
                   round(c.lo, 2) AS lo, round(c.hi, 2) AS hi, round(c.mid, 2) AS mid,
                   round(g.q1, 2) AS q1, round(g.q3, 2) AS q3,
                   (g.mean - s.mean_of_means) / nullif(s.sd_of_means, 0) AS z,
                   e.low_group, e.high_group
            FROM grp g
            JOIN eligible e ON e.term = g.term AND e.theme_code = g.theme_code
            JOIN chamber c ON c.term = g.term AND c.theme_code = g.theme_code
            JOIN spread s ON s.term = g.term AND s.theme_code = g.theme_code
            WHERE g.n >= {STANDOUT_MIN_GROUP} AND s.groups >= 4
        ),
        -- A group at one end of the chamber's main division is at that end on nearly
        -- every subject, so ranking by raw distance returns five ways of saying so.
        -- Ranking against the group's own average distance returns the subjects where it
        -- departs from its own line.
        based AS (
            SELECT *, avg(z) OVER (PARTITION BY term, group_code) AS baseline,
                   stddev_samp(z) OVER (PARTITION BY term, group_code) AS spread
            FROM placed
        ),
        scored AS (
            SELECT *, (z - baseline) / nullif(spread, 0) AS departure,
                   row_number() OVER (
                       PARTITION BY term, group_code
                       ORDER BY abs(z - baseline) / nullif(spread, 0) DESC
                   ) AS rank
            FROM based
        )
        SELECT term, group_code, code, label, meps, median, lo, hi, mid, q1, q3,
               round(z, 2) AS z, round(baseline, 2) AS baseline,
               round(departure, 2) AS departure,
               CASE WHEN z >= baseline THEN high_group ELSE low_group END AS toward,
               low_group AS low_end, high_group AS high_end
        FROM scored
        WHERE rank <= {STANDOUT_SHOWN} AND abs(departure) >= {STANDOUT_MIN_DEPARTURE}
        ORDER BY term, group_code, rank
        """,
    )

    # Every group's median on the subjects that matter, so a bar can show the field the
    # highlighted group stands out from.
    ticks: dict[tuple, list] = {}
    for term, code, group_code, median in con.execute(
        f"""
        {_DISTRIBUTIONS}
        SELECT g.term, g.theme_code, g.group_code, round(g.q2, 2)
        FROM grp g WHERE g.n >= {STANDOUT_MIN_GROUP}
        """
    ).fetchall():
        ticks.setdefault((term, code), []).append({"code": group_code, "median": median})

    groups: dict[str, dict] = {}
    for row in rows:
        term, group_code = row.pop("term"), row.pop("group_code")
        row["field"] = ticks.get((term, row["code"]), [])
        groups.setdefault(group_code, {}).setdefault(str(term), []).append(row)

    _write(out, "groups-detail.json", groups)


def _write_member_pages(con, out: Path, standouts: dict) -> None:
    """One small file per member, so a profile costs a reader only their own page."""
    con.execute(
        """
        CREATE OR REPLACE TEMP VIEW cast_votes AS
        SELECT mv.vote_id, mv.member_id, mv.position, mv.group_code, v.term
        FROM member_votes mv
        JOIN votes v ON v.id = mv.vote_id
        JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
        WHERE mv.position <> 'DID_NOT_VOTE'
          AND mv.group_code IS NOT NULL AND mv.group_code <> ''
        """
    )
    con.execute(
        """
        CREATE OR REPLACE TEMP VIEW group_majority AS
        SELECT vote_id, group_code, arg_max(position, n) AS pos
        FROM (SELECT vote_id, group_code, position, count(*) n FROM cast_votes GROUP BY 1, 2, 3)
        GROUP BY 1, 2
        """
    )

    # Participation is only answerable where the source records non-voting. The 8th
    # term's does not, so it is left null rather than reported as perfect attendance.
    participation = {}
    for member_id, term, eligible, cast in con.execute(
        """
        SELECT mv.member_id, v.term, count(*),
               count(*) FILTER (WHERE mv.position <> 'DID_NOT_VOTE')
        FROM member_votes mv
        JOIN votes v ON v.id = mv.vote_id
        JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
        GROUP BY 1, 2
        """
    ).fetchall():
        participation[(member_id, term)] = (eligible, cast)

    divergence: dict[tuple, list] = {}
    for member_id, term, code, label, votes, rate, baseline in con.execute(
        f"""
        WITH per_theme AS (
            SELECT c.member_id, c.term, t.theme_code, t.theme_label, count(*) AS votes,
                   avg(CASE WHEN c.position <> m.pos THEN 1.0 ELSE 0 END) AS rate
            FROM cast_votes c
            JOIN group_majority m USING (vote_id, group_code)
            JOIN vote_topics t ON t.vote_id = c.vote_id
            GROUP BY 1, 2, 3, 4 HAVING count(*) >= {DIVERGENCE_MIN_VOTES}
        ),
        baseline AS (
            SELECT c.member_id, c.term,
                   avg(CASE WHEN c.position <> m.pos THEN 1.0 ELSE 0 END) AS rate
            FROM cast_votes c JOIN group_majority m USING (vote_id, group_code)
            GROUP BY 1, 2
        )
        SELECT p.member_id, p.term, p.theme_code, p.theme_label, p.votes,
               round(p.rate, 4), round(b.rate, 4)
        FROM per_theme p JOIN baseline b USING (member_id, term)
        WHERE p.rate >= b.rate + {DIVERGENCE_MARGIN} AND p.rate >= {DIVERGENCE_FLOOR}
        ORDER BY p.rate - b.rate DESC
        """
    ).fetchall():
        divergence.setdefault((member_id, term), []).append(
            {"code": code, "label": label, "votes": votes, "rate": rate, "baseline": baseline}
        )

    records = {}
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
        member_id, term = row.pop("member_id"), row.pop("term")
        eligible, cast = participation.get((member_id, term), (None, None))
        pcs = [row.pop("pc1"), row.pop("pc2"), row.pop("pc3")]
        records.setdefault(member_id, {})[str(term)] = {
            **row,
            "position": None if pcs[0] is None else [round(v, 3) for v in pcs],
            "votes_eligible": eligible,
            # Term 8 lists only members who voted, so its denominator is the votes they
            # took part in — a participation rate from it would be meaningless.
            "participation": None if term == 8 or not eligible else round(cast / eligible, 4),
            "divergence": divergence.get((member_id, term), [])[:6],
            "standout": standouts.get((member_id, term), []),
        }

    profiles = {
        m["id"]: m
        for m in _rows(
            con,
            """
            SELECT id, first_name, last_name, country_code, gender, constituency,
                   photo_url, ep_url
            FROM members
            """,
        )
    }

    folder = out / "members"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.json"):
        old.unlink()
    for member_id, terms in records.items():
        profile = profiles.get(member_id, {"id": member_id})
        (folder / f"{member_id}.json").write_text(
            json.dumps({**profile, "record": terms}, separators=(",", ":")) + "\n"
        )
    flagged = sum(1 for t in records.values() for r in t.values() if r["divergence"])
    print(f"    members/: {len(records):,} profiles, {flagged:,} member-terms with a divergent theme")


# How many genuinely different texts to show at each end of a topic axis.
ANCHORS_SHOWN = 5


def _write_topic_axes(con, out: Path, terms: list[int]) -> None:
    """Named axes, one per theme, with member scores and what each end is about.

    Member scores travel raw rather than pre-binned because the reader chooses which
    three themes frame the 3D view, and every such choice needs the same numbers. One
    array per theme, aligned to a single member list per term, keeps that affordable.
    """
    if not con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'topic_axes'"
    ).fetchone()[0]:
        print("    topic-axes.json: skipped — no topic axes in the store (run `mine`)")
        return

    candidates: dict[tuple, dict[str, list]] = {}
    for row in _rows(
        con,
        """
        SELECT av.term, av.theme_code, av.component, av.side, av.vote_id AS id,
               coalesce(nullif(v.procedure_title, ''), v.display_title) AS title,
               strftime(v.timestamp, '%Y-%m-%d') AS date,
               round(av.loading, 5) AS coefficient,
               av.low_group_for, av.high_group_for,
               v.count_for, v.count_against
        FROM topic_axis_votes av JOIN votes v ON v.id = av.vote_id
        ORDER BY av.term, av.theme_code, av.component, av.side, av.ordinal
        """,
    ):
        key = (row.pop("term"), row.pop("theme_code"), row.pop("component"))
        candidates.setdefault(key, {"negative": [], "positive": []})[row.pop("side")].append(row)

    def name(row) -> str:
        return (row["title"] or "").strip().lower()

    anchors: dict[tuple, dict[str, list]] = {}
    for key, sides in candidates.items():
        # A title appearing at both ends is two opposed amendments to one report. That is
        # real — Parliament's record names no amendment, so the two votes are genuinely
        # indistinguishable by title — but a reader seeing the same words at both ends
        # reads it as a mistake. So texts that do tell the ends apart go first, and any
        # that cannot are kept and flagged rather than dropped.
        shared = {name(r) for r in sides["negative"]} & {name(r) for r in sides["positive"]}
        for side, rows in sides.items():
            distinguishing = [r for r in rows if name(r) not in shared]
            ambiguous = [r for r in rows if name(r) in shared]
            chosen, seen = [], set()
            for row in distinguishing + ambiguous:
                if len(chosen) >= ANCHORS_SHOWN or name(row) in seen:
                    continue
                seen.add(name(row))
                chosen.append(
                    {**row, "source": document_url(key[0], row["date"]),
                     "shared_with_other_end": name(row) in shared}
                )
            anchors.setdefault(key, {})[side] = chosen

    scores: dict[tuple, dict[int, float]] = {}
    for term, code, component, member_id, score in con.execute(
        "SELECT term, theme_code, component, member_id, score FROM topic_positions"
    ).fetchall():
        scores.setdefault((term, code, component), {})[member_id] = score

    payload = {
        "method": json.loads(
            con.execute("SELECT pca FROM _mining LIMIT 1").fetchone()[0]
        ).get("topic_axes", {}),
        "terms": {},
    }
    for term in terms:
        axes = _rows(
            con,
            """
            SELECT
                   -- A stable handle for one division of one subject, since a subject
                   -- now has two and the interface needs to name each.
                   CASE WHEN component = 1 THEN theme_code
                        ELSE theme_code || '~' || component END AS id,
                   theme_code AS code, component, theme_label AS label, votes, members,
                   round(explained_variance, 4) AS explained_variance,
                   global_alignment, support_correlation, low_group, high_group,
                   -- Where this subject's axis points in the main three-component
                   -- space. What lets a reader's own choice of three be judged for
                   -- whether it spans that space or collapses onto one division.
                   [dir1, dir2, dir3] AS direction
            FROM topic_axes WHERE term = ? ORDER BY votes DESC, component
            """,
            [term],
        )
        if not axes:
            continue
        frame = _rows(
            con,
            """SELECT CASE WHEN component = 1 THEN theme_code
                           ELSE theme_code || '~' || component END AS id, span
               FROM topic_frame WHERE term = ? ORDER BY slot""",
            [term],
        )
        # One member list per term, so each theme ships an array of numbers rather than
        # repeating identifiers 30-odd times over.
        member_ids = sorted(
            {
                m
                for a in axes
                for m in scores.get((term, a["code"], a["component"]), {})
            }
        )
        for axis in axes:
            by_member = scores.get((term, axis["code"], axis["component"]), {})
            # Two decimals: these are binned into a density curve and shown to one decimal
            # in a tooltip, so more digits would only pad the download.
            axis["scores"] = [
                None if by_member.get(m) is None else round(by_member[m], 2)
                for m in member_ids
            ]
            axis["ends"] = anchors.get(
                (term, axis["code"], axis["component"]), {"negative": [], "positive": []}
            )
        payload["terms"][str(term)] = {
            "members": member_ids,
            "topics": axes,
            # The default three: chosen to span the main space, not for being the
            # busiest. The busiest all follow the same division in most terms.
            "frame": {
                "topics": [row["id"] for row in frame],
                "span": frame[0]["span"] if frame else None,
            },
        }

    _write(out, "topic-axes.json", payload)


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
                SELECT t.theme_code AS topic_code, t.theme_label AS topic_label,
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
                       list_filter(list(DISTINCT t.theme_label), x -> x IS NOT NULL) AS topics,
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
                    SELECT t.theme_label AS theme, t.theme_code AS code,
                           count(DISTINCT t.vote_id) AS votes
                    FROM top JOIN vote_topics t ON t.vote_id = top.vote_id
                    GROUP BY t.theme_label, t.theme_code ORDER BY votes DESC LIMIT 4
                    """,
                    [term],
                )
                entry[end] = {
                    "votes": distinct[:6],
                    "keywords": _keywords([r["title"] for r in top]),
                    "themes": themes,
                }
            # Which subjects carry this axis, over and above their size. Exact rather
            # than fitted: a score is a sum over votes, and votes belong to subjects.
            entry["subjects"] = _rows(
                con,
                """
                SELECT theme_code AS code, theme_label AS label,
                       carries, size, lift
                FROM axis_subjects
                WHERE term = ? AND axis = ? AND size >= 0.005
                ORDER BY lift DESC
                """,
                [term, axis],
            )
            axes.append(entry)
    _write(out, "axes.json", axes)

    _write_topic_axes(con, out, terms)

    # The same topic axes as directions in the main landscape's own frame, so that view
    # can draw a named subject through its cloud without anyone having to leave it. Kept
    # apart from topic-axes.json because that bundle carries a score per member per
    # subject and is most of a megabyte; this is a few numbers per subject.
    directions: dict[str, list] = {}
    for row in _rows(
        con,
        """
        SELECT term,
               CASE WHEN component = 1 THEN theme_code
                    ELSE theme_code || '~' || component END AS id,
               theme_code AS code, component, theme_label AS label, votes,
               [dir1, dir2, dir3] AS direction,
               -- How much of this subject's division the three main axes account for.
               -- An arrow for a subject that mostly divides members in some fourth
               -- direction must not be drawn as confidently as one that lies in view.
               round(space_fit, 3) AS fit,
               low_group, high_group
        FROM topic_axes
        WHERE dir1 IS NOT NULL
        ORDER BY term, votes DESC, component
        """,
    ):
        directions.setdefault(str(row.pop("term")), []).append(row)
    _write(out, "landscape-axes.json", directions)

    # Per-theme detail: what the theme covers, how each group treated it, and its most
    # recent votes. Kept separate from the cloud so a topic page loads text first.
    theme_rows = _rows(
        con,
        """
        SELECT t.theme_code AS code, t.theme_label AS label,
               count(DISTINCT t.vote_id) AS votes,
               min(strftime(v.timestamp, '%Y-%m-%d')) AS first_vote,
               max(strftime(v.timestamp, '%Y-%m-%d')) AS last_vote,
               list(DISTINCT v.term) AS terms
        FROM vote_topics t JOIN votes v ON v.id = t.vote_id
        GROUP BY 1, 2 ORDER BY votes DESC
        """,
    )
    for theme in theme_rows:
        theme["recent"] = _rows(
            con,
            """
            SELECT v.id, coalesce(nullif(v.procedure_title, ''), v.display_title) AS title,
                   strftime(v.timestamp, '%Y-%m-%d') AS date, v.term, v.result,
                   v.count_for, v.count_against
            FROM vote_topics t JOIN votes v ON v.id = t.vote_id
            WHERE t.theme_code = ? ORDER BY v.timestamp DESC LIMIT 30
            """,
            [theme["code"]],
        )
        for row in theme["recent"]:
            row["source"] = document_url(row["term"], row["date"])
        theme["groups"] = _rows(
            con,
            """
            WITH tallies AS (
                SELECT mv.vote_id, mv.group_code, mv.position, count(*) n
                FROM member_votes mv
                JOIN vote_topics t ON t.vote_id = mv.vote_id AND t.theme_code = ?
                WHERE mv.position <> 'DID_NOT_VOTE' AND mv.group_code IS NOT NULL
                GROUP BY 1, 2, 3
            ),
            majority AS (SELECT vote_id, group_code, arg_max(position, n) AS pos FROM tallies GROUP BY 1, 2)
            SELECT group_code AS code, count(*) AS votes,
                   round(avg(CASE WHEN pos = 'FOR' THEN 1.0 ELSE 0 END), 4) AS support
            FROM majority GROUP BY 1 HAVING count(*) >= 10 ORDER BY support DESC
            """,
            [theme["code"]],
        )
    _write(out, "topics-detail.json", theme_rows)

    # Every vote as a point in the same frame the members live in, plus an index of
    # which points belong to each theme. Compact on purpose: this is the one bundle a
    # visitor only downloads if they open a topic page.
    cloud = con.execute(
        """
        SELECT vc.vote_id, round(vc.pc1, 5), round(vc.pc2, 5), round(vc.pc3, 5), v.term
        FROM vote_components vc JOIN votes v ON v.id = vc.vote_id
        ORDER BY vc.vote_id
        """
    ).fetchall()
    position = {row[0]: i for i, row in enumerate(cloud)}
    index: dict[str, list[int]] = {}
    for theme_code, vote_id in con.execute(
        "SELECT theme_code, vote_id FROM vote_topics"
    ).fetchall():
        if vote_id in position:
            index.setdefault(theme_code, []).append(position[vote_id])
    _write(
        out,
        "vote-cloud.json",
        {"votes": [[r[0], r[1], r[2], r[3], r[4]] for r in cloud], "themes": index},
    )

    _write_group_pages(con, out)
    _write_member_pages(con, out, _member_standouts(con))

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
            # Small enough to travel with the metadata, so a country filter can show
            # names without a second request.
            "countries": {
                row["code"]: row["label"]
                for row in _rows(con, "SELECT code, label FROM countries ORDER BY label")
            },
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
