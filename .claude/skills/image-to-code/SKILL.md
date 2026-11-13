---
name: image-to-code
description: Turn a supplied screenshot or mockup into a responsive implementation that follows the target project's existing stack and components.
argument-hint: "<image or mockup and target screen>"
---

# Image to Code

Translate a reference image into a working interface in the current project. Treat the image as evidence of layout and visual intent; use the repository's existing components, design tokens, and interaction patterns for the implementation.

## Workflow

1. Confirm the selected reference, target screen, primary viewport, and expected interactions. Ask for the reference if none was supplied.
2. Inspect the relevant route, shared components, styles, and design tokens. Reuse established conventions before adding new ones.
3. Break the reference into regions: hierarchy, alignment, spacing, typography, color roles, imagery, controls, and responsive behavior. Record ambiguous details as assumptions.
4. Implement the smallest coherent change. Keep semantic HTML, keyboard access, visible focus, responsive layouts, and real application data/state behavior.
5. Render the screen at the reference viewport and compare it with the source. Check the main interaction and at least one narrower viewport when the layout is responsive.
6. Correct the largest visible mismatches before reporting completion. Do not claim a visual match based only on source code or a successful build.

## Constraints

- Preserve the project's architecture and avoid introducing a second component system.
- Do not invent content or product behavior that the reference does not establish; use existing product context or label assumptions.
- Use supplied assets when available. Do not recreate logos or branded illustrations from memory.
- Keep colors, spacing, and type decisions in existing tokens when possible; explain any new token.

## Handoff

Report the files changed, the reference and viewport used for comparison, verified interactions, remaining assumptions, and any visual differences that could not be resolved.