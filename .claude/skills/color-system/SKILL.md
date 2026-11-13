---
name: color-system
description: Build or review an interface color system with clear semantic roles, coherent palettes, measurable contrast, and support for CRM states and themes.
argument-hint: "<palette, screen, or token system>"
---

# Color System

Create color choices that support hierarchy, meaning, brand expression, and accessibility. Prefer a small, role-based palette over isolated decorative values.

## Design method

1. Identify the product context, users, brand constraints, surfaces, and supported themes.
2. Choose a restrained base palette. Consider hue relationships, warm/cool balance, saturation, and lightness/value; use these as design tools, not substitutes for testing.
3. Define semantic tokens such as `text-primary`, `surface-raised`, `border-muted`, `action-primary`, `focus-ring`, and status roles. Map raw palette values to roles instead of scattering hex codes through components.
4. Check each foreground/background pair at its actual size and weight. Measure text and UI contrast against the selected accessibility target; adjust the pair rather than relying on intuition.
5. Verify states for hover, focus, selected, disabled, success, warning, and error. Do not encode meaning by color alone; pair it with labels, icons, or shape.
6. Review the palette in real screens, including dense tables and charts. Check that adjacent statuses remain distinguishable and that emphasis does not overwhelm task hierarchy.
7. Document token names, values, intended use, contrast evidence, and theme mapping.

## Output

Provide the palette with role names and values, examples of intended use, measured contrast results for important pairs, state/theme coverage, and any tradeoffs. Flag untested combinations instead of calling them accessible.