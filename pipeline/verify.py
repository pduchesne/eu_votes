"""Verify every ballot against Parliament's archived roll-call record (TK10, FR02).

Supersedes the sampling spot-check that closed TK06. Sampling catches systematic
mis-parsing well and sparse errors poorly, so under FR02 the whole corpus is compared,
and a vote that cannot be verified is marked rather than quietly presented as if it
were.

Two joins, both established by inspection rather than assumption: the XML's
`Identifier` equals our `vote_id`, and its `PersId` equals our `member_id`.

Pre-2023 documents carry no `PersId`, only an internal `MepId` that matches nothing in
our store. Those are bridged from MepId/PersId pairs seen in later documents. The
bridge cannot reach MEPs who left before the schema changed, so their ballots are
counted as unverifiable and reported as a number rather than glossed over.

The XML lists only For/Against/Abstention. `DID_NOT_VOTE` is absent from the primary
record entirely — our source derives it from the sitting roster — so it is outside
what this can verify. `Intentions` are post-hoc corrections that do not count.
"""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

from .provenance import now, script_version

POSITIONS = {"Result.For": "FOR", "Result.Against": "AGAINST", "Result.Abstention": "ABSTENTION"}


def _tag(el) -> str:
    return el.tag.split("}")[-1]


def _iter_results(path: Path):
    """Stream RollCallVote.Result elements, discarding each once handled."""
    for _, element in ET.iterparse(path, events=("end",)):
        if _tag(element) == "RollCallVote.Result":
            yield element
            element.clear()


def learn_bridge(paths: list[Path]) -> dict[str, str]:
    bridge = {}
    for path in paths:
        for result in _iter_results(path):
            for section in result:
                if _tag(section) in POSITIONS:
                    for group in section:
                        for member in group:
                            pers = member.attrib.get("PersId")
                            if pers:
                                bridge[member.attrib["MepId"]] = pers
    return bridge


def _parse(path: Path, bridge: dict[str, str]):
    for result in _iter_results(path):
        ballots, declared, unbridged = {}, {}, 0
        for section in result:
            position = POSITIONS.get(_tag(section))
            if position is None:
                continue
            raw = section.attrib.get("Number", "")
            declared[position] = int(raw) if raw.isdigit() else None
            ids = set()
            for group in section:
                for member in group:
                    pers = member.attrib.get("PersId") or bridge.get(member.attrib["MepId"])
                    if pers is None:
                        unbridged += 1
                    else:
                        ids.add(int(pers))
            ballots[position] = ids
        yield int(result.attrib["Identifier"]), declared, ballots, unbridged


def _store_ballots(con, vote_ids: list[int]) -> dict:
    rows = con.execute(
        """
        SELECT vote_id, position, member_id FROM member_votes
        WHERE vote_id IN (SELECT unnest(?)) AND position <> 'DID_NOT_VOTE'
        """,
        [vote_ids],
    ).fetchall()
    out: dict = {}
    for vote_id, position, member_id in rows:
        out.setdefault(vote_id, {}).setdefault(position, set()).add(member_id)
    return out


def verify(data_dir: Path) -> int:
    archive = data_dir / "ep_record"
    files = sorted(archive.glob("*.xml"))
    if not files:
        raise SystemExit("no archived EP record — run `archive` first")

    print(f"  learning MepId->PersId bridge from {len(files)} documents")
    bridge = learn_bridge(files)
    universe = {int(v) for v in bridge.values()}
    print(f"    {len(bridge):,} identifier pairs learned")

    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")
    con.execute("DROP TABLE IF EXISTS vote_verification")
    con.execute(
        """
        CREATE TABLE vote_verification (
            vote_id BIGINT, verified BOOLEAN, partial BOOLEAN,
            ballots_compared BIGINT, ballots_unverifiable BIGINT, note VARCHAR
        )
        """
    )

    results, discrepancies, anomalies = [], 0, 0
    for n, path in enumerate(files, 1):
        parsed = list(_parse(path, bridge))
        ours = _store_ballots(con, [vote_id for vote_id, _, _, _ in parsed])

        for vote_id, declared, ballots, unbridged in parsed:
            stored = ours.get(vote_id)
            if stored is None:
                results.append((vote_id, False, False, 0, 0, "vote absent from store"))
                discrepancies += 1
                continue

            compared, problems, notes = 0, [], []
            for position, ep_ballots in ballots.items():
                if declared[position] is None:
                    anomalies += 1
                    notes.append(f"{position}: EP count unreadable")
                    continue
                mine = stored.get(position, set())
                if unbridged:
                    mine = mine & universe
                if mine != ep_ballots:
                    problems.append(
                        f"{position}: +{len(mine - ep_ballots)}/-{len(ep_ballots - mine)}"
                    )
                compared += len(ep_ballots)

            ok = not problems
            discrepancies += 0 if ok else 1
            results.append(
                (
                    vote_id,
                    ok,
                    bool(unbridged),
                    compared,
                    unbridged,
                    "; ".join(problems + notes) or None,
                )
            )

        if n % 25 == 0 or n == len(files):
            print(f"    {n}/{len(files)} documents, {len(results):,} votes")

    con.executemany(
        "INSERT INTO vote_verification VALUES (?, ?, ?, ?, ?, ?)", results
    )
    con.execute("DROP TABLE IF EXISTS _verification")
    con.execute("CREATE TABLE _verification (checked_at VARCHAR, script JSON, summary JSON)")

    total_votes = con.execute("SELECT count(*) FROM votes").fetchone()[0]
    covered, verified, partial, unverifiable = con.execute(
        """
        SELECT count(*), sum(verified::INT), sum(partial::INT), sum(ballots_unverifiable)
        FROM vote_verification
        """
    ).fetchone()
    summary = {
        "votes_in_store": total_votes,
        "votes_checked": covered,
        "votes_verified": int(verified or 0),
        "votes_partially_covered": int(partial or 0),
        "ballots_unverifiable": int(unverifiable or 0),
        "discrepancies": discrepancies,
        "ep_record_anomalies": anomalies,
    }
    con.execute(
        "INSERT INTO _verification VALUES (?, ?, ?)",
        [now(), json.dumps(script_version()), json.dumps(summary)],
    )
    con.close()

    print(
        f"\n  {summary['votes_verified']:,}/{total_votes:,} votes verified against"
        f" Parliament's record ({summary['votes_verified'] / total_votes:.1%})"
    )
    if summary["votes_partially_covered"]:
        print(
            f"  {summary['votes_partially_covered']:,} votes only partially comparable"
            f" ({summary['ballots_unverifiable']:,} ballots unbridgeable to a known MEP)"
        )
    if anomalies:
        print(f"  {anomalies} defects in Parliament's own record, not counted against us")
    if discrepancies:
        print(f"  {discrepancies:,} DISCREPANCIES — these block publication")
    return discrepancies
