"""Publish authored stories, with their figures generated rather than typed (TK19, FR05).

A story is prose written by a person. It is persuasive in a way a table is not, and it
borrows the credibility that the verification work built — credibility that is only
warranted for claims traceable to Parliament's record. So the pipeline enforces the part
that can be enforced: **every number a story quotes is computed here, at publish time,
from the verified data.** Prose cannot silently drift from the figures it describes,
because the prose does not contain the figures.

A story declares named figures in its front matter as structured specifications, never
as SQL. That keeps stories declarative and auditable, and means an author cannot reach
past the published data into arbitrary queries.

What the pipeline cannot enforce is whether the *reading* is fair. That is why stories
carry an author and a date, and why the site renders them as visibly authored rather
than as captions on a chart.
"""

import json
import re
from pathlib import Path

import duckdb

FIGURE = re.compile(r"\{\{([a-z0-9_]+)\}\}")

# Votes matching a subject, restricted to substantive votes where the term distinguishes
# them. The 8th term's source carries no such flag, so it falls back to all votes — the
# same rule the topic tables use, stated in the figure's own provenance.
_SCOPE = """
    FROM member_votes mv
    JOIN votes v ON v.id = mv.vote_id
    JOIN vote_verification ver ON ver.vote_id = v.id AND ver.verified
    JOIN vote_topics t ON t.vote_id = v.id
    WHERE v.term = ?
      AND lower(t.subject_label) LIKE lower(?)
      AND (v.is_main OR v.term = 8)
      AND mv.position <> 'DID_NOT_VOTE'
      AND mv.group_code IS NOT NULL
"""


def group_support(con, spec):
    """Share of votes on a subject where a group's majority voted in favour."""
    row = con.execute(
        f"""
        WITH ballots AS (SELECT mv.vote_id, mv.group_code, mv.position {_SCOPE}),
             tally AS (SELECT vote_id, group_code, position, count(*) n FROM ballots GROUP BY 1,2,3),
             majority AS (SELECT vote_id, group_code, arg_max(position, n) AS pos FROM tally GROUP BY 1,2)
        SELECT count(*), avg(CASE WHEN pos = 'FOR' THEN 1.0 ELSE 0 END)
        FROM majority WHERE group_code = ?
        """,
        [spec["term"], spec["subject"], spec["group"]],
    ).fetchone()
    votes, share = row
    if not votes:
        raise SystemExit(f"figure matched no votes: {spec}")
    return {"value": round(share, 4), "format": "percent", "basis": f"{votes} votes"}


def group_cohesion_on(con, spec):
    """How often a group's members voted with their own majority, on one subject."""
    row = con.execute(
        f"""
        WITH ballots AS (SELECT mv.vote_id, mv.group_code, mv.member_id, mv.position {_SCOPE}),
             tally AS (SELECT vote_id, group_code, position, count(*) n FROM ballots GROUP BY 1,2,3),
             majority AS (SELECT vote_id, group_code, arg_max(position, n) AS pos FROM tally GROUP BY 1,2)
        SELECT count(*), avg(CASE WHEN b.position = m.pos THEN 1.0 ELSE 0 END)
        FROM ballots b JOIN majority m USING (vote_id, group_code)
        WHERE b.group_code = ?
        """,
        [spec["term"], spec["subject"], spec["group"]],
    ).fetchone()
    ballots, share = row
    if not ballots:
        raise SystemExit(f"figure matched no ballots: {spec}")
    return {"value": round(share, 4), "format": "percent", "basis": f"{ballots:,} ballots"}


def vote_count(con, spec):
    """How many votes a subject covers."""
    count = con.execute(
        f"""
        WITH ballots AS (SELECT DISTINCT mv.vote_id {_SCOPE})
        SELECT count(*) FROM ballots
        """,
        [spec["term"], spec["subject"]],
    ).fetchone()[0]
    return {"value": count, "format": "count", "basis": "verified votes"}


def vote_field(con, spec):
    """A field from one specific vote, so a story can quote a real result."""
    allowed = {"count_for", "count_against", "count_abstention", "display_title", "result"}
    field = spec["field"]
    if field not in allowed:
        raise SystemExit(f"figure field not allowed: {field}")
    row = con.execute(
        f"SELECT {field}, strftime(timestamp, '%Y-%m-%d') FROM votes WHERE id = ?",
        [spec["id"]],
    ).fetchone()
    if row is None:
        raise SystemExit(f"figure references an unknown vote: {spec['id']}")
    return {"value": row[0], "format": "raw", "basis": f"vote {spec['id']} of {row[1]}"}


RESOLVERS = {
    "group_support": group_support,
    "group_cohesion_on": group_cohesion_on,
    "vote_count": vote_count,
    "vote_field": vote_field,
}


def parse(path: Path) -> dict:
    """Front matter is `key: <json>` lines, so no YAML dependency is needed and nested
    figure specifications stay unambiguous."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise SystemExit(f"{path.name}: missing front matter")
    head, body = match.groups()

    meta = {}
    lines = [l for l in head.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    index = 0
    while index < len(lines):
        key, _, raw = lines[index].partition(":")
        raw, index = raw.strip(), index + 1
        # A structured value (figures, about) spans as many lines as it needs, so keep
        # consuming until it parses rather than demanding it fit on one.
        while raw[:1] in "{[" :
            try:
                json.loads(raw)
                break
            except json.JSONDecodeError:
                if index >= len(lines):
                    raise SystemExit(f"{path.name}: unterminated value for {key.strip()}")
                raw += " " + lines[index].strip()
                index += 1
        try:
            meta[key.strip()] = json.loads(raw)
        except json.JSONDecodeError:
            meta[key.strip()] = raw.strip('"')
    meta["slug"] = path.stem
    meta["body"] = body.strip()
    return meta


def collect(data_dir: Path, source: Path) -> list[dict]:
    if not source.exists():
        return []
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"), read_only=True)
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")

    stories = []
    for path in sorted(source.glob("*.md")):
        story = parse(path)
        for field in ("title", "author", "date"):
            if field not in story:
                raise SystemExit(f"{path.name}: front matter needs a {field}")

        figures = {}
        for name, spec in (story.get("figures") or {}).items():
            resolver = RESOLVERS.get(spec.get("kind"))
            if resolver is None:
                raise SystemExit(f"{path.name}: unknown figure kind {spec.get('kind')!r}")
            figures[name] = {**resolver(con, spec), "spec": spec}

        # A story that cites a figure it never declared would render a raw token to a
        # reader; fail the build instead.
        missing = {n for n in FIGURE.findall(story["body"])} - set(figures)
        if missing:
            raise SystemExit(f"{path.name}: undeclared figures cited: {sorted(missing)}")

        story["figures"] = figures
        stories.append(story)
        print(f"    {path.name}: {len(figures)} generated figures")

    con.close()
    return stories
