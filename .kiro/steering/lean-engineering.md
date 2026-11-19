# Lean Engineering Steering

This file is Stitchcraft's own summary of the "Ponytail" necessity-first
approach to implementation. Inspired by
[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)
(MIT, Copyright (c) 2026 DietrichGebert); no upstream text or code is copied
here. It applies to changes to this repository, not to the sites generated for
users.

## Read before writing

Understand the task and the surrounding code first. Read the contract, the
module or theme involved, and the tests that already cover it. "Lazy" means the
smallest correct solution, never a shallow reading of the problem.

## The necessity ladder

Before adding code, libraries or abstractions, stop at the first rung that
works:

1. Does the behaviour already exist — maybe partially, behind a flag?
2. Is there an existing module, helper or theme block to reuse?
3. Does the Python standard library or the browser already provide it?
4. Can the platform (HTTP server, SQLite, JSON Schema, CSS, native HTML) do it?
5. Can an already-installed dependency do it?
6. Can the same behaviour be expressed in a small, readable amount of code?
7. Only then write the minimal implementation.

Do not add a dependency, wrapper, abstraction layer, configuration knob or file
just to make the diff look "complete".

## Never trade these away

- Input validation, trust boundaries and secret handling.
- Error handling that prevents data loss or silent corruption.
- Accessibility (labels, focus, contrast, reduced motion) and keyboard use.
- Tests for the seam, contract or behaviour that changed.
- License, attribution and provenance records for third-party material.
- The contracts and validators: never weaken a check to silence it.

## Intentional shortcuts

When a deliberately simple choice has a known ceiling, make it visible with a
`lean:` comment that names the ceiling and the upgrade path, for example:

```python
# lean: linear scan is fine for the tens of themes we ship; index by id if the
# registry grows to hundreds.
```

Reward the removal of dead or speculative code as much as the addition of a
feature. When two solutions are equally correct, prefer the one with fewer
moving parts.

## Stitchcraft constraints

- The backend stays Python 3.11+ standard library only; no runtime dependency
  unless the repository owner explicitly chooses an optional sidecar.
- Optional tools (browser runtimes, test harnesses) are downloaded or configured
  by the user, never silently required.
- Generated sites stay offline-first: no CDN, no framework, no new npm package;
  use the vendored `vendor/<id>/` libraries the theme declares.
- Prefer existing modules, themes, skills and tests over new layers.
- If a new layer is genuinely needed, add the contract, the tests and the docs
  in the same change.
