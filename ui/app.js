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
  // Groups that existed only in earlier terms. ALDE shares Renew's colour as its
  // predecessor in the liberal family; they never appear in the same term. EFDD needs
  // its own, having been too close to the grey used for non-attached members.
  EFDD: [150, 110, 60], ENF: [110, 90, 170], NI: [140, 145, 150],
};
const FALLBACK = [150, 150, 150];

const state = {
  meta: null, axisVotes: null, axes: null, topicDetail: null, cloud: null, topicDeck: null,
  meps: [], groups: [], topics: [], stories: [], votes: {}, term: null, deck: null,
  // Topic landscape: the bundle, which term's frame is currently drawn, its deck, and the
  // selected subject.
  topicAxes: null, tlDrawn: null, tlDeck: null, tlTopic: null, tlChosenFrame: false,
};

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
    // Stories are optional: a deployment with none should still work.
    state.stories = await load("stories.json").catch(() => []);
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
  initTopicLandscape();
  initMeps();
  initTopics();
  initAxes();
  renderStoryList();
  window.addEventListener("hashchange", route);
  route();
}

function route() {
  const parts = location.hash.replace("#/", "").split("/");
  const view = parts[0] || "landscape";
  const known = ["landscape", "topiclandscape", "meps", "member", "axes", "topic", "topics", "stories", "methodology"];
  const active = known.includes(view) ? view : "landscape";
  known.forEach((name) => ($(`view-${name}`).hidden = name !== active));
  document.querySelectorAll("nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.view === active)
  );
  if (active === "landscape") drawLandscape();
  if (active === "topiclandscape") renderTopicLandscape(decodeURIComponent(parts.slice(1).join("/")));
  if (active === "axes") renderAxes();
  if (active === "topic") renderTopic(decodeURIComponent(parts.slice(1).join("/")));
  if (active === "member") renderMember(parts[1]);
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
  const { verification, generated_at, reference_of_record, licence } = state.meta;
  const share = verification.votes_verified / verification.votes_in_store;
  // Attribution is a licence obligation, not decoration: ODbL and the EP's reuse terms
  // both require the sources to be credited wherever the data is shown.
  const credits = (licence?.attribution || [])
    .map((a) => `<a href="${a.url}">${a.statement || a.name}</a>${a.licence ? ` (${a.licence})` : ""}`)
    .join(" · ");
  $("provenance").innerHTML = `
    ${num(verification.votes_verified)} of ${num(verification.votes_in_store)} votes
    (${pct(share)}) verified against ${reference_of_record.name}; every figure here is
    built only from those. Built ${generated_at.slice(0, 10)}.
    <a href="#/methodology">How this is made</a>.
    <br>Sources: ${credits}.
    ${licence ? `<br>This data is published under the
      <a href="${licence.published_data.url}">${licence.published_data.name}</a>.` : ""}`;
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

    <h2>Axes you can name</h2>
    <p>Those axes separate members as sharply as any three numbers can, which is exactly
    why they cannot be named: "axis 2" is not a thing anyone holds an opinion about. So the
    same computation is run again on one subject at a time — the votes Parliament itself
    classified under a theme — giving an axis that <em>can</em> be named, at the cost of
    explaining less. That is what the
    <a href="#/topiclandscape">topic landscape</a> shows.</p>
    <p>These are not for-or-against scales, and the distinction matters. Restrictive and
    permissive proposals on a subject both come to a vote, so counting how often a member
    voted yes would put the supporters of opposite texts at the same end. Each vote instead
    enters with a signed weight learned from who votes together, so backing a restrictive
    text and backing a permissive one pull a member in opposite directions. Each topic axis
    reports how far the naive yes-count would have agreed with it, because on many subjects
    it does not — and on some it inverts outright.</p>
    <p>Which three subjects frame that view is not a cosmetic choice. Each subject's axis
    points somewhere in the main three-axis space, and most of them point the same way:
    in the 9th term, 33 of 38 subjects lie closest to the first axis, five to the second,
    and <em>none</em> to the third. Framing the view with the busiest subjects therefore
    draws one division three times over — it covered 0.01 of the space, where 1.00 would
    be three unrelated divisions. The default three are instead chosen, from subjects with
    at least 150 verified votes, to come as close to perpendicular as the data allows.
    Any three can be selected, and the page states what the chosen three actually span.</p>
    <p class="caveat">That no subject's internal disagreement resembles the third axis is
    itself a result: the third axis is not about any one policy area but cuts across them.
    It is also why even the best topic frame covers under half the space.</p>

    <p class="caveat">Direction remains arbitrary here too. Each topic axis is oriented to
    agree with the term's main axis so that the subjects can be compared with one another,
    and where that correlation is too weak to decide, the subject's most influential vote
    is made positive so the choice is at least reproducible. Neither rule makes an end
    "for" or "against" anything: only the anchoring texts listed at each end say what
    sitting there meant.</p>

    <h2>Licence and credit</h2>
    <p>${state.meta.licence?.published_data.note || ""}
    The published bundles are available under the
    <a href="${state.meta.licence?.published_data.url}">${state.meta.licence?.published_data.name}</a>.</p>
    <ul>${(state.meta.licence?.attribution || [])
      .map((a) => `<li><a href="${a.url}">${a.name}</a>${a.licence ? ` — ${a.licence}` : ""}${a.statement ? ` — ${a.statement}` : ""}<br><span class="note">${a.role}</span></li>`)
      .join("")}</ul>

    <h2>What these figures are not</h2>
    <ul>${caveats.map((c) => `<li>${c}</li>`).join("")}</ul>`;
}

// ---------------------------------------------------------------- members

function initMeps() {
  const search = $("mep-search");
  $("mep-term").innerHTML =
    `<option value="">Any term</option>` +
    state.meta.terms
      .slice()
      .sort((a, b) => b - a)
      .map((t) => `<option value="${t}">${termLabel(t)}</option>`)
      .join("");
  $("mep-country").innerHTML =
    `<option value="">Any country</option>` +
    Object.entries(state.meta.countries || {})
      .filter(([code]) => state.meps.some((m) => m.country_code === code))
      .map(([code, label]) => `<option value="${code}">${escape(label)}</option>`)
      .join("");

  const run = () => renderMepList(search.value.trim().toLowerCase());
  // The group list depends on the term: offering ALDE while the 10th term is selected
  // would only ever return nothing.
  const refreshGroups = () => {
    const term = $("mep-term").value;
    const previous = $("mep-group").value;
    const codes = new Set();
    for (const mep of state.meps) {
      for (const [t, record] of Object.entries(mep.record)) {
        if ((!term || t === term) && record.group_code) codes.add(record.group_code);
      }
    }
    const options = [...codes].sort((a, b) => groupLabel(a).localeCompare(groupLabel(b)));
    $("mep-group").innerHTML =
      `<option value="">Any group</option>` +
      options.map((c) => `<option value="${c}">${escape(groupLabel(c))}</option>`).join("");
    $("mep-group").value = codes.has(previous) ? previous : "";
  };

  refreshGroups();
  search.addEventListener("input", run);
  $("mep-term").addEventListener("change", () => {
    refreshGroups();
    run();
  });
  $("mep-group").addEventListener("change", run);
  $("mep-country").addEventListener("change", run);
  run();
}

/** Which of a member's terms satisfy the current term and group selection. */
function matchingTerms(mep, term, group) {
  return Object.entries(mep.record).filter(
    ([t, record]) => (!term || t === term) && (!group || record.group_code === group)
  );
}

function mepTerms(mep) {
  return Object.keys(mep.record).map(Number).sort((a, b) => b - a);
}

function renderMepList(query) {
  const term = $("mep-term").value;
  const group = $("mep-group").value;
  const country = $("mep-country").value;

  const matches = state.meps.filter((mep) => {
    if (country && mep.country_code !== country) return false;
    if ((term || group) && !matchingTerms(mep, term, group).length) return false;
    if (!query) return true;
    return [mep.first_name, mep.last_name, mep.constituency]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });

  const filtered = query || term || group || country;
  $("mep-count").textContent =
    `${num(matches.length)} of ${num(state.meps.length)} members${filtered ? " match" : ""}.` +
    (matches.length > 60 ? " Showing the first 60." : "");

  $("mep-results").innerHTML = matches
    .slice(0, 60)
    .map((mep) => {
      // Show the group that the current selection is actually about, rather than every
      // group the member ever sat with.
      const shown = matchingTerms(mep, term, group);
      const groups = [...new Set((shown.length ? shown : Object.entries(mep.record))
        .map(([, r]) => r.group_code)
        .filter(Boolean))].map(groupLabel);
      const country = (state.meta.countries || {})[mep.country_code] || mep.country_code;
      return `<a class="card" href="#/member/${mep.id}">
        <img src="${mep.photo_url}" alt="" loading="lazy">
        <span>
          <span class="who">${escape(mep.first_name || "")} ${escape(mep.last_name)}</span>
          <span class="meta">${escape(country)} · ${escape(groups.join(", "))}</span>
        </span></a>`;
    })
    .join("");
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
    <p><a href="#/member/${mep.id}">Full profile →</a></p>
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
  const codeFor = new Map(rows.map((r) => [r.topic_label, r.topic_code]));
  const basis = rows[0].basis || "substantive votes";

  $("topics-table").innerHTML = `<p class="note">${topics.length} themes, busiest first — the same vocabulary the
     <a href="#/axes">axes</a> are described in.</p>
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
        const code = codeFor.get(topic);
        const name = code
          ? `<a href="#/topic/${encodeURIComponent(code)}">${escape(topic)}</a>`
          : escape(topic);
        return `<tr><td>${name}</td>${cells}</tr>`;
      })
      .join("")}</tbody></table></div>
    <p class="caveat">Share of ${basis} on that subject where the group's majority voted
    in favour. Themes are Parliament's own Legislative Observatory classification read one
    level above the individual file, so "Budget of the Union" rather than "2015
    discharge". A dash means fewer than fifteen such votes for that group.
    ${basis === "all votes"
      ? "This term's source carries no flag separating substantive votes from amendments, so its figures cover all roll-call votes and are not directly comparable with the other terms."
      : ""}</p>`;
}

// ---------------------------------------------------------------- axes

function initAxes() {
  termOptions($("axes-term"), renderAxes);
}

/** Members' positions along one global axis, grouped by political group. */
function axisValues(term, axis) {
  const values = new Map();
  for (const mep of state.meps) {
    const record = mep.record[term];
    if (!record?.position) continue;
    const group = record.group_code || "NI";
    if (!values.has(group)) values.set(group, []);
    values.get(group).push(record.position[axis - 1]);
  }
  return values;
}

/** Where each group's members sit along one axis, as a row of small density curves.
 *
 * Each group is scaled to its own peak rather than to a shared one. Otherwise the two
 * largest groups would be the only legible shapes, and the question here is where a
 * group sits, not how large it is.
 *
 * `values` maps a group code to its members' positions; `ends` optionally labels the two
 * extremes, since a bare number on an arbitrary scale tells a reader nothing. */
function ridgeline(values, { label = "one axis", ends = null } = {}) {
  const all = [...values.values()].flat();
  if (!all.length) return "";
  const lo = Math.min(...all), hi = Math.max(...all);
  const bins = 60, rowHeight = 26, labelWidth = 92, width = 640, pad = 8,
        footer = ends ? 34 : 26;
  const order = [...values.keys()].sort(
    (a, b) => mean(values.get(a)) - mean(values.get(b))
  );
  const height = order.length * rowHeight + footer;
  const x = (v) => labelWidth + ((v - lo) / (hi - lo || 1)) * (width - labelWidth - pad);

  const rows = order.map((group, index) => {
    const counts = new Array(bins).fill(0);
    for (const v of values.get(group)) {
      const bin = Math.min(bins - 1, Math.floor(((v - lo) / (hi - lo || 1)) * bins));
      counts[bin] += 1;
    }
    // A light three-point smooth: with a few dozen members per group the raw histogram
    // is spiky enough to read as noise rather than shape.
    const smooth = counts.map((_, i) =>
      (counts[i - 1] || 0) * 0.25 + counts[i] * 0.5 + (counts[i + 1] || 0) * 0.25
    );
    const peak = Math.max(...smooth) || 1;
    const baseline = index * rowHeight + rowHeight - 4;
    const points = smooth.map((value, i) => {
      const px = labelWidth + ((i + 0.5) / bins) * (width - labelWidth - pad);
      return `${px.toFixed(1)},${(baseline - (value / peak) * (rowHeight - 7)).toFixed(1)}`;
    });
    const [r, g, b] = GROUP_COLOUR[group] || FALLBACK;
    return `
      <path d="M${labelWidth},${baseline} L${points.join(" L")} L${width - pad},${baseline} Z"
            fill="rgb(${r},${g},${b})" fill-opacity="0.62"
            stroke="rgb(${r},${g},${b})" stroke-width="0.8"/>
      <text class="label" x="${labelWidth - 6}" y="${baseline - 2}" text-anchor="end">${escape(
        groupLabel(group)
      )}</text>`;
  });

  const baseY = height - footer + 6;
  const zero = lo < 0 && hi > 0
    ? `<line class="axis-line" x1="${x(0)}" y1="4" x2="${x(0)}" y2="${baseY - 2}"
             stroke-dasharray="2 3"/>`
    : "";
  const caption = ends
    ? `<text class="tick" x="${labelWidth}" y="${height - 4}">◀ ${escape(ends[0])}</text>
       <text class="tick" x="${width - pad}" y="${height - 4}" text-anchor="end">${escape(ends[1])} ▶</text>`
    : `<text class="tick" x="${labelWidth}" y="${height - 8}">${lo.toFixed(0)}</text>
       <text class="tick" x="${width - pad}" y="${height - 8}" text-anchor="end">${hi.toFixed(0)}</text>`;
  return `<svg class="ridge" viewBox="0 0 ${width} ${height}" role="img"
       aria-label="Distribution of each political group along ${escape(label)}">
    ${zero}
    ${rows.join("")}
    <line class="axis-line" x1="${labelWidth}" y1="${baseY}" x2="${width - pad}" y2="${baseY}"/>
    ${caption}
  </svg>`;
}

const mean = (xs) => xs.reduce((a, b) => a + b, 0) / (xs.length || 1);

function renderEnd(end, side) {
  // Themes first: they say what this end is about. The recurring words are the texture
  // underneath, useful but too specific to lead with.
  const themes = (end.themes || []).length
    ? `<p class="themes">${end.themes
        .map((t) => `<a class="theme" href="#/topic/${encodeURIComponent(t.code || t.theme)}">${escape(t.theme)}</a>`)
        .join("")}</p>`
    : "";
  const keywords = end.keywords.length
    ? `<p class="keywords">Recurring words: <b>${end.keywords.map(escape).join(", ")}</b></p>`
    : "";
  return `<div class="end">
    <h3>Voting <em>for</em> these puts a member at the ${side}</h3>
    ${themes}${keywords}
    <ol>${end.votes
      .slice(0, 5)
      .map(
        (v) => `<li><a href="${v.source}">${escape(v.title)}</a>
          <span class="subject">${v.date}</span></li>`
      )
      .join("")}</ol></div>`;
}

async function renderAxes() {
  if (!state.axes) state.axes = await load("axes.json").catch(() => []);
  const entries = state.axes.filter((a) => a.term === state.term);
  if (!entries.length) {
    $("axes-list").innerHTML = `<p class="note">No axis data published for this term.</p>`;
    return;
  }
  $("axes-list").innerHTML = entries
    .map(
      (entry) => `<section class="axis-card">
        <h2>Axis ${entry.axis}</h2>
        <p class="variance">Accounts for ${pct(entry.explained_variance)} of the variation
          in how members voted. Members span ${entry.span.min.toFixed(0)} to
          ${entry.span.max.toFixed(0)} on it; each group's curve is scaled to its own
          peak, so the shape shows where a group sits, not how large it is.</p>
        ${ridgeline(axisValues(entry.term, entry.axis), { label: `axis ${entry.axis}` })}
        <div class="ends">
          ${renderEnd(entry.negative, "left")}
          ${renderEnd(entry.positive, "right")}
        </div>
      </section>`
    )
    .join("");
}

// ------------------------------------------------------- topic landscape

// Each axis is rescaled to its own spread before being drawn, so the frame shows how
// three subjects relate rather than which of them happens to divide Parliament hardest.
const TL_SPAN = 100;

function initTopicLandscape() {
  termOptions($("tl-term"), () => {
    state.tlDrawn = null;
    renderTopicLandscape(state.tlTopic);
  });
  ["tl-x", "tl-y", "tl-z"].forEach((id) =>
    ($(id).onchange = () => {
      state.tlChosenFrame = true;
      drawTopicFrame();
    })
  );
}

const topicBundle = () => state.topicAxes?.terms?.[String(state.term)] || null;

async function renderTopicLandscape(code) {
  if (!state.topicAxes) state.topicAxes = await load("topic-axes.json").catch(() => null);
  // The term is shared with the other views, so the selector may be showing a stale one
  // after a visit elsewhere.
  $("tl-term").value = String(state.term);
  const bundle = topicBundle();
  if (!bundle) {
    $("tl-note").innerHTML = state.topicAxes
      ? `<p class="note">No subject has enough verified votes in ${termLabel(state.term)} to
         carry an axis of its own. Subject tags start in 2014 and are sparsest in the
         current term, which is still short.</p>`
      : `<p class="note">Topic axes are not present in this build of the published data.</p>`;
    $("tl-list").innerHTML = "";
    $("tl-topic").innerHTML = "";
    return;
  }
  if (state.tlDrawn !== state.term) {
    fillFrameSelectors(bundle);
    renderTopicAxisList(bundle);
    drawTopicFrame();
    state.tlDrawn = state.term;
  }
  renderTopicAxisDetail(bundle, code);
}

/** The three framing subjects.
 *
 * Defaults to the frame the pipeline chose for spanning the main space, not to the
 * busiest subjects: in most terms the busiest all follow the chamber's first division,
 * so framing by them draws that one division three times and the other two components
 * never appear. */
function fillFrameSelectors(bundle) {
  const options = bundle.topics
    .map((t) => `<option value="${t.code}">${escape(t.label)}</option>`)
    .join("");
  const preferred = bundle.frame?.topics || [];
  ["tl-x", "tl-y", "tl-z"].forEach((id, index) => {
    const previous = $(id).value;
    const fallback = bundle.topics[Math.min(index, bundle.topics.length - 1)].code;
    $(id).innerHTML = options;
    // A selection the reader made themselves survives a change of term where the subject
    // still exists. One left over from another term's default must not: it is nobody's
    // choice, and carrying it across silently replaces this term's spanning frame with a
    // collapsed one.
    const keep = state.tlChosenFrame && bundle.topics.some((t) => t.code === previous);
    $(id).value = keep ? previous : preferred[index] || fallback;
  });
}

/** How much of the main space three subjects cover between them.
 *
 * The determinant of their three directions: 1 when mutually perpendicular, 0 when they
 * all describe the same division. This is what decides whether the view is a cloud or a
 * streak, and the reader is free to pick three that collapse — so it is recomputed for
 * whatever they chose rather than only published for the default. */
function frameSpan(chosen) {
  const m = chosen.map((t) => t.direction);
  if (m.some((row) => !row || row.some((v) => v == null))) return null;
  return Math.abs(
    m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
    m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
    m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
  );
}

/** Which of the main axes a subject most nearly is. */
function nearestComponent(topic) {
  if (!topic.direction || topic.direction.some((v) => v == null)) return null;
  const k = topic.direction.reduce(
    (best, v, i) => (Math.abs(v) > Math.abs(topic.direction[best]) ? i : best),
    0
  );
  return { axis: k + 1, weight: Math.abs(topic.direction[k]) };
}

/** Group membership and name per member, for whichever term is showing. */
function memberIndex() {
  const index = new Map();
  for (const mep of state.meps) {
    const record = mep.record[state.term];
    if (!record) continue;
    index.set(mep.id, {
      name: `${mep.first_name || ""} ${mep.last_name}`.trim(),
      group: record.group_code || "NI",
      country: mep.country_code,
    });
  }
  return index;
}

function correlation(xs, ys) {
  const n = xs.length;
  if (n < 3) return 0;
  const mx = mean(xs), my = mean(ys);
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i += 1) {
    const dx = xs[i] - mx, dy = ys[i] - my;
    sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
  }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0;
}

function drawTopicFrame() {
  const bundle = topicBundle();
  if (!bundle) return;
  const chosen = ["tl-x", "tl-y", "tl-z"].map((id) =>
    bundle.topics.find((t) => t.code === $(id).value)
  );
  if (chosen.some((t) => !t)) return;

  // A member only appears if all three subjects placed them; someone who never voted on
  // one of the three has no position in this frame and is not guessed at.
  const spread = chosen.map((topic) => {
    const magnitudes = topic.scores.filter((v) => v != null).map(Math.abs).sort((a, b) => a - b);
    return magnitudes[Math.floor(magnitudes.length * 0.98)] || 1;
  });
  const index = memberIndex();
  const points = [];
  bundle.members.forEach((id, i) => {
    const raw = chosen.map((topic) => topic.scores[i]);
    if (raw.some((v) => v == null)) return;
    const who = index.get(id) || { name: String(id), group: "NI", country: "" };
    points.push({
      id,
      ...who,
      raw,
      position: raw.map((v, k) => (v / spread[k]) * TL_SPAN),
    });
  });

  const pairs = [[0, 1], [0, 2], [1, 2]].map(([a, b]) => ({
    a, b, r: correlation(points.map((p) => p.raw[a]), points.map((p) => p.raw[b])),
  }));
  const tightest = pairs.reduce((x, y) => (Math.abs(y.r) > Math.abs(x.r) ? y : x));
  const span = frameSpan(chosen);
  const isDefault = (bundle.frame?.topics || []).every((code) =>
    chosen.some((t) => t.code === code)
  );

  // The one number that says whether this frame is a cloud or a streak. Three subjects
  // that all follow the chamber's main division draw it three times over, and the view
  // then shows less than the political landscape does, not more.
  const quality = span == null
    ? ""
    : span >= 0.3
    ? `These three between them cover <b>${span.toFixed(2)}</b> of the political space
       (1.00 would be three subjects dividing members in three unrelated ways), so the
       cloud has genuine depth: each axis is showing a different disagreement.`
    : span >= 0.12
    ? `These three cover <b>${span.toFixed(2)}</b> of the political space, so they overlap
       substantially — the cloud leans along one direction because these subjects largely
       share a division.`
    : `<b>These three barely span the space (${span.toFixed(2)} of 1.00.)</b> They all
       follow much the same division, so the view is drawing one disagreement three times
       and the cloud collapses to a streak.${
         isDefault ? "" : " The subjects offered by default span it better."
       }`;

  const lockstep = Math.abs(tightest.r) >= 0.8
    ? ` ${escape(chosen[tightest.a].label)} and ${escape(chosen[tightest.b].label)} move
        almost in lockstep (r = ${tightest.r.toFixed(2)}).`
    : "";

  $("tl-caveat").innerHTML =
    `${num(points.length)} members have a position on all three subjects. Each axis is the
     first component of that subject's votes alone, accounting for
     ${chosen.map((t) => `${pct(t.explained_variance)} of the disagreement on ${escape(t.label)}`).join(", ")}.
     Each is scaled to its own spread, so the shape shows how the three subjects relate,
     not which of them divides Parliament most. ${quality}${lockstep}
     ${isDefault
        ? `<br>These are the default three, chosen because their axes come closest to
           perpendicular. Picking the busiest subjects instead would collapse the view:
           in most terms they all follow the chamber's main division.`
        : ""}`;

  if (!window.deck) {
    $("tl-wrap").innerHTML =
      `<p class="note" style="padding:1rem">The 3D view needs the deck.gl library, which
       could not be loaded. The axis list below works without it.</p>`;
    return;
  }

  const frame = Math.min($("tl-wrap").clientWidth, $("tl-wrap").clientHeight);
  const axisLines = chosen.map((topic, k) => ({
    from: [0, 1, 2].map((d) => (d === k ? -TL_SPAN * 1.15 : 0)),
    to: [0, 1, 2].map((d) => (d === k ? TL_SPAN * 1.15 : 0)),
    // Long theme names run off the canvas when anchored at the axis tip, so they are
    // centred just inside it instead.
    at: [0, 1, 2].map((d) => (d === k ? TL_SPAN * 0.92 : 0)),
    label: topic.label,
  }));

  if (state.tlDeck) state.tlDeck.finalize();
  state.tlDeck = new deck.Deck({
    canvas: "tl-deck",
    views: new deck.OrbitView({ orbitAxis: "Y", fovy: 50 }),
    initialViewState: {
      target: [0, 0, 0],
      rotationX: 18,
      rotationOrbit: 25,
      zoom: Math.log2((frame * 0.4) / TL_SPAN),
      minZoom: -4,
      maxZoom: 8,
    },
    controller: true,
    layers: [
      new deck.LineLayer({
        id: "tl-axes",
        data: axisLines,
        coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
        getSourcePosition: (d) => d.from,
        getTargetPosition: (d) => d.to,
        getColor: [140, 146, 154, 140],
        getWidth: 1.2,
      }),
      new deck.TextLayer({
        id: "tl-axis-labels",
        data: axisLines,
        coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
        getPosition: (d) => d.at,
        getText: (d) => d.label,
        getSize: 12,
        sizeUnits: "pixels",
        // Without the clamp a label's apparent size follows its distance from the camera,
        // so the nearest axis shouts and the furthest is unreadable.
        sizeMinPixels: 11,
        sizeMaxPixels: 13,
        getColor: [70, 76, 86, 230],
        billboard: true,
        background: true,
        getBackgroundColor: [255, 255, 255, 190],
        backgroundPadding: [3, 2],
        getTextAnchor: "middle",
        getAlignmentBaseline: "center",
      }),
      new deck.PointCloudLayer({
        id: "tl-members",
        data: points,
        coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
        getPosition: (d) => d.position,
        getColor: (d) => [...(GROUP_COLOUR[d.group] || FALLBACK), 225],
        pointSize: 5,
        pickable: true,
      }),
    ],
    getTooltip: ({ object }) =>
      object && {
        html: `<b>${escape(object.name)}</b><br>${escape(groupLabel(object.group))} ·
               ${escape(object.country || "")}<br>` +
          chosen
            .map((t, k) => `${escape(t.label)}: ${object.raw[k].toFixed(1)}`)
            .join("<br>"),
        style: { fontSize: "0.78rem" },
      },
    onClick: ({ object }) => object && showMep(object.id, $("tl-detail")),
  });
}

function renderTopicAxisList(bundle) {
  const meta = state.topicAxes?.method || {};
  const framing = new Set(bundle.frame?.topics || []);
  $("tl-note").innerHTML =
    `${bundle.topics.length} subjects with at least ${num(meta.min_votes || 40)} verified
     votes and ${num(meta.min_members || 100)} members voting. "Explains" is how much of
     the disagreement on that subject its axis accounts for. "Nearest main axis" says which
     of the <a href="#/axes">three axes of the overall landscape</a> that subject most
     nearly <em>is</em> — most subjects turn out to be the first one over again, which is
     why the three marked <span class="badge">frame</span> are the default: their axes come
     closest to perpendicular. Select a subject for its distribution and the texts that
     anchor each end.`;

  $("tl-list").innerHTML = `<table>
    <thead><tr><th>Subject</th><th class="num">Votes</th><th class="num">Members</th>
      <th class="num">Explains</th><th class="num">Nearest main axis</th></tr></thead>
    <tbody>${bundle.topics
      .map((t) => {
        const near = nearestComponent(t);
        return `<tr data-code="${t.code}"${t.code === state.tlTopic ? ' class="chosen"' : ""}>
          <td><a href="#/topiclandscape/${encodeURIComponent(t.code)}">${escape(t.label)}</a>${
            framing.has(t.code) ? ' <span class="badge">frame</span>' : ""
          }</td>
          <td class="num">${num(t.votes)}</td><td class="num">${num(t.members)}</td>
          <td class="num">${pct(t.explained_variance)}</td>
          <td class="num">${
            near ? `axis ${near.axis} <span class="note">(${near.weight.toFixed(2)})</span>` : "—"
          }</td></tr>`;
      })
      .join("")}</tbody></table>`;
  // The whole row is the target, not just the link in it: a 5-column table whose only
  // hit area is eleven characters of text is a worse list than a plain one.
  $("tl-list")
    .querySelectorAll("tr[data-code]")
    .forEach((tr) =>
      tr.addEventListener("click", () => {
        location.hash = `#/topiclandscape/${encodeURIComponent(tr.dataset.code)}`;
      })
    );
}

function renderTopicAxisDetail(bundle, code) {
  state.tlTopic = code || null;
  $("tl-list")
    .querySelectorAll("tr[data-code]")
    .forEach((tr) => tr.classList.toggle("chosen", tr.dataset.code === state.tlTopic));

  const panel = $("tl-topic");
  const topic = bundle.topics.find((t) => t.code === code);
  if (!topic) {
    panel.innerHTML = `<p class="note">Pick a subject above to see how the groups spread
      along it, and which texts put a member at each end.</p>`;
    return;
  }

  const index = memberIndex();
  const values = new Map();
  bundle.members.forEach((id, i) => {
    const score = topic.scores[i];
    if (score == null) return;
    const group = index.get(id)?.group || "NI";
    if (!values.has(group)) values.set(group, []);
    values.get(group).push(score);
  });

  // Whether the obvious reading — how often a member backed the texts tabled on this
  // subject — describes this axis at all. On many subjects it inverts, and saying so is
  // the difference between a figure and a misleading one.
  const r = topic.support_correlation;
  const naive = r == null
    ? ""
    : Math.abs(r) >= 0.7
    ? `<p class="note">On this subject the simple reading works too: how often a member
       backed the texts tabled tracks their place on the axis (r = ${r.toFixed(2)}).</p>`
    : `<p class="caveat">Counting how often a member backed the texts tabled would
       <b>not</b> reproduce this axis (r = ${r.toFixed(2)}). Restrictive and permissive
       proposals both come to a vote, so a yes is only meaningful together with which text
       it was cast on — which is what the two lists below show.</p>`;

  panel.innerHTML = `<section class="axis-card">
    <h2>${escape(topic.label)}</h2>
    <p class="variance">${num(topic.votes)} verified roll-call votes,
      ${num(topic.members)} members. This axis accounts for ${pct(topic.explained_variance)}
      of the disagreement among those votes${
        nearestComponent(topic)
          ? `, and of the three axes of the overall landscape it lies closest to
             axis ${nearestComponent(topic).axis}
             (${nearestComponent(topic).weight.toFixed(2)} of its direction)`
          : ""
      }.
      <a href="#/topic/${encodeURIComponent(topic.code)}">Everything about this theme →</a></p>
    ${ridgeline(values, {
      label: topic.label,
      ends: ["voted for the texts on the left", "voted for the texts on the right"],
    })}
    ${naive}
    <div class="ends">
      ${renderTopicEnd(topic, "negative", "left")}
      ${renderTopicEnd(topic, "positive", "right")}
    </div>
    ${
      ["negative", "positive"].some((side) =>
        (topic.ends?.[side] || []).some((v) => v.shared_with_other_end)
      )
        ? `<p class="note">A text marked <span class="badge">also at the other end</span>
           appears in both lists because opposed amendments to one report anchor the two
           ends, and Parliament's record names no amendment — so the titles cannot tell
           them apart even though the votes are opposites. The group figures beside each
           one do.</p>`
        : ""
    }
  </section>`;
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/** One end of a topic axis: the texts that pull hardest towards it, and how the groups at
 *  the two extremes actually voted on each.
 *
 *  That pairing is the whole argument for using a component rather than a yes-count. The
 *  same group appears in both lists with mirrored figures, which shows the two ends are
 *  opposed positions and not two piles of yes-votes. */
function renderTopicEnd(topic, end, side) {
  const votes = topic.ends?.[end] || [];
  if (!votes.length) return `<div class="end"><p class="note">No anchoring votes.</p></div>`;
  const shares = (vote) =>
    [
      [topic.low_group, vote.low_group_for],
      [topic.high_group, vote.high_group_for],
    ]
      .filter(([group, share]) => group && share != null)
      .map(([group, share]) => `${escape(groupLabel(group))} ${pct(share)} for`)
      .join(" · ");
  return `<div class="end">
    <h3>Voting <em>for</em> these puts a member at the ${side}</h3>
    <ol>${votes
      .map(
        (v) => `<li><a href="${v.source}">${escape(v.title)}</a>${
          v.shared_with_other_end ? ` <span class="badge">also at the other end</span>` : ""
        }
          <span class="subject">${v.date}${shares(v) ? ` — ${shares(v)}` : ""}</span></li>`
      )
      .join("")}</ol></div>`;
}

// ---------------------------------------------------------------- one member

async function renderMember(id) {
  const member = await load(`members/${encodeURIComponent(id)}.json`).catch(() => null);
  if (!member) {
    $("member-head").innerHTML = `<p class="note">No published profile for that member.</p>`;
    $("member-terms").innerHTML = "";
    return;
  }
  const name = `${member.first_name || ""} ${member.last_name}`.trim();
  $("member-head").innerHTML = `<div class="member-head">
    <img src="${member.photo_url}" alt="" loading="lazy">
    <div>
      <h1>${escape(name)}</h1>
      <p class="meta">${escape(member.country_code || "")}${
        member.constituency ? ` · ${escape(member.constituency)}` : ""
      }</p>
      <p class="note"><a href="${member.ep_url}">Profile at the European Parliament →</a></p>
    </div></div>`;

  const terms = Object.keys(member.record).map(Number).sort((a, b) => b - a);
  $("member-terms").innerHTML = terms
    .map((term) => {
      const r = member.record[String(term)];
      const participation = r.participation == null
        ? `<span class="stat"><b>—</b><span>participation not recorded for this term</span></span>`
        : `<span class="stat"><b>${pct(r.participation)}</b><span>took part in ${num(
            r.votes_eligible
          )} roll-call votes</span></span>`;
      return `<section class="term-block">
        <h2>${termLabel(term)} — ${escape(groupLabel(r.group_code))}</h2>
        <div class="stats">
          ${participation}
          <span class="stat"><b>${pct(r.loyalty)}</b><span>voted with their group,
            over ${num(r.votes_cast)} votes</span></span>
          <span class="stat"><b>${pct(r.main_loyalty)}</b><span>${
            r.main_votes_cast == null
              ? "substantive votes not identifiable this term"
              : `on ${num(r.main_votes_cast)} substantive votes`
          }</span></span>
        </div>
        ${renderDivergence(r)}
      </section>`;
    })
    .join("");
}

/** Themes where this member broke with their group markedly more than they usually do.
 *
 * Shown against their own baseline rather than in the absolute: a member who follows
 * their group 95% of the time diverging on a fifth of one theme's votes is saying
 * something; a habitual rebel doing the same is not. */
function renderDivergence(record) {
  if (!record.divergence?.length) {
    return `<p class="note">No theme where they broke with their group notably more
      than usual, at ${num(20)} votes or more.</p>`;
  }
  return `<div class="divergence">
    <h3>Where they part company with their group</h3>
    <ul>${record.divergence
      .map(
        (d) => `<li><a href="#/topic/${encodeURIComponent(d.code)}">${escape(d.label)}</a>
          — voted against their group on <b>${pct(d.rate)}</b> of ${num(d.votes)} votes
          <span class="compare">(they usually do on ${pct(d.baseline)})</span></li>`
      )
      .join("")}</ul></div>`;
}

// ---------------------------------------------------------------- one topic

async function renderTopic(code) {
  if (!state.topicDetail) state.topicDetail = await load("topics-detail.json").catch(() => []);
  const theme = state.topicDetail.find((t) => t.code === code || t.label === code);
  if (!theme) {
    $("topic-title").textContent = "Unknown theme";
    $("topic-summary").textContent = "";
    return;
  }
  $("topic-title").textContent = theme.label;
  const terms = theme.terms.slice().sort((a, b) => a - b);
  const termText = terms.length === 1
    ? `the ${terms[0]}th term`
    : `the ${terms.slice(0, -1).join("th, ")}th and ${terms.at(-1)}th terms`;
  $("topic-summary").innerHTML =
    `${num(theme.votes)} verified roll-call votes between ${theme.first_vote} and
     ${theme.last_vote}, across ${termText}. Classified by Parliament, not by us.`;

  $("topic-groups").innerHTML = theme.groups
    .map(
      (g) => `<div class="support-row">
        <span class="name">${escape(groupLabel(g.code))}</span>
        <span class="bar"><i style="width:${(g.support * 100).toFixed(0)}%;
          background:rgb(${(GROUP_COLOUR[g.code] || FALLBACK).join(",")})"></i></span>
        <span class="value">${pct(g.support)}</span>
      </div>`
    )
    .join("") || `<p class="note">Too few votes per group to summarise.</p>`;

  $("topic-votes").innerHTML = `<table>
    <thead><tr><th>Date</th><th>Vote</th><th class="num">For</th><th class="num">Against</th></tr></thead>
    <tbody>${theme.recent
      .map(
        (v) => `<tr><td>${v.date}</td>
          <td><a href="${v.source}">${escape(v.title)}</a></td>
          <td class="num">${num(v.count_for)}</td><td class="num">${num(v.count_against)}</td></tr>`
      )
      .join("")}</tbody></table>`;

  await drawTopicCloud(theme);
}

/** Every vote as a point, with this theme's votes picked out of the crowd.
 *
 * Votes sit in the same frame as members, so a vote's position says how it divided the
 * chamber — not what it was about. Two votes on one theme can sit at opposite ends,
 * which is the point of showing the whole cloud behind them. */
async function drawTopicCloud(theme) {
  if (!state.cloud) state.cloud = await load("vote-cloud.json").catch(() => null);
  const wrap = $("topic-cloud-wrap");
  if (!state.cloud || !window.deck) {
    wrap.innerHTML = `<p class="note" style="padding:1rem">The vote cloud could not be loaded.</p>`;
    return;
  }
  const highlight = new Set(state.cloud.themes[theme.code] || []);
  const scale = 1200; // loadings are ~0.02; scale so the cloud fills the frame
  const points = state.cloud.votes.map((v, i) => ({
    id: v[0],
    position: [v[1] * scale, v[2] * scale, v[3] * scale],
    term: v[4],
    on: highlight.has(i),
  }));

  $("topic-cloud-caveat").textContent =
    `Every one of ${num(points.length)} verified votes, with the ${num(highlight.size)} on ` +
    `this theme picked out. A vote's place reflects how it split the chamber, not its ` +
    `subject — so votes on one theme scatter when members disagreed about them in ` +
    `different ways, and cluster when they divided the chamber alike.`;

  if (state.topicDeck) state.topicDeck.finalize();
  state.topicDeck = new deck.Deck({
    canvas: "topic-cloud",
    views: new deck.OrbitView({ orbitAxis: "Y", fovy: 50 }),
    initialViewState: { target: [0, 0, 0], rotationX: 20, rotationOrbit: 25, zoom: 3.4 },
    controller: true,
    layers: [
      new deck.PointCloudLayer({
        id: "all-votes",
        data: points.filter((p) => !p.on),
        coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
        getPosition: (d) => d.position,
        getColor: [175, 180, 188, 55],
        pointSize: 2,
      }),
      new deck.PointCloudLayer({
        id: "theme-votes",
        data: points.filter((p) => p.on),
        coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
        getPosition: (d) => d.position,
        getColor: [29, 78, 137, 235],
        pointSize: 4.5,
        pickable: true,
      }),
    ],
    getTooltip: ({ object }) =>
      object && {
        html: `${theme.label}<br>vote ${object.id} · ${object.term}th term`,
        style: { fontSize: "0.78rem" },
      },
  });
}

// ---------------------------------------------------------------- stories

const escape = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function formatFigure(figure) {
  if (figure.format === "percent") return pct(figure.value);
  if (figure.format === "count") return num(figure.value);
  return escape(figure.value);
}

// A deliberately small markdown subset. Anything richer would mean a dependency, and
// stories are written in-repo by the project rather than submitted by readers.
function renderProse(body, figures) {
  return escape(body)
    .split(/\n{2,}/)
    .map((block) => {
      const withFigures = block.replace(/\{\{([a-z0-9_]+)\}\}/g, (_, name) => {
        const figure = figures[name];
        if (!figure) return "—";
        // The tooltip carries what the number is counted over, so a reader can see the
        // basis of any figure without leaving the prose.
        return `<span class="figure" title="computed from ${escape(figure.basis)}">${formatFigure(figure)}</span>`;
      });
      const inline = withFigures
        .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
        .replace(/\[(.+?)\]\((https?:[^)]+)\)/g, '<a href="$2">$1</a>');
      if (inline.startsWith("## ")) return `<h2>${inline.slice(3)}</h2>`;
      return `<p>${inline.replace(/\n/g, " ")}</p>`;
    })
    .join("");
}

function renderStoryList() {
  if (!state.stories.length) {
    $("story-list").innerHTML = `<p class="note">No stories published yet.</p>`;
    return;
  }
  $("story-list").innerHTML = state.stories
    .map(
      (story) => `<button class="card story-card" data-slug="${story.slug}">
        <span class="who">${escape(story.title)}</span>
        <span class="meta">${escape(story.author)} · ${escape(story.date)}</span>
      </button>`
    )
    .join("");
  $("story-list").querySelectorAll(".card").forEach((card) =>
    card.addEventListener("click", () => showStory(card.dataset.slug))
  );
  if (state.stories.length === 1) showStory(state.stories[0].slug);
}

function showStory(slug) {
  const story = state.stories.find((s) => s.slug === slug);
  if (!story) return;
  const body = $("story-body");
  body.hidden = false;
  body.innerHTML = `
    <h2 style="margin-top:0;font-size:1.35rem">${escape(story.title)}</h2>
    <p class="byline">Written by <b>${escape(story.author)}</b> on ${escape(story.date)}.
      Figures in <span class="figure">this style</span> are computed from the verified
      record; the rest is argument.</p>
    ${renderProse(story.body, story.figures)}`;
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
  if (!state.axisVotes) {
    // A precomputed shortlist: ranking axes in the browser would mean downloading the
    // entire vote list for the term, which is megabytes for three short lists.
    state.axisVotes = await load("axis-votes.json").catch(() => []);
  }
  const rows = state.axisVotes.filter((v) => v.term === term);
  if (!rows.length) {
    $("axis-votes").innerHTML =
      `<p class="note">Axis coefficients are not present in this build of the published data.</p>`;
    return;
  }
  $("axis-votes").innerHTML = [1, 2, 3]
    .map((axis) => {
      const top = rows.filter((v) => v.axis === axis).slice(0, 5);
      return `<section><h3>Axis ${axis}</h3><ol>${top
        .map(
          (v) => `<li><a href="${v.source}">${escape(v.title || v.id)}</a>
            <br><span class="note">${v.date}</span></li>`
        )
        .join("")}</ol></section>`;
    })
    .join("");
}

boot();
