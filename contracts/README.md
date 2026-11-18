# Contracts — the seams

A **contract** is the JSON Schema every stage must satisfy before it may hand an
artifact to the next stage. Contracts are what make the stitch hold: modules can
be swapped, rewritten by a different model, or run by a different agent, and the
pipeline still works because nobody is allowed to pass raw prose through a seam.

## Rules

1. One artifact type = one schema file in this folder (`<artifact>.schema.json`).
2. A schema describes the **minimum** a downstream module needs. Extra keys are
   allowed (`additionalProperties: true`) so modules can carry richer evidence
   forward without breaking the seam.
3. Schemas are validated by `stitch validate` (structure and wiring) and by the
   Kiro hooks, which ask the agent to re-check an artifact whenever its schema or
   the producing module changes.
4. If a module needs data that no upstream artifact carries, the fix is to amend
   the upstream contract and its module — never to reach across the seam and read
   another module's internals.

## The nine artifacts

| Artifact | Produced by | Consumed by |
| --- | --- | --- |
| `brief` | `brief` | `site-plan`, `design-system`, `copy` |
| `site-plan` | `site-plan` | `design-system`, `copy`, `build`, `seo` |
| `design-tokens` | `design-system` | `build` |
| `page-content` | `copy` | `build`, `seo`, `a11y` |
| `build-manifest` | `build` | `seo`, `a11y`, `qa`, `deploy` |
| `seo-report` | `seo` | `qa` |
| `a11y-audit` | `a11y` | `qa` |
| `qa-report` | `qa` | `deploy` |
| `deploy-plan` | `deploy` | — (terminal artifact) |

## Reference artifacts

`examples/coffee-roastery/` shows a small raw request and the `.stitch/` layout a
dry run produces. `stitch run --dry-run` writes one prompt folder per stage and
prints the exact artifact path each module must fill.
