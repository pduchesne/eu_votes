"""Assemble a deployable directory (TK12).

The site reads `../data/published` relative to itself, which is convenient while
developing from the repository root but not what you want to upload. This copies the
interface and the published bundles into one self-contained tree with that relative
layout preserved, so deploying is uploading a directory — no build step, no server, no
configuration.

The licence file travels with the data, because ODbL asks that it does.
"""

import hashlib
import shutil
from pathlib import Path

# Assets whose URL carries a content hash when deployed.
FINGERPRINTED = ("app.js", "styles.css")


def _fingerprint(ui: Path) -> None:
    """Stamp a content hash onto the script and stylesheet URLs.

    GitHub Pages serves everything with `max-age=600` and no fingerprinting, so after a
    deploy a visitor can hold a fresh index.html and a stale app.js — the new navigation
    appears but does nothing, because the running module has never heard of the view. A
    browser tab left open across a deploy never re-fetches at all.

    The hash goes in only when the deployable tree is assembled, so `ui/` keeps plain
    filenames and serving the repository directly still works.
    """
    index = ui / "index.html"
    html = index.read_text()
    for asset in FINGERPRINTED:
        digest = hashlib.sha256((ui / asset).read_bytes()).hexdigest()[:10]
        html = html.replace(f'"{asset}"', f'"{asset}?v={digest}"')
    index.write_text(html)


def build(data_dir: Path, out: Path = Path("site")) -> Path:
    published = data_dir / "published"
    if not published.exists():
        raise SystemExit("nothing published yet — run `publish` first")

    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)

    shutil.copytree(Path("ui"), out / "ui")
    shutil.copytree(published, out / "data" / "published")
    _fingerprint(out / "ui")

    # A root landing page, so the deployed URL works without anyone knowing to add /ui/.
    (out / "index.html").write_text(
        '<!doctype html><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url=ui/">'
        '<title>How the European Parliament votes</title>'
        '<p><a href="ui/">How the European Parliament votes</a></p>\n'
    )

    # GitHub Pages runs Jekyll by default, which skips files and directories beginning
    # with an underscore and adds a build step this site does not need.
    (out / ".nojekyll").write_text("")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    files = sum(1 for f in out.rglob("*") if f.is_file())
    print(f"  {files} files, {total / 1e6:.1f} MB in {out}/")
    print(f"  upload {out}/ as-is; it needs no server-side anything")
    print("  for GitHub Pages: scripts/deploy-gh-pages.sh")
    return out
