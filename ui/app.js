// Citizen-facing views over the published bundles (PJ03).
//
// Reads IF-PUBLISHED-DATA only — never a database, never the ingest source. Every vote
// shown links to the European Parliament document it was verified against, because the
// platform's authority is Parliament's record and not whichever dataset we loaded.

const DATA = "../data/published";

// Group colours: deliberately not a left-right ramp. Components have no political
// direction, so colouring by position would invent one.
const GROUP_COLOUR = {
  EPP: [51, 102, 204], SD: [204, 51, 51], RENEW: [240, 160, 30], ALDE: [240, 160, 30],
  GREEN_EFA: [60, 150, 80], ECR: [90, 120, 170], GUE_NGL: [150, 40, 90],
  ID: [110, 90, 170], PFE: [110, 90, 170], ESN: [80, 70, 120],
  EFDD: [130, 140, 150], ENF: [110, 90, 170], NI: [140, 145, 150],
};
const FALLBACK = [150, 150, 150];

const state = { meta: null, meps: [], groups: [], topics: [], votes: {}, term: null, deck: null };

const $ = (id) => document.getElementById(id);
const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
const num = (v) => (v == null ? "—" : v.toLocaleString());

async function load(name) {
  const response = await fetch(`${DATA}/${name}`);
  if (!response.ok) throw new Error(`${name}: ${response.status}`);
  return response.json();
}

async function boot() {
  try {
    const [meta, meps, groups, topics] = await Promise.all(
      ["meta.json", "meps.json", "groups.json", "topics.json"].map(load)
    );
    Object.assign(state, { meta, meps, groups, topics });
    state.term = Math.max(...meta.terms);
  } catch (error) {
    $("loading").textContent =
      `Could not load the published data (${error.message}). Run the pipeline, then serve the repository root.`;
    return;
  }
  $("loading").hidden = true;
  renderProvenance();
  renderMethodology();
  initLandscape();
  initMeps();
  initTopics();
  window.addEventListener("hashchange", route);
  route();
}

function route() {
  const view = (location.hash.replace("#/", "") || "landscape").split("/")[0];
  const known = ["landscape", "meps", "topics", "methodology"];
  const active = known.includes(view) ? view : "landscape";
  known.forEach((name) => ($(`view-${name}`).hidden = name !== active));
  document.querySelectorAll("nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.view === active)
  );
  if (active === "landscape") drawLandscape();
}

function termOptions(select, onChange) {
  select.innerHTML = state.meta.terms
    .slice()
    .sort((a, b) => b - a)
    .map((t) => `<option value="${t}">${termLabel(t)}</option>`)
    .join("");
  select.value = String(state.term);
  select.onchange = () => {
    state.term = Number(select.value);
    onChange();
  };
}

const TERM_YEARS = { 8: "2014–2019", 9: "2019–2024", 10: "2024– " };
const termLabel = (t) => `${t}th term (${TERM_YEARS[t] || ""})`;

// ---------------------------------------------------------------- provenance

function renderProvenance() {
  const { verification, ingest_source, generated_at, reference_of_record } = state.meta;
  const share = verification.votes_verified / verification.votes_in_store;
  $("provenance").innerHTML = `
    Built ${generated_at.slice(0, 10)} from
    <a href="${ingest_source.repo}">${ingest_source.name}</a>
    (${ingest_source.licence}, release ${ingest_source.release_tag}).
    ${num(verification.votes_verified)} of ${num(verification.votes_in_store)} votes
    (${pct(share)}) were checked against ${reference_of_record.name}; figures are built
    only from those. <a href="#/methodology">How this is made</a>.`;
}

function renderMethodology() {
  const { verification: v, analysis, caveats, ingest_source, reference_of_record } = state.meta;
  const variance = state.meta.terms
    .filter((t) => analysis[t])
    .map((t) => {
      const a = analysis[t];
      const explained = a.explained_variance.reduce((x, y) => x + y, 0);
      return `<tr><td>${termLabel(t)}</td><td class="num">${num(a.meps)}</td>
              <td class="num">${num(a.votes)}</td><td class="num">${pct(explained)}</td></tr>`;
    })
    .join("");

  $("methodology").innerHTML = `
    <p class="lede">The European Parliament's own record is the authority here. Everything
    below is checkable against it, and where it cannot be checked, that is said plainly.</p>

    <h2>Where the numbers come from</h2>
    <p>Votes are loaded from <a href="${ingest_source.repo}">${ingest_source.name}</a>,
    published under ${ingest_source.licence}, which derives them from
    ${ingest_source.upstream}. That dataset is a convenience, not the authority: every
    ballot is compared against ${reference_of_record.name}, and a vote that disagrees is
    excluded from every figure rather than shown with a caveat.</p>
    <p><b>${num(v.votes_verified)} of ${num(v.votes_in_store)} votes verified.</b>
    ${num(v.discrepancies)} were excluded for disagreeing with Parliament's record, and
    ${num(v.ep_record_anomalies)} defects were found in Parliament's own documents —
    counted against neither side. ${num(v.explained_source_gaps)} votes have a ballot the
    source could not attribute to a named member.</p>

    <h2>How positions are computed</h2>
    <p>Each member is placed by principal component analysis over their roll-call votes:
    the axes are whatever best separates how members actually voted. Terms are fitted
    separately and then rotated onto a common frame using the members who served in more
    than one, because independently fitted axes are otherwise not comparable.</p>
    <div class="scroll"><table>
      <thead><tr><th>Term</th><th class="num">Members</th><th class="num">Votes</th>
      <th class="num">Variance explained by 3 axes</th></tr></thead>
      <tbody>${variance}</tbody></table></div>
    <p class="caveat">A component's sign and rotation are arbitrary. Distance and
    clustering carry meaning; being left or right of zero does not.</p>

    <h2>What these figures are not</h2>
    <ul>${caveats.map((c) => `<li>${c}</li>`).join("")}</ul>`;
}

// ---------------------------------------------------------------- members

function initMeps() {
  const search = $("mep-search");
  const run = () => renderMepList(search.value.trim().toLowerCase());
  search.addEventListener("input", run);
  run();
}

function mepTerms(mep) {
  return Object.keys(mep.record).map(Number).sort((a, b) => b - a);
}

function renderMepList(query) {
  const matches = state.meps.filter((mep) => {
    if (!query) return true;
    const haystack = [
      mep.first_name, mep.last_name, mep.country_code, mep.constituency,
      ...(mep.groups || []),
    ].join(" ").toLowerCase();
    return haystack.includes(query);
  });
  $("mep-count").textContent =
    `${num(matches.length)} of ${num(state.meps.length)} members${query ? " match" : ""}.`;
  $("mep-results").innerHTML = matches
    .slice(0, 60)
    .map(
      (mep) => `<button class="card" data-id="${mep.id}">
        <img src="${mep.photo_url}" alt="" loading="lazy">
        <span>
          <span class="who">${mep.first_name || ""} ${mep.last_name}</span>
          <span class="meta">${mep.country_code} · ${(mep.groups || []).join(", ")}</span>
        </span></button>`
    )
    .join("");
  $("mep-results").querySelectorAll(".card").forEach((card) =>
    card.addEventListener("click", () => showMep(Number(card.dataset.id)))
  );
}

function showMep(id, container = $("mep-detail")) {
  const mep = state.meps.find((m) => m.id === id);
  if (!mep) return;
  const rows = mepTerms(mep)
    .map((term) => {
      const r = mep.record[term];
      return `<tr><td>${termLabel(term)}</td><td>${r.group_code || "—"}</td>
        <td class="num">${num(r.votes_cast)}</td><td class="num">${pct(r.loyalty)}</td>
        <td class="num">${r.main_votes_cast == null ? "—" : num(r.main_votes_cast)}</td>
        <td class="num">${pct(r.main_loyalty)}</td></tr>`;
    })
    .join("");

  container.hidden = false;
  container.innerHTML = `
    <h3>${mep.first_name || ""} ${mep.last_name}</h3>
    <p class="meta">${mep.country_code}${mep.constituency ? ` · ${mep.constituency}` : ""}
      · <a href="${mep.ep_url}">profile at the European Parliament</a></p>
    <div class="scroll"><table>
      <thead><tr><th>Term</th><th>Group</th><th class="num">Roll-call votes</th>
        <th class="num">Voted with group</th><th class="num">Substantive votes</th>
        <th class="num">With group (substantive)</th></tr></thead>
      <tbody>${rows}</tbody></table></div>
    <p class="caveat">Counts are roll-call votes only. Parliament publishes no record of
    who was absent, so these are participation figures, not attendance. "Voted with
    group" compares each member against their own group's majority; the substantive
    column excludes amendment and procedural votes, which make up most of the total.
    ${mep.record[8] ? "Substantive figures are unavailable for the 8th term, whose source carries no such flag." : ""}</p>`;
  container.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ---------------------------------------------------------------- topics

function initTopics() {
  termOptions($("topics-term"), renderTopics);
  renderTopics();
}

function renderTopics() {
  const rows = state.topics.filter((t) => t.term === state.term);
  if (!rows.length) {
    $("topics-table").innerHTML =
      `<p class="note">No subject-tagged substantive votes for ${termLabel(state.term)}.
       Subject tags and the substantive-vote flag both start in 2019.</p>`;
    return;
  }
  const groups = [...new Set(rows.map((r) => r.group_code))].sort();
  // Busiest subjects first: with 147 of them in the 8th term, alphabetical order buries
  // everything anyone would actually look for.
  const volume = new Map();
  rows.forEach((r) => volume.set(r.topic_label, (volume.get(r.topic_label) || 0) + r.votes));
  const topics = [...volume.keys()].sort((a, b) => volume.get(b) - volume.get(a));
  const lookup = new Map(rows.map((r) => [`${r.topic_label}|${r.group_code}`, r]));
  const basis = rows[0].basis || "substantive votes";

  $("topics-table").innerHTML = `<p class="note">${topics.length} subjects, busiest first.</p>
    <div class="scroll"><table>
    <thead><tr><th>Subject</th>${groups.map((g) => `<th class="num">${g}</th>`).join("")}</tr></thead>
    <tbody>${topics
      .map((topic) => {
        const cells = groups
          .map((group) => {
            const row = lookup.get(`${topic}|${group}`);
            if (!row) return `<td class="num">—</td>`;
            return `<td class="num" title="${num(row.votes)} votes">${pct(row.support)}</td>`;
          })
          .join("");
        return `<tr><td>${topic}</td>${cells}</tr>`;
      })
      .join("")}</tbody></table></div>
    <p class="caveat">Share of ${basis} on that subject where the group's majority voted
    in favour. Subjects are Parliament's own Legislative Observatory classification, not
    ours. A dash means fewer than fifteen such votes for that group.
    ${basis === "all votes"
      ? "This term's source carries no flag separating substantive votes from amendments, so its figures cover all roll-call votes and are not directly comparable with the other terms."
      : ""}</p>`;
}

// ---------------------------------------------------------------- landscape

function initLandscape() {
  termOptions($("landscape-term"), () => {
    renderFilterOptions();
    drawLandscape();
  });
  $("landscape-colour").onchange = drawLandscape;
  renderFilterOptions();
  $("landscape-filter").onchange = drawLandscape;
}

function renderFilterOptions() {
  const groups = [...new Set(landscapePoints().map((p) => p.group))].sort();
  $("landscape-filter").innerHTML =
    `<option value="">All groups</option>` +
    groups.map((g) => `<option value="${g}">${groupLabel(g)}</option>`).join("");
}

function landscapePoints() {
  return state.meps
    .filter((mep) => mep.record[state.term]?.position)
    .map((mep) => ({
      id: mep.id,
      name: `${mep.first_name || ""} ${mep.last_name}`.trim(),
      group: mep.record[state.term].group_code || "NI",
      country: mep.country_code,
      loyalty: mep.record[state.term].loyalty,
      votes: mep.record[state.term].votes_cast,
      position: mep.record[state.term].position,
    }));
}

function colourFor(point, mode, countries) {
  if (mode === "country") {
    const index = countries.indexOf(point.country);
    const hue = (index * 47) % 360;
    return hslToRgb(hue, 0.55, 0.55);
  }
  return GROUP_COLOUR[point.group] || FALLBACK;
}

function hslToRgb(h, s, l) {
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [f(0) * 255, f(8) * 255, f(4) * 255].map(Math.round);
}

function drawLandscape() {
  const points = landscapePoints();
  const analysis = state.meta.analysis[state.term];
  const explained = analysis
    ? analysis.explained_variance.reduce((a, b) => a + b, 0)
    : null;
  $("landscape-caveat").textContent =
    `${num(points.length)} members placed from ${num(analysis?.votes)} verified votes. ` +
    `The three axes together account for ${pct(explained)} of the variation in how members voted. ` +
    `Orientation is arbitrary — read clusters and distances, not directions.`;

  if (!window.deck) {
    $("deck-wrap").innerHTML =
      `<p class="note" style="padding:1rem">The 3D view needs the deck.gl library, which
       could not be loaded. Everything else on this page works without it.</p>`;
    return;
  }

  const highlight = $("landscape-filter").value;
  const mode = $("landscape-colour").value;
  const countries = [...new Set(points.map((p) => p.country))].sort();
  // Fit the cloud to the frame rather than a fixed guess: outliers are the point of
  // this view, so the 98th percentile keeps them visible without letting one member
  // shrink everyone else into the middle.
  const magnitudes = points.flatMap((p) => p.position.map(Math.abs)).sort((a, b) => a - b);
  const spread = magnitudes[Math.floor(magnitudes.length * 0.98)] || 1;
  const frame = Math.min($("deck-wrap").clientWidth, $("deck-wrap").clientHeight);

  const layer = new deck.PointCloudLayer({
    id: "meps",
    data: points,
    coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
    getPosition: (d) => d.position,
    getColor: (d) => {
      const colour = colourFor(d, mode, countries);
      const dim = highlight && d.group !== highlight;
      return dim ? [...colour.map((c) => c * 0.25 + 150 * 0.25), 60] : [...colour, 230];
    },
    pointSize: 5,
    pickable: true,
    updateTriggers: { getColor: [mode, highlight] },
  });

  const view = new deck.OrbitView({ orbitAxis: "Y", fovy: 50 });
  const viewState = {
    target: [0, 0, 0],
    rotationX: 18,
    rotationOrbit: 25,
    zoom: Math.log2((frame * 0.42) / spread),
    minZoom: -4,
    maxZoom: 8,
  };

  if (state.deck) state.deck.finalize();
  state.deck = new deck.Deck({
    canvas: "deck",
    views: view,
    initialViewState: viewState,
    controller: true,
    layers: [layer],
    getTooltip: ({ object }) =>
      object && {
        html: `<b>${object.name}</b><br>${groupLabel(object.group)} · ${object.country}<br>
               voted with group ${pct(object.loyalty)}`,
        style: { fontSize: "0.8rem" },
      },
    onClick: ({ object }) => object && showMep(object.id, $("landscape-detail")),
  });

  renderLegend(mode, countries, points);
  renderAxisVotes();
}

function groupLabel(code) {
  const match = state.groups.find((g) => g.code === code);
  return match?.short_label || match?.label || code;
}

function renderLegend(mode, countries, points) {
  const keys = mode === "country" ? countries : [...new Set(points.map((p) => p.group))].sort();
  const existing = $("deck-wrap").querySelector(".legend");
  if (existing) existing.remove();
  const legend = document.createElement("div");
  legend.className = "legend";
  legend.innerHTML = keys
    .map((key) => {
      const sample = points.find((p) => (mode === "country" ? p.country : p.group) === key);
      const [r, g, b] = colourFor(sample, mode, countries);
      const label = mode === "country" ? key : groupLabel(key);
      return `<div><span class="swatch" style="background:rgb(${r},${g},${b})"></span>${label}</div>`;
    })
    .join("");
  $("deck-wrap").appendChild(legend);
}

async function renderAxisVotes() {
  const term = state.term;
  if (!state.votes[term]) {
    try {
      state.votes[term] = await load(`votes-t${term}.json`);
    } catch {
      $("axis-votes").innerHTML = `<p class="note">Vote list for this term is unavailable.</p>`;
      return;
    }
  }
  if (state.term !== term) return; // the user moved on while it loaded

  const votes = state.votes[term].filter((v) => v.verified && v.components);
  if (!votes.length) {
    $("axis-votes").innerHTML =
      `<p class="note">Per-vote axis coefficients are not present in this build of the
       published data.</p>`;
    return;
  }
  $("axis-votes").innerHTML = [0, 1, 2]
    .map((axis) => {
      const top = votes
        .slice()
        .sort((a, b) => Math.abs(b.components[axis]) - Math.abs(a.components[axis]))
        .slice(0, 5);
      return `<section><h3>Axis ${axis + 1}</h3><ol>${top
        .map(
          (v) => `<li><a href="${v.source}">${v.title || v.procedure_reference || v.id}</a>
            <br><span class="note">${v.date}${v.topics?.length ? ` · ${v.topics[0]}` : ""}</span></li>`
        )
        .join("")}</ol></section>`;
    })
    .join("");
}

boot();
