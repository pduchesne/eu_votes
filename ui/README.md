# The citizen-facing site

Static files. No build step, no framework, no bundler — the site reads the published
JSON bundles directly, so deploying it is copying a directory.

## Running it locally

From the repository root, after the pipeline has produced `data/published/`:

```
$> ./venv/bin/python -m http.server 8765
```

Then open <http://localhost:8765/ui/>.

It is served from the repository root rather than from `ui/` because the pages read
`../data/published/*.json`. To deploy, copy `ui/` and the published bundles together and
keep that relative layout.

## What is here

| View | Use case | What it shows |
|---|---|---|
| Political landscape | `UC02` | The 3D point cloud, one point per member, positioned by how they voted. Orbit, zoom, filter by group, click a point for that member. Below it, the votes that most define each axis. |
| Topic landscape | `UC02.01` | The same cloud, framed by three subjects the reader picks instead of by principal components. Below it, every subject that carries an axis; select one for each group's distribution along it and the texts anchoring either end. |
| Members | `UC01` | Search by name, country or group; per-term participation and group loyalty. A member's page adds the subjects where they sit furthest from their own group, each on a bar against that group's spread. |
| One group | `UC01` | Reached from the landscape legend, a member's page, or a theme page. Size, cohesion, and the subjects where the group departs from its own usual position, against the other groups. |
| Topics | `UC04` | How often each group's majority voted in favour, by Parliament's own subject areas. |
| How this is made | `UC05` | Provenance, verification coverage, how positions are computed, and what the figures are not. |

## Things that are deliberate

- **Nothing is drawn from a database.** The site reads `IF-PUBLISHED-DATA` and nothing
  else, so it cannot outrun what the pipeline verified.
- **Groups are coloured by identity, never by position.** Colouring a point by where it
  sits would invent a left-right axis the analysis does not claim to have found.
- **Every vote links to Parliament's own document**, because that is the platform's
  authority — not whichever dataset the pipeline happened to load.
- **Participation, not attendance.** Parliament publishes no record of who was absent,
  so the wording says participation everywhere it appears.
- **deck.gl is loaded from a CDN at a pinned version.** If it fails to load, the 3D view
  says so and the rest of the site still works.
- **"Stands out" is always measured against the right baseline.** A member's distance
  from the chamber mostly restates which group they joined, and a group at one end of the
  chamber is at that end on nearly every subject. Both pages therefore rank subjects by
  departure from the member's or group's *own* usual position, scaled by their own spread
  across subjects — so the number means the same thing on a page comparing one member
  against 700 peers and one comparing a group against eight.
- **A topic axis is never presented as a for-or-against score.** Restrictive and permissive
  proposals on a subject both come to a vote, so a yes-count would put the backers of
  opposing texts at the same end. Each subject publishes how far the naive reading would
  have agreed with its axis, and the page says when it would mislead.
