---
name: design-qa
description: Compare a rendered interface with its approved design and report evidence-based visual, interaction, responsive, and accessibility issues before handoff.
argument-hint: "<design source and rendered screen>"
---

# Design QA

Review the implementation against the actual approved reference. This is a verification pass for a specific screen or flow, not an open-ended redesign.

## Required evidence

Use both the design source and the rendered implementation. Capture them at matching viewport dimensions and comparable application state. If one is unavailable, report the review as incomplete and name what is missing.

## Review sequence

1. Confirm the target route, source design, viewport, state, and supported browser/device sizes.
2. Compare hierarchy, geometry, spacing, typography, colors, assets, and component states using visible evidence.
3. Exercise the primary action, keyboard navigation, focus visibility, and relevant loading, empty, error, or success states.
4. Check narrow layouts and zoom/reflow where they apply. Review text alternatives, labels, contrast, and non-color status cues.
5. Report actionable findings in priority order. Recheck the same viewport and state after fixes.

## Finding format

For each finding include: location, observed behavior or visual difference, reference evidence, user impact, severity (blocker/high/medium/low), and a concrete correction. Separate verified defects from subjective suggestions.

## Completion

State which evidence was reviewed, what was exercised, what remains unresolved, and whether the screen is ready for handoff. Never infer a pass from compilation, lint, screenshots from different viewports, or code inspection alone.