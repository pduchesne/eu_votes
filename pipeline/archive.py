"""Archive Parliament's roll-call record for every sitting (TK09).

Parliament is the platform's reference of record (FR02), so we keep its roll-call XML
ourselves rather than relying on links staying live.

Retrieval needs a browser: the EP fronts these documents with an AWS WAF JavaScript
challenge, and plain HTTP clients get an empty HTTP 202 that reads exactly like the
document not existing. A real browser solves the challenge and yields an
`aws-waf-token` cookie, which plain HTTP can then reuse until it expires (minutes).
So we mint a token with headless Chromium, spend it on as many sittings as it lasts,
and mint another when it stops working.

These documents never change once published, so the archive is append-only and a
re-run fetches only what is missing.
"""

import json
from pathlib import Path

import duckdb
import requests

from .provenance import now, script_version

DOC_URL = "https://www.europarl.europa.eu/doceo/document/PV-{term}-{date}-RCV_EN.xml"
# The 8th term predates the doceo scheme and lives under a different path entirely.
DOC_URL_T8 = (
    "https://www.europarl.europa.eu/RegData/seance_pleniere/proces_verbal/"
    "{year}/{md}/liste_presence/P8_PV({year}){md}(RCV)_XC.xml"
)


def document_url(term: int, date: str) -> str:
    if term >= 9:
        return DOC_URL.format(term=term, date=date)
    year, month, day = date.split("-")
    return DOC_URL_T8.format(year=year, md=f"{month}-{day}")
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)
CHALLENGE_HEADER = "x-amzn-waf-action"
# Only /doceo/ documents trigger the WAF challenge, so the token must always be minted
# against one of those even when the document we actually want lives elsewhere
# (the 8th term's RegData path does not challenge, and yields no token).
TOKEN_PROBE = "https://www.europarl.europa.eu/doceo/document/PV-10-2026-09-17-RCV_EN.xml"


def sittings(data_dir: Path) -> list[tuple[int, str]]:
    """Sittings we must archive: exactly the dates our store has votes for."""
    con = duckdb.connect(str(data_dir / "eu_votes.duckdb"), read_only=True)
    rows = con.execute(
        """
        SELECT DISTINCT term, strftime(CAST(timestamp AS DATE), '%Y-%m-%d') AS d
        FROM votes ORDER BY d
        """
    ).fetchall()
    con.close()
    return [(int(t), d) for t, d in rows]


def mint_token(probe_url: str) -> str:
    """Solve the WAF challenge in a real browser and take the resulting token.

    Only the /doceo/ documents are challenged — the portal pages are not — so the
    probe has to be a document URL even though we discard whatever it returns.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(user_agent=UA, accept_downloads=True)
        page = context.new_page()
        try:
            page.goto(probe_url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            # The challenge interstitial, or the download that follows it, can abort
            # navigation. The cookie is what matters, not the page.
            pass

        token = None
        for _ in range(20):
            token = next(
                (c["value"] for c in context.cookies() if c["name"] == "aws-waf-token"),
                None,
            )
            if token:
                break
            page.wait_for_timeout(1000)
        browser.close()

    if not token:
        raise RuntimeError(f"no aws-waf-token after solving the challenge at {probe_url}")
    return token


def _get(session: requests.Session, url: str, token: str):
    return session.get(
        url,
        headers={"User-Agent": UA},
        cookies={"aws-waf-token": token},
        timeout=300,
    )


def archive(data_dir: Path, limit: int | None = None) -> Path:
    out = data_dir / "ep_record"
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}

    todo = [
        (term, date)
        for term, date in sittings(data_dir)
        if index.get(date, {}).get("status") not in ("archived", "absent")
    ]
    if limit:
        todo = todo[:limit]
    print(f"  {len(todo)} sittings to fetch ({len(index)} already recorded)")

    session = requests.Session()
    token = None
    fetched = missing = 0

    for i, (term, date) in enumerate(todo, 1):
        url = document_url(term, date)
        dest = out / f"PV-{term}-{date}-RCV_EN.xml"

        for attempt in range(2):
            if token is None:
                print("    minting a WAF token")
                token = mint_token(TOKEN_PROBE)
            response = _get(session, url, token)
            if response.headers.get(CHALLENGE_HEADER) or response.status_code == 202:
                token = None  # expired or rejected; mint a fresh one and retry once
                continue
            break

        if response.status_code == 404:
            # A sitting with votes but no roll-call document: record it so we neither
            # retry forever nor mistake it for a fetch failure.
            index[date] = {"status": "absent", "term": term, "checked_at": now()}
            missing += 1
        elif response.status_code == 200 and response.content.lstrip().startswith(b"<?xml"):
            dest.write_bytes(response.content)
            index[date] = {
                "status": "archived",
                "term": term,
                "url": url,
                "bytes": len(response.content),
                "retrieved_at": now(),
            }
            fetched += 1
        else:
            raise SystemExit(
                f"unexpected response for {date}: HTTP {response.status_code}"
                f" ({len(response.content)} bytes) — refusing to guess"
            )

        index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
        if i % 10 == 0 or i == len(todo):
            print(f"    {i}/{len(todo)} — {fetched} archived, {missing} absent")

    (out / "provenance.json").write_text(
        json.dumps(
            {
                "source": "European Parliament plenary minutes (roll-call XML)",
                "url_patterns": {"terms 9+": DOC_URL, "term 8": DOC_URL_T8},
                "sittings_archived": sum(
                    1 for v in index.values() if v["status"] == "archived"
                ),
                "sittings_absent": sum(1 for v in index.values() if v["status"] == "absent"),
                "script": script_version(),
                "updated_at": now(),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  archive: {fetched} new, {missing} absent, in {out}")
    return out
