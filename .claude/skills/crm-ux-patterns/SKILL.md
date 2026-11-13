---
name: crm-ux-patterns
description: Design CRM screens and workflows for dense operational work, including records, queues, search, filters, permissions, and follow-up actions.
argument-hint: "<CRM screen or workflow>"
---

# CRM UX Patterns

Design for people who move between many customer records and operational tasks. Make context, next action, and record identity easy to keep in view.

## Review the workflow

1. Identify the user's role, goal, record type, and decision they need to make.
2. Keep the primary action visible while preserving the information needed to choose it.
3. Make search, filters, sorting, pagination, and active filter state understandable and reversible.
4. For tables, prioritize scannable columns, stable row identity, meaningful empty/loading/error states, and keyboard-accessible row actions.
5. For record details, group information by task and keep history, ownership, status, and next steps easy to distinguish.
6. Show permission boundaries and destructive effects before actions. Confirm bulk changes with scope and consequences.
7. Preserve work across navigation where appropriate; do not lose unsaved edits or selection without a clear signal.
8. Test realistic cases: long names, missing data, many records, restricted access, stale data, and narrow windows.

## Output

Describe the task flow, information hierarchy, key states, permission-sensitive actions, accessibility needs, and evidence from the current product. Prefer patterns already established by the product unless a concrete user problem justifies a change.