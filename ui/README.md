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
| Members | `UC01` | Search by name, country or group; per-term participation and group loyalty. |
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
