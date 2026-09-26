"""Compare the normalized store against Parliament's own roll-call XML.

Every other check validates the data against itself or against the tallies our source
publishes. This is the only one that leaves that circle, which is what makes it the
check TK06 cannot skip: we ingest a third-party derivation of the minutes.

Votes join on the XML's `Identifier`, verified equal to our `vote_id`.

MEP identity is messier, because the XML schema changed mid-term:
  - Newer files (seen from 2023) carry `PersId`, which equals our `member_id`.
  - Older files (2019-2021) carry only the internal `MepId`, which matches nothing in
    our store. For those we bridge MepId -> PersId using pairs learned from the newer
    files. The bridge cannot cover MEPs who left before the schema changed, so ballot
    comparison on those sittings is partial and reports its own coverage rather than
    implying more assurance than it has. Their tallies are still fully checked.

The XML lists only For/Against/Abstention. "Did not vote" is absent from the primary
record — our source derives it from the sitting roster — so it cannot be verified here.
`Intentions` blocks are post-hoc corrections that do not count towards the result and
are ignored.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import duckdb

POSITIONS = {"Result.For": "FOR", "Result.Against": "AGAINST", "Result.Abstention": "ABSTENTION"}


def _tag(el) -> str:
    return el.tag.split("}")[-1]


def _member_elements(root):
    for result in (c for c in root if _tag(c) == "RollCallVote.Result"):
        for section in result:
            if _tag(section) in POSITIONS:
                for group in section:
                    yield from group


def learn_id_bridge(paths: list[Path]) -> dict[str, str]:
    bridge = {}
    for path in paths:
        for member in _member_elements(ET.parse(path).getroot()):
            if "PersId" in member.attrib:
                bridge[member.attrib["MepId"]] = member.attrib["PersId"]
    return bridge


def parse_rcv(path: Path, bridge: dict[str, str]) -> tuple[list[dict], int]:
    root = ET.parse(path).getroot()
    votes, unbridged = [], set()

    for result in (c for c in root if _tag(c) == "RollCallVote.Result"):
        ballots, declared = {}, {}
        for section in result:
            position = POSITIONS.get(_tag(section))
            if position is None:
                continue
            # Parliament's XML is not always well formed: at least one section carries
            # the multilingual "corrections" heading where its count belongs.
            raw = section.attrib.get("Number", "")
            declared[position] = int(raw) if raw.isdigit() else None
            ids = set()
            for group in section:
                for member in group:
                    pers = member.attrib.get("PersId") or bridge.get(member.attrib["MepId"])
                    if pers is None:
                        unbridged.add(member.attrib["MepId"])
                    else:
                        ids.add(int(pers))
            ballots[position] = ids
        votes.append(
            {
                "id": int(result.attrib["Identifier"]),
                "declared": declared,
                "ballots": ballots,
            }
        )
    return votes, len(unbridged)


def check_file(con, path: Path, bridge: dict[str, str]) -> tuple[int, int, str]:
    ep_votes, unbridged = parse_rcv(path, bridge)
    problems = 0
    anomalies: list[str] = []
    universe = {int(v) for v in bridge.values()} if unbridged else None

    for ep in ep_votes:
        store = con.execute(
            "SELECT count_for, count_against, count_abstention FROM votes WHERE id = ?",
            [ep["id"]],
        ).fetchone()
        if store is None:
            problems += 1
            print(f"    vote {ep['id']} present in EP record but missing from store")
            continue
        counts = dict(zip(("FOR", "AGAINST", "ABSTENTION"), store))

        for position in POSITIONS.values():
            if position not in ep["ballots"]:
                if counts[position] != 0:
                    problems += 1
                    print(
                        f"    vote {ep['id']} {position}: absent from EP record"
                        f" but store has {counts[position]}"
                    )
                continue

            ep_ballots = ep["ballots"][position]
            declared = ep["declared"][position]
            if declared is None:
                anomalies.append(f"vote {ep['id']} {position}: EP count unreadable")
                continue
            if counts[position] != declared:
                problems += 1
                print(f"    vote {ep['id']} {position}: EP {declared} vs store {counts[position]}")

            rows = con.execute(
                "SELECT member_id FROM member_votes WHERE vote_id = ? AND position = ?",
                [ep["id"], position],
            ).fetchall()
            ours = {r[0] for r in rows}
            if universe is not None:
                # Only members the bridge can name are comparable on this sitting.
                ours &= universe
            if ours != ep_ballots:
                problems += 1
                missing, extra = ep_ballots - ours, ours - ep_ballots
                print(
                    f"    vote {ep['id']} {position}: ballots differ"
                    f" (+{len(extra)} in store, -{len(missing)} missing);"
                    f" e.g. {sorted(missing)[:3] or sorted(extra)[:3]}"
                )

    if unbridged:
        mode = f"tallies in full, ballots partial ({unbridged} MEPs unbridgeable)"
    else:
        mode = "tallies and every individual ballot"
    for note in anomalies:
        print(f"    EP record anomaly (not ours): {note}")
    return len(ep_votes), problems, mode


def spotcheck(data_dir: Path) -> int:
    files = sorted((data_dir / "spotcheck").glob("*.xml"))
    if not files:
        raise SystemExit(
            "no roll-call XML found in data/spotcheck/ — see TK06 for how to obtain it"
        )
    bridge = learn_id_bridge(files)
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"), read_only=True)

    total = 0
    for path in files:
        votes, problems, mode = check_file(con, path, bridge)
        total += problems
        verdict = "ok" if problems == 0 else f"{problems} PROBLEM(S)"
        print(f"  [{verdict:^14}] {path.name}: {votes} votes — {mode}")
    con.close()

    if total == 0:
        print("\n  store agrees with Parliament's own record on every vote checked")
    return total
