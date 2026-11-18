---
name: deploy
description: Turn a passed release into a reproducible deploy plan with provider, environment, ordered steps, post-deploy checks and rollback.
---

# Ship It

## Job

Consume the release-gate verdict and the build manifest and produce the exact,
reproducible plan for publishing the site: provider, environment, ordered
commands, verification and rollback. This module plans the release; the operator
runs it.

## Inputs

- `qa-report` — `contracts/qa-report.schema.json`. Fields: `verdict`,
  `build.status`, `blockers[]`, `release_notes`.
- `build-manifest` — `contracts/build-manifest.schema.json`. Fields:
  `build.command`/`output`/`env`/`node_version`, `routes[].path`, `stack`.
- Domain, provider account and credentials are not carried by any consumed
  artifact; they arrive only as open questions, never as guesses.

## Outputs

- Artifact: `deploy-plan` at `.stitch/09-deploy/deploy-plan.json`; contract
  `contracts/deploy-plan.schema.json`.
- Non-negotiable fields: `target.provider`, `env[].key`/`source`,
  `steps[].order`/`command`/`verify`, `post_deploy_checks`,
  `rollback.trigger`/`steps`.

## Procedure

1. Read the QA verdict. If it is `fail`, stop and report; do not plan a deploy.
   If `conditional`, list accepted risks as open questions and proceed only when
   every residual blocker has an owner and none is `blocker` severity.
2. Choose `target.provider` from the enum (`cloudflare-pages`, `vercel`,
   `netlify`, `github-pages`, `self-hosted`) from `build-manifest.stack` and
   constraints, preferring the option that needs the fewest new secrets.
3. Fill `target.project`, `domain` and `preview_url` when known; unknown values
   become open questions, never invented domains.
4. Fill `env[]` from `build.build.env`: each `key` gets a `source` (`manual`,
   `repo-secret`, `provider-secret`, `generated`) and `secret: true` where
   appropriate. Record names and sources only, never secret values.
5. Write `steps[]` in execution order, each with an integer `order`, a
   non-interactive `command`, a `verify` check and a `rollback` instruction.
   Cover install, build, publish, smoke test and domain promotion; use
   repo-relative, version-pinned commands.
6. Fill `post_deploy_checks` an operator can run: every public route returns 200,
   home carries the expected title, TLS is valid, preview matches production.
7. Fill `rollback` with a concrete `trigger` and ordered `steps` (republish the
   previous build, revert DNS, disable deployment), each with a verified outcome.
8. Read the plan as the operator: if a step needs a question answered, record it
   in a top-level `open_questions` array (allowed by `additionalProperties`).
9. Write the JSON and run `python -m stitchcraft validate`.

## Quality bar

- `target.provider` is one of the five enum values and `target.project` is set.
- Every `env[].key` has a valid `source`; no field contains a secret value.
- `steps[].order` values are unique and ascending; every step has a `command`,
  and `build-manifest.build.command` appears verbatim in one step.
- `post_deploy_checks` covers every public route family, not just home.
- `rollback.trigger` and `rollback.steps` are present and actionable.
- `python -m stitchcraft validate` passes.

## Hand-off

- Save `.stitch/09-deploy/deploy-plan.json` and run `python -m stitchcraft validate`.
  This is the terminal artifact; nothing downstream consumes it.
- Hand the plan to the operator with the QA `verdict` and `release_notes`; a
  `conditional` verdict must travel with its accepted risks.
- The plan must be executable as written; fix unclear steps now rather than
  leaving questions for the operator.
- Missing domain, account or credentials go in `open_questions` for the operator.

## Failure modes

- **Deploying a `fail` verdict.** The gate exists for this; stop and report.
- **Secrets copied into the plan.** Record key and source only.
- **Local-only commands.** Absolute paths and interactive prompts break reproducibility.
- **No rollback.** Every production change needs a tested way back.
- **Domain invented.** A wrong domain breaks DNS, mail and TLS at once.
