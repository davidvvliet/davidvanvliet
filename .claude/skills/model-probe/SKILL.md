---
name: model-probe
description: Model a spacecraft (probe, lander, rocket stage) in Blender for the site with the harness in frontend/scripts/blender. Use when asked to model, build, fix or refine a probe's 3D model, add a new probe model, or change the shared Blender parts.
---

# Modelling a probe

The harness lives in `frontend/scripts/blender` (read its README first). Every model is a
script plus a sourced spec; nothing is modelled by hand in the GUI, so every model rebuilds
from the repo.

## Rules
- Never type a dimension from memory. Every number in a spec has a `source` (a URL, or a
  document and page). A value estimated from a reference image says so in its source
  ("estimated from refs/<probe>/<file>, scaled by the 3.66 m dish").
- Look for an official NASA 3D model first (NASA's 3D Resources) and record it in
  `reference_model`. Measure it with `npm run model:ref`; say so before deriving geometry from it.
- Model in metres at real size. Stay within the budgets (default 50k triangles, 1.5 MB).
- Build from `lib/parts.py`. When a probe needs a part twice or another probe will want
  it, add it to `lib/` instead of writing it in the probe script.
- A change to `lib/` affects every probe: run `npm run model:all` and look at any sheet
  flagged as changed before calling the change done.
- Never run `model:approve` without the user's go-ahead: it writes `public/models/` and
  resets the baseline. Wiring a model into the solar-system scene is a separate change
  (see "From Blender to the site" in the README, including the scale problem).

## Loop
1. `npm run model:new <probe> "Title"` (from `frontend/`), then research and fill in the spec
   with the `research-probe` skill, and get the user's review of it before modelling.
2. Put reference images in `refs/<probe>/` (the dashboard shows them beside the sheet).
3. Ask the user to start the live session (`npm run blender`) if they want to watch, and to
   open `localhost:3000/models` (their iTerm2 browser pane works).
4. Start `npm run model:dev <probe>` in the background so every save rebuilds (the user sees
   each change on the dashboard and in Blender), then write `probes/<probe>.py`. Or build by
   hand with `npm run model <probe>`. Read the check table it prints;
   fix failing checks before looking at images.
5. Read `out/<probe>/sheet.png` (one image, four views, metric grid) against the
   references for proportions, then `out/<probe>/closeups.png` for joints and small parts:
   at sheet scale a bent boom or a floating part is a few pixels (both slipped through on
   Voyager until the user spotted them). Give the spec `closeups` for every joint and boom
   end. Fix proportions, then details. Repeat 4-5.
6. When checks pass and the sheet matches, show the user the sheet and ask for approval.
   On approval: `npm run model:approve <probe>`.

## Lessons from Voyager
- Build in the reference model's frame and give the spec a `sheet_frame` (the union of both
  models' bounds), then re-run `model:ref`: identical framing makes differences obvious.
- Measure a part from points that can only belong to it (Voyager's boom angle was first
  skewed by the RTG stack inside the region). Cross-check: does the documented length,
  laid back from the measured tip, land somewhere physically sensible?
- Check what a document's number refers to against the reference model (Voyager's
  "40.6 cm RTG diameter" is the body; the fins span 0.63 m).

## When the user corrects something
Fix it at the level it belongs: a wrong number in the spec (with a better source), a
part's shape in `lib/parts.py`, a look in `lib/materials.py`. If the lesson applies to
future probes, add it to the rules above.
