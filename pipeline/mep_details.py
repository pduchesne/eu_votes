"""Enrich MEP records with the attributes the 2019 analysis carried (TK15, FR03).

The primary source for terms 9-10 gives names, country, birthdate and contact details
but no gender, photo, constituency or official page. The parltrack MEP dump has all of
them and covers every term, so it serves as the attribute source for all MEPs rather
than only for the 8th term it was introduced for.

These are the fields that make an MEP page recognisable to a citizen rather than a row
in a table (UC01), and they are limited to what Parliament itself publishes about MEPs
acting in their public role.
"""

import csv
from pathlib import Path

import duckdb

from .term8 import _stream, fetch_dumps

# Deterministic EP URLs, the same ones parltrack stores. Derived from the member id
# rather than scraped, so they are available even where the dump omits them.
PHOTO = "https://www.europarl.europa.eu/mepphoto/{id}.jpg"
PROFILE = "https://www.europarl.europa.eu/meps/en/{id}"

COLUMNS = {
    "gender": "VARCHAR",
    "constituency": "VARCHAR",
    "photo_url": "VARCHAR",
    "ep_url": "VARCHAR",
}


def _latest(entries, key: str):
    """Parltrack lists constituencies and groups as dated spells; take the newest."""
    dated = [e for e in entries or [] if isinstance(e, dict) and e.get(key)]
    if not dated:
        return None
    return max(dated, key=lambda e: str(e.get("end") or e.get("start") or ""))


def enrich(data_dir: Path) -> None:
    raw = fetch_dumps(data_dir)
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"))
    con.execute("SET enable_progress_bar=false")

    existing = {c[0] for c in con.execute("DESCRIBE members").fetchall()}
    for column, kind in COLUMNS.items():
        if column not in existing:
            con.execute(f"ALTER TABLE members ADD COLUMN {column} {kind}")

    wanted = {r[0] for r in con.execute("SELECT id FROM members").fetchall()}
    print(f"  enriching {len(wanted):,} MEPs from the parltrack dump")

    rows, seen = [], 0
    for mep in _stream(raw / "ep_meps.json.zst"):
        mep_id = int(mep["UserID"])
        if mep_id not in wanted:
            continue
        seen += 1
        constituency = _latest(mep.get("Constituencies"), "party")
        birth = (mep.get("Birth") or {}).get("date")
        rows.append(
            (
                mep_id,
                mep.get("Gender"),
                (constituency or {}).get("party"),
                mep.get("Photo") or PHOTO.format(id=mep_id),
                PROFILE.format(id=mep_id),
                str(birth)[:10] if birth else None,
                mep.get("Mail"),
            )
        )

    staging = data_dir / "tmp"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / "mep_details.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "gender", "constituency", "photo_url", "ep_url", "dob", "mail"])
        writer.writerows(rows)

    con.execute(
        f"""
        UPDATE members SET
            gender       = coalesce(s.gender, members.gender),
            constituency = coalesce(s.constituency, members.constituency),
            photo_url    = coalesce(s.photo_url, members.photo_url),
            ep_url       = coalesce(s.ep_url, members.ep_url),
            date_of_birth = coalesce(members.date_of_birth, try_cast(s.dob AS DATE)),
            email        = coalesce(members.email, s.mail)
        FROM read_csv('{path}', header=true, auto_detect=true) s
        WHERE members.id = s.id
        """
    )

    filled = con.execute(
        """
        SELECT count(gender), count(constituency), count(photo_url), count(ep_url),
               count(date_of_birth), count(email), count(*)
        FROM members
        """
    ).fetchone()
    con.close()
    labels = ["gender", "constituency", "photo", "ep_url", "birthdate", "email"]
    print(f"    matched {seen:,} MEPs in the dump")
    print("    " + ", ".join(f"{l} {filled[i]}/{filled[-1]}" for i, l in enumerate(labels)))
