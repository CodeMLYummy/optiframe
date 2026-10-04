# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Field volunteer or technician** at a humanitarian clinic, fablab or health NGO (SN-SF context): measures donated or recycled lenses for a patient in front of them, without an optician's tracer.
- **Trained optical staff** (opticians, optometry students): fluent in A, B, PD and bridge; wants precise readouts and fast repetition.
- **Evaluators** (CodeML jury, INOVA demo in October 2026, SN-SF specialists in November 2026): open the app from a QR code on their own phone, set up the capture rig in under two minutes, photograph two real lenses, compare A and B to caliper values, and download the STL.

The interface must work for the volunteer without hiding the precision the trained user expects.

## Product Purpose

From one photo of a recycled lens on a printed reference sheet, measure its shape to the millimetre and generate a 3D-printable frame front whose rims fit each lens, even when the left and right lenses differ. It replaces an expensive lens tracer with a phone and a sheet of paper.

Success: A and B within 1 mm of caliper (target 0.5 mm), a valid closed STL, and a flow a first-time user finishes on a phone without help.

## Positioning

Measurement-first: a printed ChArUco/ArUco sheet gives scale and perspective correction, a trained segmentation model traces the transparent lens, and the frame is generated lens by lens in the browser. Every result is checkable: control images, 1:1 SVG contour to lay the real lens on, take-to-take coherence, and contour-versus-rim overlay.

## Operating Context

- Phone in one hand, at a table: printed sheet on a lit surface (window, laptop screen as light box), lens convex side up, nasal side toward the frame centre.
- Flow: print sheet (Letter or A4) and calibrate print scale, photograph right lens, then left lens, enter PD (total or per eye) or use the standard 18 mm bridge, generate frame, download `monture.stl` and `branches.stl`.
- Optional: second take per lens for coherence, contour/rim fit check, face try-on (on-device MediaPipe, no upload), step-by-step control images.
- Weak connectivity is plausible; installable PWA.

## Capabilities and Constraints

- Angular 22 PWA (`frontend/`), Spring Boot measurement API (`POST /api/measure`), ONNX U-Net segmentation.
- Mobile first: usable one-handed on Chrome Android and Safari iOS, ~6-inch screen; camera built in with file-import fallback; HTTPS.
- No account, no install, no API key; opens from a QR code.
- Clear, non-technical error messages for missing sheet, blur, misplaced lens.
- Languages: French (reference), English, Spanish; RTL-ready.
- Terminology: A (width), B (height), périmètre, PD (écart pupillaire), pont (bridge), OD/OG, boxing system (ISO 8624).

## Brand Commitments

- Name: OptiFrame. Tagline: "Du verre recyclé à la monture imprimée en 3D".
- Voice: plain, instructive French; tells the user what to do next rather than what went wrong technically.

## Evidence on Hand

- Validation results in `docs/validation.md`; caliper references for test lenses.
- Printable sheets in `frontend/public/` (Letter, A4, ChArUco).
- No testimonials, customers or deployment numbers exist; do not invent any.

## Product Principles

1. Every number is checkable: show how a measurement was obtained and let the user verify it against the real object.
2. One clear next action per moment; the guided path never strands a first-time user.
3. Precision is visible but never noisy: millimetre values are primary, diagnostics are one tap away.
4. Works in the field: one hand, bad light, weak network, any of three languages.
5. Privacy by default: face images stay on the phone.

## Accessibility & Inclusion

- WCAG AA contrast in both light and dark themes; 44 px minimum touch targets; respects reduced motion.
- Multilingual (fr, en, es) with locale number formatting.
