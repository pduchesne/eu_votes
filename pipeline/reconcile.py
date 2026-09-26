"""Match 8th-term votes to Parliament's record where identifiers cannot (TK14, FR03).

Roughly a third of Parliament's own term-8 roll-call results carry no `Identifier`
attribute at all. The source dump has no identifier for those same votes either, and
synthesises a date-based placeholder — so an identifier join can never reach them, and
half the term goes unverified and therefore unpublished under FR02.

They are matched instead on what both sides do record: the sitting, the tally, and
where that collides, the individual ballots. Anything still ambiguous stays unmatched.
Recovering coverage must not come at the cost of binding the wrong vote — a mis-join
would corrupt exactly the figures this project exists to make trustworthy.

Votes of ours with no counterpart at all are duplicates: sittings the dump records both
with and without times. They are flagged, not deleted, so the evidence survives.
"""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

import duckdb

from .verify import POSITIONS, _iter_results, _pers_id, _tag, learn_bridge

TERM = 8


def _normalise(text: str | None) -> str:
    """Strip everything but alphanumerics so punctuation and spacing cannot differ."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _ep_results(path: Path, bridge: dict[str, str]):
    """Every roll-call result in a document, in order, with tallies and ballots."""
    out = []
    for index, result in enumerate(_iter_results(path)):
        tallies, ballots = {}, {}
        for section in result:
            position = POSITIONS.get(section.tag.split("}")[-1])
            if position is None:
                continue
            raw = section.attrib.get("Number", "")
            tallies[position] = int(raw) if raw.isdigit() else None
            ids = set()
            for group in section:
                for member in group:
                    pers = _pers_id(member) or bridge.get(member.attrib.get("MepId", ""))
                    if pers:
                        ids.add(int(pers))
            ballots[position] = ids
        # The description carries the vote's own reference ("RC-B8-1344/2016 - Am 1").
        # Checked against 498 identifier-matched votes it agreed every time, which makes
        # it a stronger discriminator than either tallies or ballots.
        description = next(
            (c for c in result if _tag(c) == "RollCallVote.Description.Text"), None
        )
        identifier = result.attrib.get("Identifier", "")
        out.append(
            {
                "index": index,
                "id": int(identifier) if identifier.lstrip("-").isdigit() else None,
                "title": _normalise("".join(description.itertext())) if description is not None else "",
                "signature": (
                    tallies.get("FOR"),
                    tallies.get("AGAINST"),
                    tallies.get("ABSTENTION"),
                ),
                "ballots": ballots,
            }
        )
    return out


def _our_ballots(con, vote_ids: list[int]) -> dict:
    rows = con.execute(
        """SELECT vote_id, position, member_id FROM member_votes
           WHERE vote_id IN (SELECT unnest(?)) AND position <> 'DID_NOT_VOTE'""",
        [vote_ids],
    ).fetchall()
    out: dict = {}
    for vote_id, position, member_id in rows:
        out.setdefault(vote_id, {}).setdefault(position, set()).add(member_id)
    return out


def _agreement(ours: dict, theirs: dict) -> float:
    """Share of the members Parliament names that we place in the same position.

    Scored against the names Parliament's document actually resolves to, not against
    our whole ballot: in 8th-term documents most members carry only an internal id we
    cannot map, so a ratio over our own total could never approach 1 even for a perfect
    match — which is why an earlier attempt disambiguated nothing.
    """
    named = sum(len(theirs.get(p, set())) for p in POSITIONS.values())
    if named < 20:
        return 0.0
    agree = sum(len(ours.get(p, set()) & theirs.get(p, set())) for p in POSITIONS.values())
    return agree / named


def reconcile(data_dir: Path) -> int:
    archive = data_dir / "ep_record"
    files = sorted(archive.glob(f"PV-{TERM}-*.xml"))
    if not files:
        raise SystemExit("no archived term-8 record — run `archive` first")

    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")

    ours_by_date = defaultdict(list)
    for vote_id, date, f, a, ab, title in con.execute(
        """SELECT id, strftime(timestamp, '%Y-%m-%d'), count_for, count_against,
                  count_abstention, display_title
           FROM votes WHERE term = ?""",
        [TERM],
    ).fetchall():
        ours_by_date[date].append((vote_id, (f, a, ab), _normalise(title)))

    print(f"  learning identity bridge (needed only where tallies collide)")
    bridge = learn_bridge(sorted(archive.glob("*.xml")))

    matches, duplicates = [], []
    counts = Counter()
    for n, path in enumerate(files, 1):
        date = path.stem.replace(f"PV-{TERM}-", "").replace("-RCV_EN", "")
        ep = _ep_results(path, bridge)
        mine = ours_by_date.get(date, [])

        taken, claimed = set(), set()
        for entry in ep:  # 1. identifier, where both sides have one
            if entry["id"] is not None and any(v == entry["id"] for v, _, _ in mine):
                matches.append((entry["id"], date, entry["index"], "identifier"))
                taken.add(entry["index"])
                claimed.add(entry["id"])
                counts["identifier"] += 1

        # 2. the vote's own reference, which both sides record verbatim. A sitting can
        # reuse a reference across results, so a title group with more than one
        # candidate is paired on the tally rather than in arbitrary order — binding by
        # position alone mismatched 141 votes.
        by_title = defaultdict(list)
        for entry in ep:
            if entry["index"] not in taken and entry["title"]:
                by_title[entry["title"]].append(entry)
        mine_by_title = defaultdict(list)
        for vote_id, signature, title in mine:
            if vote_id not in claimed and title:
                mine_by_title[title].append((vote_id, signature))

        for title, rows in mine_by_title.items():
            candidates = by_title.get(title, [])
            for vote_id, signature in rows:
                if not candidates:
                    break
                exact = [e for e in candidates if e["signature"] == signature]
                entry = exact[0] if len(exact) == 1 else (candidates[0] if len(candidates) == 1 else None)
                if entry is None:
                    continue
                matches.append((vote_id, date, entry["index"], "title"))
                taken.add(entry["index"])
                claimed.add(vote_id)
                candidates.remove(entry)
                counts["title"] += 1

        pool = defaultdict(list)
        for entry in ep:
            if entry["index"] not in taken:
                pool[entry["signature"]].append(entry)
        pending = defaultdict(list)
        for vote_id, signature, _ in mine:
            if vote_id not in claimed:
                pending[signature].append(vote_id)

        for signature, vote_ids in pending.items():
            candidates = pool.get(signature, [])
            if len(vote_ids) == 1 and len(candidates) == 1:  # 2. unambiguous tally
                matches.append((vote_ids[0], date, candidates[0]["index"], "tally"))
                counts["tally"] += 1
                candidates.clear()
            elif candidates:  # 3. tallies collide — decide on the ballots themselves
                mine_ballots = _our_ballots(con, vote_ids)
                for vote_id in vote_ids:
                    if not candidates:
                        counts["ambiguous"] += 1
                        continue
                    scored = sorted(
                        ((_agreement(mine_ballots.get(vote_id, {}), e["ballots"]), e) for e in candidates),
                        key=lambda pair: pair[0],
                        reverse=True,
                    )
                    best_score, best = scored[0]
                    runner_up = scored[1][0] if len(scored) > 1 else 0.0
                    # Bind only on a near-perfect match that is also clearly better
                    # than the alternative: same-tally votes differ in who voted how,
                    # and a wrong bind would attach the wrong title to a real vote.
                    # Tightened after verification caught 141 wrong binds at
                    # 0.95/0.05: a near-miss on a same-tally vote is a plausible-looking
                    # match to the wrong vote, which is worse than no match at all.
                    if best_score > 0.995 and best_score - runner_up > 0.15:
                        matches.append((vote_id, date, best["index"], "ballots"))
                        counts["ballots"] += 1
                        candidates.remove(best)
                    else:
                        counts["ambiguous"] += 1
            else:  # 4. nothing left in Parliament's record: a duplicate of ours
                for vote_id in vote_ids:
                    duplicates.append((vote_id, date))
                    counts["duplicate"] += 1
        if n % 50 == 0 or n == len(files):
            print(f"    {n}/{len(files)} sittings")

    staging = data_dir / "tmp"
    staging.mkdir(parents=True, exist_ok=True)
    for name, rows, columns in (
        ("matches", matches, ["vote_id", "sitting", "result_index", "method"]),
        ("duplicates", duplicates, ["vote_id", "sitting"]),
    ):
        path = staging / f"reconcile_{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            writer.writerows(rows)
        table = "vote_ep_match" if name == "matches" else "vote_duplicate"
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_csv('{path}', header=true, auto_detect=true)"
        )
    con.close()

    print(
        f"  matched {len(matches):,} term-8 votes"
        f" (identifier {counts['identifier']:,}, title {counts['title']:,},"
        f" tally {counts['tally']:,}, ballots {counts['ballots']:,})"
    )
    if counts["ambiguous"]:
        print(f"  {counts['ambiguous']:,} left unmatched — too ambiguous to bind safely")
    if counts["duplicate"]:
        print(f"  {counts['duplicate']:,} flagged as duplicate records of the same vote")
    return len(matches)
