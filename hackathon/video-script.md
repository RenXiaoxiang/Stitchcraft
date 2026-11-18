# Stitchcraft — Kiroween 2026 demo video script

A shot-by-shot storyboard for the required public YouTube demo. **Hard limit:
under three minutes.** The planned cut lands at about **2:50**, and the narration
is deliberately sparse so the screen does the explaining.

- Format: 1920×1080, 30 fps, screen recording with voice-over. No face camera
  required.
- Narration: **under 500 spoken words**, paced at roughly 150 words per minute.
  The script below is about 400 words including the optional lines in brackets.
- Every caption is short enough to read in under two seconds.
- The recording can be assembled from several takes; record each section
  separately and cut at the timecodes.

## Pre-recording setup

Do these before opening the recorder. The goal is that nothing unexpected can
appear on screen and no dead air has to be edited out.

**Environment**

- [ ] Windows 11 at 1920×1080 with 100% display scaling; close every other
      window, mute notifications and hide the taskbar clock if it shows personal
      data.
- [ ] Use a clean user desktop or a dedicated recording profile. No browser
      tabs, no chat apps, no personal filenames in the window title.
- [ ] Ethernet or stable Wi-Fi; the AI call is the only network dependency.
- [ ] Close the app and the terminal once before recording, then relaunch, so
      the recording shows a cold, honest start.

**Repository and app**

- [ ] `git clone https://github.com/RenXiaoxiang/Stitchcraft.git` into a fresh
      folder (never the working copy with uncommitted experiments).
- [ ] `python -m pip install -e .` once, before recording.
- [ ] `stitch validate --strict` and `python -m unittest discover -s tests -v`
      run clean; keep the terminal open with one clean validation output ready.
- [ ] `stitch app` launches the studio and the Edge app window opens. Close it,
      then relaunch for the take.
- [ ] Create the two demo projects ahead of time but leave them in a pre-run
      state: a **Warehouse Operations** project and a **Personal Space**
      project, both with their brief typed but generation not yet started.
- [ ] Seed sample data for the warehouse table (a few inventory rows and inbound
      shipments) so the generated page looks alive without inventing numbers on
      camera.
- [ ] In the AI settings, enter a working OpenAI-compatible endpoint, model name
      and key. Keep the key masked; if the UI shows it, blur that region in the
      edit or re-enter it off camera.
- [ ] Choose database mode **local (browser localStorage)** for both demos; the
      remote REST fields can be shown but do not spend camera time on them.
- [ ] Run one generation off camera to confirm the model returns in reasonable
      time. If a run takes longer than ~25 seconds, plan to speed-ramp the waiting
      shot (2× or 4×) and say the timestamps do not change.

**Recording and post**

- [ ] OBS or similar at 1080p/30, microphone tested with a 10-second room-tone
      take; system audio off so notifications cannot leak in.
- [ ] Cursor highlighting on; mouse movement slow and deliberate.
- [ ] Record each storyboard section as a separate clip; label the clips by
      timecode.
- [ ] Music: none, or a YouTube Audio Library track cleared for reuse. Do not
      use commercial music.
- [ ] Final cut must be under 3:00. Aim for 2:45–2:55 to leave margin.
- [ ] Burn in captions or upload a clean subtitle track; read every caption
      against the screen.
- [ ] YouTube: public visibility, title "Stitchcraft — one skeleton, any site
      (Kiroween 2026)", description with the repository and Pages links, no
      age-restriction. Check playback on a phone before submitting the URL.

## Storyboard

| Time | Screen action | Narration | On-screen caption |
| --- | --- | --- | --- |
| **0:00–0:15** | Start on the exported warehouse dashboard, cursor still. Hard cut at 0:04 to the exported personal site. Hard cut at 0:09 to the studio with both projects listed. | One website skeleton. Two completely different applications. This is Stitchcraft — an AI site builder that stitches nine specialised skills into one pipeline, and shows its work at every seam. | One skeleton. Two apps. |
| **0:15–0:35** | Slow scroll through a generic AI chat producing a long page (or a static mock), then cut to the studio's stage list with the nine stages dimmed. | AI can write a landing page. Ask it for a whole site and it drifts: the brief fades, design and copy stop agreeing, and search and accessibility get bolted on last. The problem is not the page. It is the hand-offs. | The hard part is the hand-offs. |
| **0:35–1:00** | Terminal: type `stitch app`, press Enter. The Edge app window opens on the studio home. Click through the three top-level areas: **Projects**, **Themes**, **Skills** (or the equivalent labels in the built app). | Stitchcraft runs entirely on your machine. One command starts a local server and opens it as an Edge app window. No account, no cloud. Under the hood: nine modules — brief, plan, design, copy, build, SEO, accessibility, QA, deploy. One job each. One JSON contract per hand-off. | `stitch app` · local-first · no account |
| **1:00–1:20** | Open **Settings → AI**: fill base URL, model, key (key masked). Switch to **Database**: point at local mode, then briefly hover the remote fields (table URL, account) without filling them. | Bring your own OpenAI-compatible model: base URL, key, model. Keys stay local. Then choose where the site's data lives — browser localStorage, or a REST table you own. We will use local. | Your model. Your data. |
| **1:20–2:00** | Open the **Warehouse Operations** project. Type the brief in one sentence. Press **Generate**. Let the nine-stage view run (speed-ramp if needed). Land on the preview: dashboard, inventory table, filter a row, open the add-item modal, save. Click **Export**, then open the exported `index.html` from disk. | Pick Warehouse Operations. Describe it in a sentence. Watch the nine stages run — brief, plan, design, copy, build, discovery, accessibility, QA, deploy. The generator reads the theme's data model and the bundled skills. There it is: inventory, inbound shipments, low-stock alerts. Add an item. Preview it. Export static files that run offline. | Nine stages · one artifact per seam |
| **2:00–2:25** | Return to the studio. Open the **Personal Space** project, type the brief, generate. Cut to the finished personal site: notes list, tag filter, photo wall, about section. Scroll slowly. | Same skeleton, second application: Personal Space. Another brief. Notes, tags, a photo wall. Everything below the theme — the stages, the contracts, the export — is identical. | Same skeleton. Different theme. |
| **2:25–2:45** | Cut to a split screen: the repository tree on the left (`skills/`, `themes/`, `.kiro/`), the studio on the right. Highlight `skills/ATTRIBUTION.md`, `.kiro/specs/desktop-studio/requirements.md` and `.kiro/hooks/`. | Two things make this work. Skills: Google Chrome's Modern Web Guidance, GreenSock's official GSAP skills and the web-animation skills, vendored with pinned commits and licenses. Kiro: steering on every task, a spec with requirements, design and tasks, and seven agent hooks that re-run validation whenever a contract, theme or skill changes. I built this module by module in Kiro, and the hooks caught each broken seam after the edit. | Chrome guidance · GSAP · animation skills · 7 Kiro hooks |
| **2:45–2:55** | Cut back to the hero screen, then a slow cross-fade between the warehouse and personal exports. End card: wordmark, repository URL, "MIT licensed". | Stitchcraft is MIT licensed, open source, and offline by default. One skeleton. Two applications. Any site you can describe. Thanks for watching. | MIT · open source · offline |

## Spoken-word budget

The narration above is **under 500 words** and fits comfortably under three
minutes at a normal documentary pace. If a take runs long, cut the second
sentence of the problem section (it is the most compressible), never the screen
actions — the demo is the argument.

## Absolute rules for the final file

1. Length must be **less than 3:00** on YouTube's counter, not "about three
   minutes".
2. Video visibility must be **Public** (not unlisted) before the Devpost URL is
   pasted.
3. Every claim spoken on camera must be visible on screen or in the repository —
   no invented user counts, benchmarks or "thousands of sites".
4. The URL is pasted into [`submission.md`](submission.md) and
   [`checklist.md`](checklist.md) in the same sitting it is uploaded.
