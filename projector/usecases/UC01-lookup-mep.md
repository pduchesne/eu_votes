---
id: UC01-lookup-mep
title: Look Up MEP Voting Record
keywords: [mep, search, voting record, attendance, cohesion]
scenario: SC01-citizen-looks-up-mep
priority: 1
requires:
  - CMP-PUBLISH
  - CMP-UI
  - IF-PUBLISHED-DATA
  - FR03-term8-parity
---
# UC01 — Look Up MEP Voting Record

A citizen searches for an MEP by name or constituency and views their voting record:
votes cast, attendance rate, and how closely they align with their political group.

## Standing out (added 2026-09-27)
Both a member's page and a group's page name the five subjects where they sit furthest
from where they usually sit, each drawn as a horizontal bar against the field they are
being judged against: the chamber's span, the comparison group's middle half, and their
own mark.

The baseline is the whole design. Two wrong versions were built and discarded first:

- **Distance from the chamber**, for a member. This is very largely a restatement of
  which group they joined, and hands every member of a group the same five subjects.
  Distance from the people they normally vote with is the part that is about them.
- **Raw distance from the other groups**, for a group. A group at one end of the
  chamber's main division is at that end on nearly every subject, so this returned five
  ways of saying "ECR is right-wing" — its top five all sat at z ≈ −1.1 and all pointed
  the same way, and the ranking between them was noise.

Both now rank by departure from the entity's *own* average position, scaled by its own
spread across subjects. That scaling matters: a group is compared against eight or nine
peers and a member against several hundred, so a fixed threshold in standard deviations
would mean two different things on the two pages. With it, ECR's 10th-term page leads
with Enlargement of the Union — where it sits nearer the Greens than it ever normally
does — instead of repeating its own general position five times.

This is deliberately a different question from the existing divergence list, which counts
ballots cast against the group majority. A member can follow their group on every
division and still sit at its edge, and the reverse.

A group page did not exist before this and was added: size, cohesion, and those bars,
reachable from the landscape legend, a member's page, and a theme page.
