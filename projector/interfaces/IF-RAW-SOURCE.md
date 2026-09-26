---
id: IF-RAW-SOURCE
title: EP Raw Data Source
status: provided
required: true
---
# IF-RAW-SOURCE — EP Raw Data Source

### Purpose
The external, third-party source of raw MEP and vote data that `CMP-FETCH` pulls
from. To be documented explicitly (exact source, endpoint/dump format, and access
method) as part of implementing CMP-FETCH, since the current pipeline has no
documented source at all — dumps simply appear in `tmp/`.

### Key capabilities / Conformance classes
- Provides MEP roster/profile data.
- Provides per-vote roll-call results (For/Against/Abstain per MEP).

### Key endpoints
To be confirmed during CMP-FETCH implementation.
