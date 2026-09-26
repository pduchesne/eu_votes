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
    """Stream RollCallVote.Result elements, releasing each once handled.

    Clearing the element alone is not enough: the root keeps a reference to every child
    it has seen, so a large document stays resident in full. Detaching handled siblings
    from the root is what actually bounds memory here.
    """
    root = None
    for event, element in ET.iterparse(path, events=("start", "end")):
        if root is None:
            root = element
            continue
        if event == "end" and _tag(element) == "RollCallVote.Result":
            yield element
            # Clearing the root releases every sibling parsed so far — the corrections
            # and glossary blocks in these documents are far larger than the results.
            root.clear()


def _pers_id(member) -> str | None:
    """Parliament occasionally records `PersId="UNKNOWN"` for a member it could not
    identify. That is not an id, so it is treated as absent rather than parsed."""
    pers = member.attrib.get("PersId")
    return pers if pers and pers.isdigit() else None


# `PersId` only appears in documents from 2023 onwards, so only those can teach the
# bridge. Reading the whole archive to discover that wasted a full pass over 1.7GB.
BRIDGE_FROM = "2023-01-01"
BRIDGE_CACHE = "id_bridge.json"


def learn_bridge(paths: list[Path]) -> dict[str, str]:
    """MepId -> PersId, learned from the documents that carry both.

    Cached beside the archive: it only changes when the archive does, and recomputing
    it meant a second full pass over every document on every run.
    """
    archive = paths[0].parent if paths else Path(".")
    cache = archive / BRIDGE_CACHE
    teachers = sorted(p for p in paths if p.stem.split("-", 2)[2][:10] >= BRIDGE_FROM)
    if not teachers:
        raise SystemExit(
            "no documents carry PersId — the bridge cannot be taught from this set"
        )
    fingerprint = {"documents": len(teachers), "newest": teachers[-1].name}

    if cache.exists():
        stored = json.loads(cache.read_text())
        if stored.get("fingerprint") == fingerprint:
            return stored["bridge"]

    bridge = {}
    for path in teachers:
        for result in _iter_results(path):
            for section in result:
                if _tag(section) in POSITIONS:
                    for group in section:
                        for member in group:
                            pers = _pers_id(member)
                            if pers:
                                bridge[member.attrib["MepId"]] = pers
    cache.write_text(json.dumps({"fingerprint": fingerprint, "bridge": bridge}) + "\n")
    return bridge


def _parse(path: Path, bridge: dict[str, str], mapping: dict | None = None):
    """Returns (votes, unjoinable). Some results carry no `Identifier` attribute at
    all, so there is nothing to join them to; they are counted, not guessed at."""
    votes, unjoinable = [], 0
    sitting = path.stem.split("-", 2)[2].replace("-RCV_EN", "") if mapping else None
    for index, result in enumerate(_iter_results(path)):
        ballots, declared = {}, {}
        for section in result:
            position = POSITIONS.get(_tag(section))
            if position is None:
                continue
            raw = section.attrib.get("Number", "")
            declared[position] = int(raw) if raw.isdigit() else None
            ids, unresolved = set(), 0
            for group in section:
                for member in group:
                    pers = _pers_id(member) or bridge.get(member.attrib.get("MepId", ""))
                    if pers is None:
                        unresolved += 1
                    else:
                        ids.add(int(pers))
            ballots[position] = (ids, unresolved)

        # Prefer the reconciled mapping: a third of Parliament's term-8 results carry
        # no identifier, and were bound to our votes by sitting, tally and ballots.
        vote_id = (mapping or {}).get((sitting, index))
        if vote_id is None:
            identifier = result.attrib.get("Identifier", "")
            if not identifier.lstrip("-").isdigit():
                unjoinable += 1
                continue
            vote_id = int(identifier)
        votes.append((vote_id, declared, ballots))
    return votes, unjoinable


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


def verify(data_dir: Path, term: int | None = None, offset: int = 0, limit: int | None = None) -> int:
    """Verify the whole archive, or one term at a time.

    Reading 577 documents in a single pass is enough I/O to trip a memory watchdog on a
    modest machine, so the work is divisible by term; results accumulate per vote.
    """
    archive = data_dir / "ep_record"
    files = sorted(archive.glob(f"PV-{term}-*.xml" if term else "*.xml"))
    batched = offset or limit
    if batched:
        files = files[offset : offset + limit if limit else None]
    if not files:
        raise SystemExit("no archived EP record — run `archive` first")

    # Always taught from the whole archive, never from the filtered subset: a
    # term-filtered run contains no documents that carry PersId at all, and would
    # otherwise cache an empty bridge over a good one.
    print("  loading MepId->PersId bridge (from documents that carry both)")
    bridge = learn_bridge(sorted(archive.glob("*.xml")))
    print(f"    {len(bridge):,} identifier pairs learned")

    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")
    con.execute("CREATE INDEX IF NOT EXISTS idx_member_votes_vote ON member_votes(vote_id)")

    # Ballots our own ingest already declared unattributable. A shortfall of exactly
    # that size is a known gap, not a disagreement with Parliament.
    try:
        known_gap = dict(con.execute("SELECT vote_id, ballots FROM term8_unattributed").fetchall())
    except Exception:
        known_gap = {}

    try:
        mapping = {
            (sitting.isoformat(), index): vote_id
            for vote_id, sitting, index in con.execute(
                "SELECT vote_id, sitting, result_index FROM vote_ep_match"
            ).fetchall()
        }
        print(f"    using {len(mapping):,} reconciled vote matches")
    except Exception:
        mapping = {}

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS vote_verification (
            vote_id BIGINT, verified BOOLEAN, partial BOOLEAN,
            ballots_compared BIGINT, ballots_unverifiable BIGINT, note VARCHAR
        )
        """
    )
    # A batch replaces only the votes it actually re-checks, so runs can be resumed
    # or sliced without losing what earlier batches established.
    if batched:
        pass
    elif term:
        con.execute(
            """DELETE FROM vote_verification WHERE vote_id IN
               (SELECT id FROM votes WHERE term = ?)""",
            [term],
        )
    else:
        con.execute("DELETE FROM vote_verification")

    results, discrepancies, anomalies, explained = [], 0, 0, 0
    for n, path in enumerate(files, 1):
        parsed, unjoinable = _parse(path, bridge, mapping)
        anomalies += unjoinable
        ours = _store_ballots(con, [vote_id for vote_id, _, _ in parsed])

        for vote_id, declared, ballots in parsed:
            stored = ours.get(vote_id)
            if stored is None:
                results.append((vote_id, False, False, 0, 0, "vote absent from store"))
                discrepancies += 1
                continue

            compared, unresolved_total, problems, notes = 0, 0, [], []
            allowance = known_gap.get(vote_id, 0)
            shortfall = surplus = 0

            for position, (ep_ballots, unresolved) in ballots.items():
                if declared[position] is None:
                    anomalies += 1
                    notes.append(f"{position}: EP count unreadable")
                    continue
                mine = stored.get(position, set())
                unresolved_total += unresolved
                compared += len(ep_ballots)

                # Members Parliament lists but we cannot name are charged to neither
                # side; what we hold beyond the ones we could name should be exactly
                # that unresolvable remainder.
                missing = ep_ballots - mine
                extra = len(mine - ep_ballots)
                shortfall += len(missing) + max(0, unresolved - extra)
                surplus += max(0, extra - unresolved)
                if missing:
                    notes.append(f"{position}: {len(missing)} named member(s) absent from our record")

            # The verdict is per vote, not per position: a ballot our source could not
            # attribute is missing from one position only, while the allowance is
            # recorded for the vote as a whole.
            if surplus:
                problems.append(f"{surplus} ballot(s) we hold that Parliament does not list")
            elif shortfall > allowance:
                problems.append(f"{shortfall} ballot(s) short, {allowance} explained by ingest")
            elif shortfall:
                explained += 1
                notes.append(f"{shortfall} ballot(s) unattributable at ingest")

            ok = not problems
            discrepancies += 0 if ok else 1
            results.append(
                (
                    vote_id,
                    ok,
                    bool(unresolved_total),
                    compared,
                    unresolved_total,
                    "; ".join(problems + notes) or None,
                )
            )

        if n % 25 == 0 or n == len(files):
            print(f"    {n}/{len(files)} documents, {len(results):,} votes")

    con.execute(
        "DELETE FROM vote_verification WHERE vote_id IN (SELECT unnest(?))",
        [[r[0] for r in results]],
    )
    con.executemany(
        "INSERT INTO vote_verification VALUES (?, ?, ?, ?, ?, ?)", results
    )
    con.execute("DROP TABLE IF EXISTS _verification")
    con.execute("CREATE TABLE _verification (checked_at VARCHAR, script JSON, summary JSON)")
    # Counted over the whole table so a per-term run still reports the true total.

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
        "explained_source_gaps": explained,
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
    if explained:
        print(f"  {explained:,} gaps explained by ballots our source could not attribute")
    if anomalies:
        print(f"  {anomalies} defects in Parliament's own record, not counted against us")
    if discrepancies:
        print(f"  {discrepancies:,} DISCREPANCIES — these block publication")
    return discrepancies
