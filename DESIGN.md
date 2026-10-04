---
name: OptiFrame
description: Du verre recyclé à la monture imprimée en 3D. A guided measuring flow read like a backlit acuity chart.
colors:
  wall: '#dfe3e7'
  panel: '#fbfbf8'
  panel-2: '#f0f1ed'
  ink: '#121416'
  ink-2: '#4b5258'
  ink-3: '#686f76'
  steel: '#9aa0a5'
  rule: '#d8dbd5'
  snellen-red: '#bd3329'
  snellen-green: '#1b7244'
  amber: '#8a5300'
  on-ink: '#fbfbf8'
  wall-dark: '#0b0d0e'
  panel-dark: '#17191b'
  panel-2-dark: '#212427'
  ink-dark: '#eceee9'
  ink-2-dark: '#b1b6bb'
  ink-3-dark: '#8d949a'
  steel-dark: '#50565c'
  rule-dark: '#2c3034'
  snellen-red-dark: '#ff6b5d'
  snellen-green-dark: '#5ccb8d'
  amber-dark: '#f0b14d'
  on-ink-dark: '#121416'
typography:
  display:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: 'clamp(2rem, 1.2rem + 4vw, 2.7rem)'
    fontWeight: 750
    lineHeight: 1
    letterSpacing: '0.05em'
    fontVariation: "'wdth' 125"
  numeral:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: 'clamp(2rem, 0.8rem + 6vw, 3.4rem)'
    fontWeight: 650
    lineHeight: 0.95
    letterSpacing: '-0.02em'
    fontFeature: "'tnum' 1"
    fontVariation: "'wdth' 125"
  headline:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: 'clamp(1.6rem, 1.2rem + 2vw, 2.05rem)'
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: '-0.01em'
    fontVariation: "'wdth' 125"
  title:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: '1.05rem'
    fontWeight: 650
    lineHeight: 1.3
  body:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: '1rem'
    fontWeight: 400
    lineHeight: 1.5
  body-small:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: '0.875rem'
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "'Archivo Variable', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: '0.8rem'
    fontWeight: 700
    letterSpacing: '0.08em'
    fontVariation: "'wdth' 125"
rounded:
  plate: '4px'
  control: '8px'
  track: '12px'
  panel: '16px'
spacing:
  xs: '4px'
  sm: '8px'
  md: '12px'
  gutter: '18px'
  lg: '24px'
  xl: '28px'
  xxl: '40px'
components:
  button-primary:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.on-ink}'
    rounded: '{rounded.control}'
    padding: '0 18px'
    height: '48px'
  button-secondary:
    backgroundColor: 'transparent'
    textColor: '{colors.ink}'
    rounded: '{rounded.control}'
    padding: '0 18px'
    height: '48px'
  button-secondary-hover:
    backgroundColor: '{colors.panel-2}'
  button-square:
    rounded: '{rounded.control}'
    size: '48px'
  input-measure:
    backgroundColor: '{colors.panel-2}'
    textColor: '{colors.ink}'
    rounded: '{rounded.control}'
    padding: '0 52px 0 14px'
    height: '52px'
  segmented-track:
    backgroundColor: '{colors.panel-2}'
    rounded: '{rounded.track}'
    padding: '4px'
  segmented-option-selected:
    backgroundColor: '{colors.ink}'
    textColor: '{colors.on-ink}'
    rounded: '{rounded.control}'
    height: '44px'
  note:
    backgroundColor: '{colors.panel-2}'
    textColor: '{colors.ink}'
    rounded: '{rounded.control}'
    padding: '12px 14px'
  chart-panel:
    backgroundColor: '{colors.panel}'
    textColor: '{colors.ink}'
    rounded: '{rounded.panel}'
    padding: '28px 18px 0'
  name-plate:
    textColor: '{colors.ink}'
    rounded: '{rounded.plate}'
    height: '1.7em'
  verified-mark:
    textColor: '{colors.snellen-green}'
    typography: '{typography.body-small}'
---

# Design System: OptiFrame

## Overview

**Creative North Star: "The Chart Room"**

OptiFrame is read like a backlit acuity chart in an exam room. A lit, faintly warm panel sits on a cool steel wall; everything on it is printed in optotype-black ink; steel hairlines rule it into lines. The procedure is a five-line chart read one line at a time: the line being read is underlined in Snellen red, lines already read dim to grey, and a verified result is underlined in Snellen green. The dark theme is the same room with the lights down: a near-black wall and a panel that still glows.

Density is calm and one-handed. Each step owns one panel, one expanded-width title, one primary action pinned in a sticky bar at the thumb. Measurements are the loudest thing on any screen: big expanded tabular numerals framed by registration corners, the same corners printed on the reference sheet the user photographs. Archivo's width axis carries the hierarchy: expanded (125%) for step titles, chart lines, numerals and name plates; normal width for reading.

The system rejects the generic card-stack wizard with a blue progress bar. Progress is the chart ladder, not a bar; color is signal, not decoration.

**Key Characteristics:**

- Lit panel on a steel wall; one soft panel shadow, everything else flat and ruled by hairlines.
- Optotype-black ink as the only fill for primary actions and selected states.
- Snellen red marks where you are (and what is wrong); Snellen green marks what is verified.
- Expanded Archivo for titles and numbers; tabular figures wherever a number lives.
- Registration corners frame anything measured.
- Light and dark themes from one token set; system default with a remembered user override.

## Colors

A near-neutral room (cool wall, warm-white panel, blue-black ink) with three signal inks borrowed from the acuity chart and the clinic.

### Primary

- **Optotype Ink** (ink): the text color, the fill of the primary button and of a selected segmented option, and the focus outline. In dark theme it inverts to a warm off-white (ink-dark) and on-ink flips to black, so the primary button becomes a lit bar.

### Secondary

- **Snellen Red** (snellen-red): the current line. The sliding 3px rule under the active ladder step, the red rule under the current chart line on the welcome screen, the text caret, the selection tint (28% mix), and error states (invalid input border, error note tint at 10%, error icon).
- **Snellen Green** (snellen-green): a verified result only. The "verified" underline mark, ladder ticks on completed steps, ok icons.

### Tertiary

- **Clinic Amber** (amber): warnings only. Warn note tint (12% mix into the panel) and its icon.

### Neutral

- **Steel Wall** (wall): page background behind the panel; also drives the browser theme-color.
- **Lit Panel** (panel): the chart surface every step sits on, and the sticky action bar.
- **Panel Shade** (panel-2): recessed surfaces on the panel: inputs, segmented track, notes, viewfinder, row and button hover.
- **Ink 2** (ink-2): lead paragraphs, secondary text, read ladder lines, field labels, note icons.
- **Ink 3** (ink-3): tertiary text: units, line numbers, readout keys, registration corners, placeholders.
- **Steel** (steel): button borders and link underlines at rest.
- **Hairline** (rule): section dividers, row separators, input borders, the ladder baseline.

### Named Rules

**The One Red Line Rule.** Snellen red appears once per screen as the current-step rule, and otherwise only to flag an error. It is never a fill, a button, or decoration.

**The Green Means Checked Rule.** Snellen green is reserved for a result that has been measured or verified. Never use it for a generic success-looking button or accent.

**The Ink Owns Action Rule.** The only filled control is ink on panel (primary button, selected option). There is no brand-blue or accent-colored button.

## Typography

**Display Font:** Archivo Variable (self-hosted via @fontsource-variable/archivo, width axis), with system-ui fallback
**Body Font:** Archivo Variable at normal width

**Character:** One family, two widths. Expanded Archivo reads like chart optotypes and gauge numerals; normal-width Archivo carries instructions plainly.

### Hierarchy

- **Display** (750, clamp(2rem, 1.2rem + 4vw, 2.7rem), 1, expanded, 0.05em, uppercase): only the welcome chart lines, stepping down in five sizes to 0.92–1.05rem on line 5. Uppercase here is the optotype itself.
- **Numeral** (650, clamp(2rem, 0.8rem + 6vw, 3.4rem), 0.95, expanded, tabular): A and B measurement readouts; the largest type in any step.
- **Headline** (700, clamp(1.6rem, 1.2rem + 2vw, 2.05rem), 1.1, expanded, balanced wrap): one step title per page, optionally followed by an OD/OG name plate.
- **Title** (650, 1.05rem, 1.3): section headings inside a step, with an optional ink-3 ordinal for numbered sub-tasks.
- **Body** (400, 1rem, 1.5): instructions; leads in ink-2 capped at 52ch, prose at 60ch.
- **Body small** (400, 0.875rem, 1.45): captions, row descriptions, prompts, the verified mark.
- **Label** (700, 0.8rem, expanded, 0.08em): single-letter measurement keys (A, B) above numerals.
- Interface weights: buttons 600, fields and segmented options 550, top-bar brand 750 expanded at 1.1rem.

### Named Rules

**The Width Carries Rank Rule.** Hierarchy is expressed with Archivo's width axis plus size, not with extra families or colors. Expanded is for titles, chart lines, numerals and plates; body stays at normal width.

**The Tabular Everywhere Rule.** Every number (measurements, step numbers, ordinals, facts, input values) uses tabular figures.

## Layout

Mobile first, single column. A 60px top bar sits on the wall (brand mark and wordmark left; language select and theme toggle right). In flow, the ladder of five step numbers sits below it on the wall, numbers stepping down in size like chart lines (1.55rem to 0.88rem) over a hairline baseline, with a 20%-wide red rule that slides under the current number.

The panel is inset 8px from the screen edges, 18px internal gutter, top-rounded only, and fills the viewport height; the column caps at 680px. Each step stacks: step head (28px below), sections separated by hairlines with 24px vertical padding, then a sticky action bar flush to the panel bottom (hairline top, 12px padding plus safe-area inset) holding a 48px square Back button and a full-flex primary Continue. A single status prompt can sit above the buttons explaining why Continue is disabled.

At 960px and up, the ladder becomes the full chart in a sticky 260px side rail: each line 60px tall with a hairline, step names in expanded type stepping down from 1.5rem to 0.92rem, and the red rule becomes a 3px underline that slides vertically. The panel becomes fully rounded at 640px max with 40px/44px padding; the whole layout caps at 1040px with a 48px gap.

Spacing is a loose 4px-based rhythm (4, 8, 12, 14, 18, 24, 28, 40); touch targets are never below 44px, primary controls are 48px, measurement inputs 52px.

## Elevation & Depth

Flat by default, with one exception: the chart panel. Depth is the panel lifted off the wall; everything on the panel is separated by hairlines and the panel-2 recess, never by shadows. In dark theme the shadow turns into a glow: an inset hairline highlight, a faint cool light above, and a deep shadow below, so the panel reads as backlit.

### Shadow Vocabulary

- **Panel lift, light** (`box-shadow: 0 1px 2px rgb(18 20 22 / 0.05), 0 16px 40px -20px rgb(18 20 22 / 0.22)`): the chart panel only.
- **Panel glow, dark** (`box-shadow: 0 0 0 1px rgb(236 238 233 / 0.07) inset, 0 1px 0 rgb(236 238 233 / 0.1) inset, 0 -12px 60px -24px rgb(196 206 214 / 0.16), 0 28px 56px -28px rgb(0 0 0 / 0.8)`): the chart panel in dark theme.
- **Input focus ring** (`box-shadow: 0 0 0 1px var(--ink)`): doubles the ink border of a focused measurement input.

### Named Rules

**The One Lit Panel Rule.** Only the chart panel carries a shadow. Components on it are flat; separate them with hairlines (rule) or the panel-2 recess.

## Shapes

Gently rounded and mostly rectilinear. Controls, notes and inputs use 8px; the segmented track wraps its 8px options at 12px (radius + 4px); the chart panel uses 16px (top corners only on mobile). Small 4px corners belong to name plates and images inside registration frames. A filled area that carries registration corners itself (the empty photo slot) stays square, so its corner marks are never clipped. Borders are 1px hairlines, 1.5px for plates and registration corners, 2–3px only for the green verified line and the red current-step rule. Lists are open, ruled rows rather than boxed cards.

## Components

### Buttons

Quiet, outlined, ink-filled only for the one next action.

- **Shape:** gently rounded (8px), 48px tall, 18px horizontal padding, 10px icon gap, weight 600.
- **Primary:** ink fill, on-ink text, ink border; hover mixes 16% panel into the ink. One per step, in the sticky action bar or the welcome Start.
- **Secondary (default):** transparent with a steel 1px border; hover fills panel-2 and darkens the border to ink-3; active nudges down 1px.
- **Ghost / Square:** ghost drops the border (theme toggle); square is 48x48 for icon-only actions (Back).
- **Disabled:** 38% opacity, no pointer events.
- **Text button:** underlined ink text, steel underline at 4px offset, 44px tall hit area, weight 550.
- **Focus:** 2px ink outline, 2px offset, everywhere.

### Segmented Choice

- **Style:** a panel-2 track with a hairline border and 4px inset; options are 44px tall, ink-2 text at 550.
- **State:** the checked option fills with ink and on-ink text (0.2s ease). Built from real radio inputs.

### Inputs / Fields

- **Style:** 52px tall, panel-2 fill, hairline border, 8px radius, value at 1.2rem 550, slightly expanded (112%), tabular. Unit sits inside at the right in ink-3.
- **Hover / Focus:** border goes steel on hover; ink border plus 1px ink ring on focus.
- **Error:** border turns Snellen red. Labels above in ink-2 at 0.9rem 550.

### Notes

- **Style:** panel-2 recess, 8px radius, 12px/14px padding, 20px leading icon in ink-2, 0.95rem text.
- **Variants:** error tints the panel 10% red with a red icon; warn tints 12% amber with an amber icon; ok keeps the recess and turns the icon green.

### Navigation

- **Top bar:** on the wall, 60px; line-art spectacles mark (1.9 stroke) and wordmark at 1.1rem 750 expanded; language select shows the code in 650 with 0.04em tracking.
- **Ladder:** five expanded step numbers in decreasing size; read lines in ink-2 with a small green tick when done, the current in ink, open lines in ink-3 at 500, locked lines at 45% opacity. The red rule slides between lines (0.5s, the system ease).

### Measurement Readout (signature)

Keys (A, B) in the label style above expanded tabular numerals, a light "×" between, unit in ink-2 at 1.1rem; facts below (périmètre) in ink-2 with values in ink 600. The whole readout sits inside registration corners.

### Registration Frame (signature)

Four 14px by 1.5px corner brackets in ink-3 drawn around anything measured (readouts, control images, contours), 10px inset; images inside take 4px corners; captions in ink-2 at 0.875rem.

### Verified Mark (signature)

Green circle-check icon and 650 small text with a 2px green underline: the Snellen green line under a confirmed result.

### Name Plate (signature)

OD / OG in a 1.5px currentColor outline, 4px corners, half the parent size, expanded 700 with 0.06em tracking; fixed beside the lens step title.

### Rows

Open list of 64px rows ruled by hairlines: leading 22px ink-2 icon, title 600 and ink-2 description, trailing ink-3 icon; hover fills panel-2. Used for downloads and checks instead of cards.

### Icons

Lucide (ISC), inlined SVG, 24-unit viewBox, 1.75 stroke, currentColor, 1.25em by default (set per context via --icon-size: 18–22px). No emoji, no glyph icons.

### Motion

One ease, `cubic-bezier(0.22, 1, 0.36, 1)`: 0.15s for hover/border, 0.2s for selection, 0.3s for ladder color, 0.5s for the red rule slide. Step changes use a view transition: old step fades out in 160ms, new step rises 10px from a 2px blur in 320ms. Reduced motion removes all of it.

## Do's and Don'ts

### Do:

- **Do** put every step on the lit panel with one expanded headline, hairline-separated sections, and a sticky action bar holding Back (48px square) and one ink primary.
- **Do** frame every measurement or control image with registration corners and set its numbers in expanded tabular Archivo.
- **Do** use Snellen red only for the current-step rule and for errors, and Snellen green only for verified results.
- **Do** use panel-2 recesses and 1px hairlines to group content on the panel.
- **Do** keep touch targets at 44px minimum and primary controls at 48px.
- **Do** define every color through the theme tokens so light and dark (system, light, dark override) stay in step.
- **Do** use inlined Lucide icons at 1.75 stroke in currentColor.

### Don't:

- **Don't** build progress as a colored progress bar or a stack of cards; progress is the chart ladder with the sliding red rule.
- **Don't** add shadows to components on the panel; only the chart panel is lifted.
- **Don't** fill buttons or chips with red, green, amber or any brand hue; filled means ink.
- **Don't** introduce a second typeface or use proportional figures for numbers.
- **Don't** spread uppercase tracking beyond the welcome chart lines and OD/OG plates (no small-caps labels above headings).
- **Don't** use emoji or text glyphs as icons.
