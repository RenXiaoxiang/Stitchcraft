---
name: brief
description: Turn a raw client request into a sealed brief with audience segments, measurable goals, brand constraints and explicit open questions.
---

# Brief Intake

## Job

Take the client's raw request, however thin, and seal it into a brief that every
later module can trust without ever talking to the client. Facts stay facts,
guesses become open questions, and no design, page plan or copy is produced here.

## Inputs

- **None: this is the entry module.** The raw request in the conversation is the
  only input: a message, a document, or a link the client supplied.
- Contract: `contracts/brief.schema.json`. Fields that matter most: `project`,
  `audience`, `goals`, `brand`, `constraints`, `non_goals`, `open_questions`.

## Outputs

- Artifact: `brief` at `.stitch/01-brief/brief.json`; contract
  `contracts/brief.schema.json`.
- Non-negotiable fields: `project.name`, `project.one_liner`, at least one
  `audience[].segment` with `needs`, `goals[].id` and `statement`, and
  `open_questions` whenever the request leaves anything material unresolved.

## Procedure

1. Read the request twice and separate explicit facts from assumptions. Each
   assumption either becomes a client fact or an entry in `open_questions`.
2. Name the project and write `project.one_liner` as one sentence naming the
   audience and outcome; keep it at least 8 characters and free of jargon.
3. Define one to three `audience` segments. Each needs a concrete `needs` list a
   later module can act on; "everyone" is not a segment. Prefer the client's own
   words for segment names.
4. Convert every stated objective into a `goals` entry with an `id` matching
   `^G[0-9]+$`, a measurable `statement`, and a `metric` where one genuinely
   exists. These ids are the spine the plan, copy and build modules use; number
   them from G1.
5. Capture `brand.tone`, `brand.constraints` and `brand.assets` only from
   evidence in the request. Unprovided visual assets are expectations, not facts
   you can supply.
6. Record `pages_hint` as a flat list of page names the client actually
   mentioned. Do not order pages, design navigation or infer a sitemap here.
7. Put `constraints` (budget, stack, timeline, legal) and `non_goals` in the
   brief; the non-goals stop later stages from adding scope.
8. Move every unanswered question, such as pricing, proof, legal copy, content
   ownership or domain, into `open_questions` with enough context to answer it.
9. Write the JSON and run `python -m stitchcraft validate`, then re-read the
   artifact as the site-plan module: can it choose pages from this alone?

## Quality bar

- `project.name` and `project.one_liner` are present and the one-liner names an
  audience plus an outcome.
- Every audience segment has at least one concrete need.
- Every goal id matches `^G[0-9]+$`, is unique, and its statement is testable.
- `pages_hint` contains only page names from the request and no invented IA.
- No invented brand, proof, price or legal fact; anything unknown appears in
  `open_questions`.
- `python -m stitchcraft validate` passes with no schema errors.

## Hand-off

- Save `.stitch/01-brief/brief.json`; it is the only source of client truth from
  this point on.
- Run `python -m stitchcraft validate` before the stage counts as complete.
- Downstream modules read `goals[].id`, `audience`, `brand.tone`, `constraints`,
  `non_goals` and `open_questions`; the site-plan module must map every goal to
  at least one page.
- If a downstream module needs a field the brief lacks, amend this contract and
  skill through the pipeline owner; never let it read the raw request.

## Failure modes

- **Vague request becomes a vague brief.** Ask up to five concrete questions and
  record the rest in `open_questions`; never invent audience or goals.
- **Brief turns into an IA or a design doc.** `pages_hint` is a list of names,
  not a sitemap; fonts, colors and copy belong to later modules.
- **Client predictions recorded as facts.** Put estimates in `constraints` or
  `open_questions`, not in `goals[].metric` or `project.one_liner`.
- **Open questions silently deleted.** An empty `open_questions` is fine only
  when the request is genuinely complete; otherwise the list is the deliverable.
- **Talking to the client again later.** Once sealed, later modules use this
  artifact; a missing field is a contract amendment, not a new interview.
