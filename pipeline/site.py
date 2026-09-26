"""Assemble a deployable directory (TK12).

The site reads `../data/published` relative to itself, which is convenient while
developing from the repository root but not what you want to upload. This copies the
interface and the published bundles into one self-contained tree with that relative
layout preserved, so deploying is uploading a directory — no build step, no server, no
configuration.

The licence file travels with the data, because ODbL asks that it does.
"""

import shutil
from pathlib import Path


def build(data_dir: Path, out: Path = Path("site")) -> Path:
    published = data_dir / "published"
    if not published.exists():
        raise SystemExit("nothing published yet — run `publish` first")

    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)

    shutil.copytree(Path("ui"), out / "ui")
    shutil.copytree(published, out / "data" / "published")

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
