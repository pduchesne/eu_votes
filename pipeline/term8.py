"""Ingest the 2014-2019 (8th) term from parltrack (TK13).

The primary source for terms 9 and 10 starts in 2019, so the 8th term needs a second
ingest path. Parltrack was rejected for the current terms on freshness — its votes
dump ran months behind — but that objection does not apply to a term that ended in
2019: the record is closed and static.

Identity reconciles cleanly: parltrack's `mepid`/`UserID` is the European Parliament's
own MEP identifier, the same one our store already uses as `member_id`, so an MEP who
served in both the 8th and 9th terms is one person without any matching heuristics.

What this term does **not** carry, and must never be presented as though it did:

- **No "did not vote" records.** Parltrack lists only MEPs who voted, so participation
  cannot be computed for this term the way it is for 9 and 10.
- **No `is_main` flag.** Substantive votes cannot be separated from amendments, so
  main-vote cohesion is unavailable.
- **No EuroVoc or OEIL subject tags**, so topic stories do not cover this term.

These gaps are recorded as NULLs rather than guesses, and `validate` treats term 8
accordingly.
"""

import csv
import io
import json
import zlib
from datetime import datetime
from pathlib import Path

import duckdb
import ijson
import requests
import zstandard

from .provenance import now, script_version, sha256

DUMPS = {
    "ep_meps.json.zst": "https://parltrack.org/dumps/ep_meps.json.zst",
    "ep_votes.json.zst": "https://parltrack.org/dumps/ep_votes.json.zst",
}
TERM8_START, TERM8_END = "2014-07-01", "2019-07-02"
POSITION = {"+": "FOR", "-": "AGAINST", "0": "ABSTENTION"}


def fetch_dumps(data_dir: Path) -> Path:
    out = data_dir / "raw" / "parltrack"
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, url in DUMPS.items():
        dest = out / name
        if not dest.exists():
            print(f"  fetching {name}")
            with requests.get(url, stream=True, timeout=900) as response:
                response.raise_for_status()
                with dest.open("wb") as fh:
                    for chunk in response.iter_content(1 << 20):
                        fh.write(chunk)
        else:
            print(f"  have {name}")
        files[name] = {"sha256": sha256(dest), "bytes": dest.stat().st_size}

    (out / "provenance.json").write_text(
        json.dumps(
            {
                "source": {
                    "name": "Parltrack",
                    "url": "https://parltrack.org/dumps/",
                    "used_for": "8th parliamentary term (2014-2019) only",
                    "rationale": "primary source starts in 2019; this term is closed, so the dump's lag is irrelevant",
                },
                "fetched_at": now(),
                "script": script_version(),
                "files": files,
            },
            indent=2,
        )
        + "\n"
    )
    return out


def _stream(path: Path):
    with open(path, "rb") as fh:
        reader = zstandard.ZstdDecompressor().stream_reader(fh)
        yield from ijson.items(io.TextIOWrapper(reader, encoding="utf-8"), "item")


def _in_term8(timestamp: str) -> bool:
    return TERM8_START <= timestamp[:10] < TERM8_END


def _vote_id(raw) -> int:
    """Most parltrack vote ids are integers, but some are strings like
    '2017-12-12 00:00:00-1.'. Those get a deterministic negative id so they are
    neither dropped nor able to collide with a real one."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return -(zlib.crc32(str(raw).encode()) or 1)


def load_votes(raw: Path):
    votes, ballots, synthetic, unresolved = [], [], 0, 0
    for vote in _stream(raw / "ep_votes.json.zst"):
        timestamp = str(vote.get("ts", ""))
        if not _in_term8(timestamp) or "votes" not in vote:
            continue

        vote_id = _vote_id(vote.get("voteid"))
        if vote_id < 0:
            synthetic += 1
        counts = {"FOR": 0, "AGAINST": 0, "ABSTENTION": 0}
        for symbol, block in vote["votes"].items():
            position = POSITION.get(symbol)
            if position is None or not isinstance(block, dict):
                continue
            counts[position] = int(block.get("total") or 0)
            groups = block.get("groups") or {}
            for group_code, members in groups.items():
                for member in members:
                    mep_id = member.get("mepid")
                    if isinstance(mep_id, int):
                        ballots.append((vote_id, mep_id, position, group_code))
                    else:
                        # Parltrack could not resolve this MEP to an identity and
                        # recorded an `obscure_id` placeholder instead (an ambiguous
                        # surname). The ballot is real but unattributable, so it is
                        # counted and reported rather than silently dropped.
                        unresolved += 1

        refs = vote.get("epref") or []
        votes.append(
            (
                vote_id,
                datetime.fromisoformat(timestamp),
                vote.get("title"),
                refs[0] if refs else None,
                counts["FOR"],
                counts["AGAINST"],
                counts["ABSTENTION"],
            )
        )
    if synthetic:
        print(f"    {synthetic} votes had non-numeric parltrack ids; given deterministic synthetic ids")
    if unresolved:
        print(
            f"    {unresolved:,} ballots name an MEP parltrack could not resolve"
            f" ({unresolved / (len(ballots) + unresolved):.2%}); excluded, not attributable"
        )
    return votes, ballots


def load_meps(raw: Path, needed: set[int]):
    members, memberships = [], []
    for mep in _stream(raw / "ep_meps.json.zst"):
        mep_id = int(mep["UserID"])
        if mep_id not in needed:
            continue
        name = mep.get("Name") or {}
        constituencies = mep.get("Constituencies") or []
        country = next(
            (c.get("country") for c in constituencies if isinstance(c, dict) and c.get("country")),
            None,
        )
        members.append((mep_id, name.get("sur"), name.get("family"), country))
        for group in mep.get("Groups") or []:
            if not isinstance(group, dict) or not group.get("groupid"):
                continue
            group_id = group["groupid"]
            code = group_id[0] if isinstance(group_id, list) else group_id
            start, end = str(group.get("start", ""))[:10], str(group.get("end", ""))[:10]
            if end and end >= TERM8_START and start < TERM8_END:
                memberships.append((mep_id, code, 8, start or None, end or None))
    return members, memberships


def ingest(data_dir: Path) -> None:
    raw = fetch_dumps(data_dir)
    print("  parsing votes (streaming a ~500MB decompressed dump)")
    votes, ballots = load_votes(raw)
    print(f"    {len(votes):,} votes, {len(ballots):,} ballots in the 8th term")

    needed = {mep_id for _, mep_id, _, _ in ballots}
    members, memberships = load_meps(raw, needed)
    print(f"    {len(members):,} MEPs, {len(memberships):,} group spells")

    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")
    con.execute("DELETE FROM member_votes WHERE vote_id IN (SELECT id FROM votes WHERE term = 8)")
    con.execute("DELETE FROM votes WHERE term = 8")
    con.execute("DELETE FROM group_memberships WHERE term = 8")
    con.execute(
        "INSERT INTO terms SELECT 8, ?, ? WHERE NOT EXISTS (SELECT 1 FROM terms WHERE term = 8)",
        [TERM8_START, "2019-07-01"],
    )

    staging = data_dir / "tmp"
    staging.mkdir(parents=True, exist_ok=True)

    def bulk(name: str, columns: list[str], rows) -> str:
        """Row-at-a-time inserts take tens of minutes at this volume; staging a CSV and
        letting DuckDB read it takes seconds."""
        path = staging / f"t8_{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            writer.writerows(rows)
        return f"read_csv('{path}', header=true, auto_detect=true)"

    votes_csv = bulk(
        "votes",
        ["id", "timestamp", "display_title", "procedure_reference",
         "count_for", "count_against", "count_abstention"],
        votes,
    )
    con.execute(
        f"""INSERT INTO votes (id, timestamp, display_title, procedure_reference,
                               count_for, count_against, count_abstention, term)
            SELECT id, timestamp, display_title, procedure_reference,
                   count_for, count_against, count_abstention, 8 FROM {votes_csv}"""
    )

    ballots_csv = bulk("ballots", ["vote_id", "member_id", "position", "group_code"], ballots)
    con.execute(
        f"""INSERT INTO member_votes (vote_id, member_id, position, group_code)
            SELECT vote_id, member_id, position, group_code FROM {ballots_csv}"""
    )

    members_csv = bulk("members", ["id", "first_name", "last_name", "country_code"], members)
    con.execute(
        f"""INSERT INTO members (id, first_name, last_name, country_code)
            SELECT s.id, s.first_name, s.last_name, s.country_code FROM {members_csv} s
            WHERE NOT EXISTS (SELECT 1 FROM members m WHERE m.id = s.id)"""
    )

    memberships_csv = bulk(
        "memberships", ["member_id", "group_code", "term", "start_date", "end_date"], memberships
    )
    con.execute(
        f"""INSERT INTO group_memberships (member_id, group_code, term, start_date, end_date)
            SELECT member_id, group_code, term, start_date, end_date FROM {memberships_csv}"""
    )

    # Group codes of the 8th term (ALDE, EFDD, ENF...) are not all in the current
    # lookup; add the missing ones so nothing silently drops out of published output.
    con.execute(
        """
        INSERT INTO groups (code, official_label, label, short_label)
        SELECT DISTINCT mv.group_code, mv.group_code, mv.group_code, mv.group_code
        FROM member_votes mv
        WHERE mv.group_code IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM groups g WHERE g.code = mv.group_code)
        """
    )
    totals = con.execute(
        "SELECT term, count(*) FROM votes GROUP BY term ORDER BY term"
    ).fetchall()
    con.close()
    print("  votes per term now: " + ", ".join(f"T{t}={n:,}" for t, n in totals))
