#!/usr/bin/env bash
# Publish the built site to the gh-pages branch.
#
# The branch is rewritten as a single orphan commit each time rather than appended to.
# The site is ~19MB of regenerated data, so keeping its history would add that much to
# the repository on every deploy, for snapshots nobody will ever check out. The source
# of truth is the pipeline; gh-pages is only ever a rendering of it.
#
# Raw data stays out of master, which is why data/ and site/ are gitignored.
set -euo pipefail

BRANCH="gh-pages"
SITE="site"

cd "$(dirname "$0")/.."

[ -d "$SITE" ] || { echo "no $SITE/ — run: ./venv/bin/python -m pipeline site" >&2; exit 1; }
[ -f "$SITE/index.html" ] || { echo "$SITE/ looks incomplete" >&2; exit 1; }

commit=$(git rev-parse --short HEAD)
work=$(mktemp -d)
# Remove the worktree through git, not just the directory: deleting the directory alone
# leaves git holding a stale registration that a later run trips over.
trap 'cd "$OLDPWD" 2>/dev/null || true; git worktree remove --force "$work" 2>/dev/null || true; rm -rf "$work"' EXIT

git worktree add --detach "$work" >/dev/null
cd "$work"
git checkout --orphan "$BRANCH" >/dev/null 2>&1
git rm -rf . >/dev/null 2>&1 || true

cp -r "$OLDPWD/$SITE/." .
git add -A
git commit -q -m "Publish site built from $commit"
# The branch is committed locally before this point, so a push that fails for want of
# credentials leaves the work intact: authenticate and push, no rebuild needed.
git push -f origin "$BRANCH"

cd "$OLDPWD"
echo "pushed $BRANCH — enable Pages for this branch at:"
echo "  https://github.com/pduchesne/eu_votes/settings/pages"
