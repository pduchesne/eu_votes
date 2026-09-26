"""Fill in what each vote was about, for the term that has nothing (TK18, FR04).

Terms 9 and 10 arrive with a `procedure_title` — the actual subject matter, as opposed
to the ballot's own formulaic title ("A8-0175/2015 - Bernd Lange - Am 77"). The 8th term
has none: no procedure titles, no descriptions, and no subject tags whatsoever. There is
simply nothing in it to derive a topic from.

Parltrack's dossier dump closes both gaps from a source already in use. Every one of the
8th term's 2,149 procedure references resolves to a title, and most carry Parliament's
own Legislative Observatory subject codes — the same taxonomy the later terms use, so
the tags are comparable rather than merely similar.

This is what makes topic work possible across all three terms rather than only the two
that came pre-labelled.
"""

import csv
import io
from pathlib import Path

import duckdb
import ijson
import zstandard

from .provenance import now, script_version, sha256

DUMP = "ep_dossiers.json.zst"
URL = f"https://parltrack.org/dumps/{DUMP}"


def fetch(data_dir: Path) -> Path:
    import requests

    out = data_dir / "raw" / "parltrack"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / DUMP
    if dest.exists():
        print(f"  have {DUMP}")
    else:
        print(f"  fetching {DUMP}")
        with requests.get(URL, stream=True, timeout=900) as response:
            response.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in response.iter_content(1 << 20):
                    fh.write(chunk)
    return dest


def read(path: Path, wanted: set[str]):
    """Titles and subject codes for the procedure references we actually hold."""
    titles, subjects = {}, []
    with open(path, "rb") as fh:
        text = io.TextIOWrapper(
            zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8"
        )
        for dossier in ijson.items(text, "item"):
            procedure = dossier.get("procedure") or {}
            reference = procedure.get("reference")
            if reference not in wanted:
                continue
            if procedure.get("title"):
                titles[reference] = procedure["title"]
            for code, label in (procedure.get("subject") or {}).items():
                subjects.append((reference, code, label))
    return titles, subjects


def ingest(data_dir: Path) -> None:
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")
    con.execute("SET memory_limit='3GB'")

    wanted = {
        r[0]
        for r in con.execute(
            """SELECT DISTINCT procedure_reference FROM votes
               WHERE procedure_reference IS NOT NULL
                 AND (procedure_title IS NULL OR procedure_title = '')"""
        ).fetchall()
    }
    if not wanted:
        print("  every vote already has a procedure title")
        con.close()
        return
    print(f"  {len(wanted):,} procedure references lack a title")

    path = fetch(data_dir)
    titles, subjects = read(path, wanted)
    print(f"    resolved {len(titles):,} titles ({len(titles)/len(wanted):.0%})"
          f" and {len(subjects):,} subject assignments")

    staging = data_dir / "tmp"
    staging.mkdir(parents=True, exist_ok=True)

    title_csv = staging / "dossier_titles.csv"
    with title_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["reference", "title"])
        writer.writerows(sorted(titles.items()))
    con.execute(
        f"""UPDATE votes SET procedure_title = s.title
            FROM read_csv('{title_csv}', header=true, auto_detect=true) s
            WHERE votes.procedure_reference = s.reference
              AND (votes.procedure_title IS NULL OR votes.procedure_title = '')"""
    )

    # Subject tags are attached per vote, matching how the later terms carry them, so
    # everything downstream treats all three terms the same way.
    subject_csv = staging / "dossier_subjects.csv"
    with subject_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["reference", "code", "label"])
        writer.writerows(subjects)
    con.execute(
        f"""CREATE OR REPLACE TEMP TABLE incoming AS
            SELECT * FROM read_csv('{subject_csv}', header=true, auto_detect=true)"""
    )
    con.execute(
        """INSERT INTO oeil_subjects (code, label)
           SELECT DISTINCT i.code, i.label FROM incoming i
           WHERE NOT EXISTS (SELECT 1 FROM oeil_subjects o WHERE o.code = i.code)"""
    )
    con.execute(
        """INSERT INTO oeil_subject_votes (vote_id, oeil_subject_code)
           SELECT DISTINCT v.id, i.code
           FROM votes v JOIN incoming i ON i.reference = v.procedure_reference
           WHERE NOT EXISTS (
               SELECT 1 FROM oeil_subject_votes sv
               WHERE sv.vote_id = v.id AND sv.oeil_subject_code = i.code)"""
    )

    con.execute("DROP TABLE IF EXISTS _dossiers")
    con.execute("CREATE TABLE _dossiers (ingested_at VARCHAR, script JSON, source JSON)")
    con.execute(
        "INSERT INTO _dossiers VALUES (?, ?, ?)",
        [
            now(),
            __import__("json").dumps(script_version()),
            __import__("json").dumps(
                {
                    "name": "Parltrack dossier dump",
                    "url": URL,
                    "sha256": sha256(path),
                    "used_for": "procedure titles and Legislative Observatory subjects",
                }
            ),
        ],
    )

    coverage = con.execute(
        """SELECT v.term, count(DISTINCT v.id) AS votes,
                  count(DISTINCT CASE WHEN v.procedure_title IS NOT NULL THEN v.id END) AS titled,
                  count(DISTINCT sv.vote_id) AS tagged
           FROM votes v LEFT JOIN oeil_subject_votes sv ON sv.vote_id = v.id
           GROUP BY 1 ORDER BY 1"""
    ).fetchall()
    con.close()
    for term, votes, titled, tagged in coverage:
        print(f"    T{term}: {titled:,}/{votes:,} titled, {tagged:,} subject-tagged")
