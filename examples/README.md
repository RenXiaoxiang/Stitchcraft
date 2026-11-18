# Examples

Each example is a *seed*, not a checked-in generated site. They exist so a new
user can see the shape of the input the first module expects and can watch the
stitch plan render without inventing a brief.

- `coffee-roastery/request.md` — a realistic raw client request for a small
  specialty coffee roastery. Paste it into the Brief Intake stage (or let an
  agent read it) and the other eight modules follow.

Dry-run the pipeline to see the prompts each stage would receive:

```bash
stitch run --dry-run
```

Generated artifacts and prompts are written under `.stitch/` and are gitignored
on purpose: every build should be reproducible from the request plus the
skills in this repository, not from stale output.
