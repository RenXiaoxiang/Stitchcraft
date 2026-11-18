# Kiroween 2026 — submission compliance checklist

**Project:** Stitchcraft — one skeleton, any site  
**Primary category:** Skeleton Crew  
**Secondary flavour:** Frankenstein (Kiro + Chrome Modern Web Guidance + GSAP skills + a user-supplied AI model)  
**Visual flavour:** Costume Contest (Kiroween-styled studio UI)  
**Deadline:** **4 December 2026, 2:00 PM PT** — 5 December 2026, 6:00 AM Beijing time  
**Submission surface:** Devpost

## Status key

| Status | Meaning |
| --- | --- |
| **READY** | The evidence exists in the repository. Re-check it on the submitted revision. |
| **VERIFY** | The evidence exists, but a final manual or remote check is required. |
| **ACTION** | An owner action is still required (deployment, recording, Devpost form, confirmation). |
| **CONFIRM** | The repository cannot prove it. The author must confirm it against the official rules. |

## Compliance matrix

| Requirement | Status | Evidence | Action |
| --- | --- | --- | --- |
| Public repository | **READY** | <https://github.com/RenXiaoxiang/Stitchcraft> — linked from `README.md`, `hackathon/submission.md` and `docs/index.html` | Open the repository URL in a private/incognito window while signed out. Confirm it loads without a login. |
| Detectable open-source license (MIT) | **READY** | [`LICENSE`](../LICENSE) is the MIT text; `pyproject.toml` declares `license = { text = "MIT" }`; [`README.md`](../README.md) links the license | Keep `LICENSE` at the repository root. Do not replace it with an “all rights reserved” notice. |
| MIT license visible in GitHub “About” | **VERIFY** | The repository contains a detectable MIT license, but the GitHub sidebar setting is remote metadata and is not stored in this repo | In GitHub: repository **About → Edit** → set **License: MIT**, then confirm the sidebar shows “MIT license”. |
| Root `/.kiro` present and **not** gitignored | **READY** | 16 files under [`.kiro/`](../.kiro): 3 steering files, 2 specs (requirements/design/tasks), 7 hooks. [`.gitignore`](../.gitignore) contains no `.kiro` rule | Confirm `.kiro/` appears in the GitHub tree after the final push. Run `grep -n '\.kiro' .gitignore` and expect no output (or no ignore rule). |
| Working public application/showcase URL | **ACTION** | The Pages source is [`docs/index.html`](../docs/index.html). The intended URL is <https://renxiaoxiang.github.io/Stitchcraft/>; when checked on 19 Nov 2026 it returned **HTTP 404** | Push `docs/`, enable **Pages → Deploy from a branch → `main` / `/docs`**, wait for the Pages build, then verify the URL in a private window. Test on a phone-width viewport. |
| Two demo sites prove the one-skeleton claim | **READY** | `docs/demo/warehouse/index.html` (Ember &amp; Bean Fulfilment) and `docs/demo/personal-space/index.html` (Notes from the attic) are exported, static and linked from the showcase. Theme sources live under `themes/warehouse-ops/` and `themes/personal-space/` | Open both links from the deployed Pages URL and click through the inventory and note interactions. A 404 on the Skeleton Crew evidence is a serious presentation problem. |
| Required text description | **READY** | [`hackathon/submission.md`](submission.md) — title, tagline, category, inspiration, what it does, how it was built, challenges, Kiro summary and links | Paste the body into Devpost. Keep the title/tagline/category fields in sync with `submission.md`. |
| Public YouTube video, **under 3 minutes** | **ACTION** | [`hackathon/video-script.md`](video-script.md) is a shot-by-shot 2:45 storyboard with a hard 3:00 cap | Record, edit to **2:45–2:55**, upload to YouTube as **Public**, confirm playback signed out, then replace the video placeholder in `submission.md` and this checklist with the URL. |
| Write-up on Kiro usage | **VERIFY** | [`hackathon/kiro-usage.md`](kiro-usage.md) — capability map, five-minute verification path, spec-driven loop, hooks and author-attestation section | Replace every `[author: ...]` placeholder in the attribution table. Re-run the five-minute verification on the submitted revision. |
| Third-party trademark / license notes | **VERIFY** | [`skills/ATTRIBUTION.md`](../skills/ATTRIBUTION.md) records Apache-2.0 for GoogleChrome/modern-web-guidance, MIT for the GSAP and web-animation skill packs, the GSAP standard license for the browser build, and explicit trademark notes for GSAP/Google/Kiro | Do not add third-party logos or imply endorsement. If the official rules require written permission for a mark, obtain it and keep the confirmation with the submission materials. |
| Project built during the submission window | **CONFIRM** | Stitchcraft is presented as a new Kiroween 2026 project. Application files do not carry a verifiable creation date or authorship record | The author confirms the project was created within the submission window and that the repository history supports it. Do not claim a start date you cannot verify. |
| Entrant eligibility | **CONFIRM** | No eligibility attestation is stored in the repository | Read the official Devpost rules and confirm age, residence, employment/affiliation restrictions, team/individual status and eligibility for the selected categories. Keep the confirmation with the submission. |
| Primary category: Skeleton Crew | **READY** | The nine-stage skeleton is shared by the warehouse (`themes/warehouse-ops/`) and personal (`themes/personal-space/`) applications; the category is stated in `submission.md` | Select **Skeleton Crew** as the primary category on Devpost. Use the two demo links as the proof. |
| Secondary flavour: Frankenstein / Costume Contest | **READY** | `skills/` (three vendored packs + attribution), `.kiro/` (Kiro governance), `app/web/` (Kiroween visual system) and the generated sites | If Devpost offers only one category, keep Skeleton Crew primary and mention the Frankenstein/Costume Contest elements in the description. Do not invent a category the platform does not offer. |
| Devpost project fields | **ACTION** | Field-by-field map below; long description in `submission.md` | Fill every required field, add the final video URL and Pages URL, upload a thumbnail, and preview the public project page before submitting. |
| Deadline and buffer | **ACTION** | Deadline above. Existing kit recommends leaving time for Pages and YouTube processing | Submit at least **24 hours before** the deadline if possible; YouTube processing and Pages deployment can lag. |

## Devpost field map

| Devpost field | Use | Status |
| --- | --- | --- |
| Project name | **Stitchcraft — one skeleton, any site** | READY |
| Tagline | **One skeleton, any site. AI stitches nine skills.** (49 characters) | READY |
| Primary category | **Skeleton Crew** | READY |
| Repository URL | `https://github.com/RenXiaoxiang/Stitchcraft` | READY |
| “Try it out” / demo URL | `https://renxiaoxiang.github.io/Stitchcraft/` once Pages is live | ACTION |
| Video URL | Public YouTube URL; replace the placeholder in `submission.md` and this file | ACTION |
| Built with | Python, Kiro, HTML, CSS, JavaScript, GSAP, SQLite, OpenAI-compatible APIs | READY |
| Long description | Body of [`hackathon/submission.md`](submission.md) | READY |
| Kiro usage | [`hackathon/kiro-usage.md`](kiro-usage.md), placeholders filled | VERIFY |
| Thumbnail / screenshot | Use the real studio screenshot at `docs/assets/app.png` (1440×960) or a demo image from `docs/assets/` | READY |
| Public GitHub repo | Confirm Public, MIT license visible in About, `.kiro` visible | VERIFY |

## Judging alignment

| Criterion | What the judge should see | Where to point them |
| --- | --- | --- |
| **Potential Impact** | A solo builder with their own AI endpoint can produce a complete, exportable site without a hosted account; one skeleton serves both a data-heavy operations app and an editorial personal site. | `hackathon/submission.md`; the two demos; `README.md`. |
| **Technological Implementation** | Nine contract-checked stages, a dependency-free Python core, a local HTTP studio, SQLite projects, safe generated-file writes, mock/AI parity, vendored skill packs and seven Kiro hooks. | `.kiro/`, `contracts/`, `modules/`, `pipeline/`, `src/stitchcraft/`, `tests/`, CI. |
| **Design** | One Kiroween visual system across the studio and showcase; five theme packages; reduced-motion support and accessible UI states. | `app/web/`, `themes/`, `docs/showcase.css`, generated demo sites. |
| **Innovation / Idea** | The Skeleton Crew premise is literal: one block vocabulary and one data layer dressed as two unrelated applications, with the seams exposed as artifacts. | `hackathon/submission.md` (“Two sites, one skeleton”); `docs/index.html`. |
| **Presentation** | A clear 2:45 demo, a scan-friendly submission, a working Pages showcase, honest Kiro evidence and no unverifiable metrics. | `video-script.md`, `submission.md`, `kiro-usage.md`, Pages URL. |

## Final submission checklist

Complete these in order. Do not start recording until the repository gate is
green.

- [ ] **1. Run the definition of done on the submission revision.**
      `python -m unittest discover -s tests -v`,
      `python -m stitchcraft validate --strict`,
      `python -m stitchcraft plan`,
      `PYTHONPATH=src python -m stitchcraft app --smoke-test --no-window`.
      All must pass; record the exact commands and outputs for your own log.
- [ ] **2. Fill the author placeholders in `hackathon/kiro-usage.md`.** Remove
      every `[author: ...]` marker and replace it with a specific, checkable
      statement. If something was done outside Kiro, say so.
- [ ] **3. Check the remote repository as a signed-out visitor.** Public repo,
      MIT license visible in About, `.kiro/` visible in the tree, `LICENSE` and
      `skills/ATTRIBUTION.md` opening correctly.
- [ ] **4. Deploy the Pages showcase.** Push the final `docs/`, set Pages to
      `main` / `/docs`, wait for the build, and verify the root URL, both demo
      links, `showcase.css`, `showcase.js` and the screenshot assets.
- [ ] **5. Check the demo and screenshot set.** The two exports live under
      `docs/demo/` and the screenshots under `docs/assets/`. Re-capture
      `app.png` if the studio UI changes after recording, and confirm both demo
      links still work from the deployed Pages URL.
- [ ] **6. Record and publish the video.** Follow `video-script.md`, keep the
      final file below 3:00 (target 2:45–2:55), upload as **Public**, and check
      it signed out on a phone. Paste the URL into `hackathon/submission.md` and
      the Devpost field map above.
- [ ] **7. Paste the Devpost story.** Use `submission.md`; update the title,
      tagline, category, repo, demo URL, video URL, built-with tags and
      thumbnail. Preview the public page.
- [ ] **8. Confirm the two attestations.** New project within the submission
      window; entrant eligibility under the official rules.
- [ ] **9. Do the trademark review.** Confirm the attribution notes are intact
      and no third-party logos or implied endorsements were added.
- [ ] **10. Submit with buffer.** Target at least 24 hours before
      **4 Dec 2026, 2:00 PM PT**. Save the Devpost confirmation, public project
      URL, video URL and a zip/snapshot of the submitted repository revision.

## Known gaps and owner actions

These are the items that cannot be closed by editing a source file alone. They
must be handled by the author before the Devpost entry is final.

| Gap | Why it matters | Owner action |
| --- | --- | --- |
| Public YouTube video URL is still a placeholder | Required submission field; no Devpost entry is complete without it | Record, publish as Public, verify under 3:00, paste the URL into `submission.md` and the Devpost field map. **User action.** |
| Devpost submission is not complete | The hackathon entry lives on Devpost, not in this repository | Fill all fields, preview, submit, and save the confirmation. **User action.** |
| GitHub Pages URL | **Resolved** — Pages enabled from `main` + `/docs`; build succeeded and the showcase, screenshots and both demo sites return HTTP 200 (`https://renxiaoxiang.github.io/Stitchcraft/`) | Re-verify after any future docs change. **Verified.** |
| Kiro write-up contains author placeholders | Unfilled placeholders are not submittable and an unsupported “Kiro did everything” claim is worse | Complete the attestation table. **Author action.** |
| GitHub About license is remote metadata | “Detectable license in About” is a separate check from having `LICENSE` in the tree | Verify on GitHub; the API reports `license: MIT` (`LICENSE`). **Verified.** |
| Warehouse demo name drift | Resolved in this revision | Demo, screenshots and narrative now consistently use “Ember &amp; Bean Fulfilment”; re-check the video script captions while recording.**Resolved.** |
| Eligibility and submission-window attestations are not in the repo | The repository cannot prove entrant eligibility or project start date | Confirm both against the official rules and keep the evidence. **Author action.** |

**Not a gap:** the seven Kiro hooks, both spec folders and the third-party
attribution file are present in the repository. Do not list them as planned or
missing in the submission narrative.
