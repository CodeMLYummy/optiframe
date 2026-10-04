---
version: 1
slug: 'frontend-src-app'
primary_target: 'frontend/src/app'
related_targets: []
---

# OptiFrame app shell and guided flow

Scope: the whole mobile web app (`frontend/src/app`): welcome, guided steps (sheet, right lens, left lens, frame, files), optional side steps (fit check, face try-on, control images). Mode: Operate.

Audience and job: field volunteer or trained optical staff, phone in one hand at a table, measuring two recycled lenses and leaving with printable STL and a 1:1 SVG. Jury runs the same path from a QR code.

Constraints: light and dark themes following system with a user override; fr/en/es; 44 px targets; drawn icons (Lucide, ISC), no emoji; one primary action per step pinned to the thumb zone.

## Direction contract

THESIS: The flow is read like an acuity chart: one line at a time, the current line underlined in red, the lines above already read. Refuses the generic card-stack wizard with a blue progress bar.

OWN-WORLD: Backlit chart panel (near-white, faint warm) on a steel-grey wall; optotype-black ink; steel hairlines; Snellen red line marks the current step, Snellen green marks a verified result. Dark theme is the dimmed exam room: near-black wall, the panel glows softly. Archivo variable: expanded width for step titles and measurement numerals, normal width for body; tabular figures everywhere a number lives.

STORY: The user sees the whole procedure as a five-line chart, starts at line 1, and each step tells them exactly what to do next; measurements are big, checkable, and framed by registration corners like the printed sheet.

FIRST VIEWPORT: Welcome screen is the chart itself: five step names in decreasing size on a lit panel, line numbers in the left margin, red rule under line 1, short "what you need" list, full-width black Start button at the bottom. In-flow screens: steel top bar (brand, language, theme), compact ladder of five bars with the current one red, step title in expanded type, content, sticky Back + Continue bar.

FORM: Chart Room (ETDRS backlit acuity chart), candidate 6 of the grounded list; seed key cd3c8cd4. Raises: tabular digit cells (split-flap), registration-corner framing (plate section), one ink owns the active step (transit), fixed OD/OG name plates (character catalog). Signature interaction: on advancing, the finished line dims and the red rule slides to the next line.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
