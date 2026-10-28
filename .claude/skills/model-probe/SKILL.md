---
name: model-probe
description: Model a spacecraft (probe, lander, rocket stage) in Blender for the site with the harness in frontend/scripts/blender. Use when asked to model, build, fix or refine a probe's 3D model, add a new probe model, or change the shared Blender parts.
---

# Modelling a probe

The harness lives in `frontend/scripts/blender` (read its README first). Every model is a
script plus a sourced spec; nothing is modelled by hand in the GUI, so every model rebuilds
from the repo.

## Rules
- Never type a dimension from memory. Every number in a spec has a `source`: an id from the
  spec's `sources`, plus the page or how it was measured. A value estimated from a reference image says so in its source
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
- Approve publishes the last build only if nothing it read has changed since. Otherwise it
  refuses and lists the files: rebuild, look at the result, then approve. It also refuses while
  shared code (`lib/`, `build.py`, `blender.json`) has uncommitted changes.

## Several sessions at once
More than one Claude session may be working in this harness.
- A probe's files (`specs/<probe>.json`, `probes/<probe>.py`, `refs/<probe>/`) belong to the
  session working on that probe. Check `git status` before starting on one. If another session
  has uncommitted changes there, message it (ListAgents, SendMessage) instead of editing.
- `lib/`, `build.py`, `run.py` and the README are shared. Before changing them, tell the other
  sessions what will change. Edit only your own lines.
- Commit only your own work. Run `git diff --cached --name-only` first: another session may
  have staged files, and a plain commit takes them along. In a file both sessions edited, stage
  just your lines (index the committed version with your edits applied, via
  `git hash-object -w` + `git update-index --cacheinfo`).
- Approve only a probe you own, or after telling its session. A rebuild while another session
  is mid-change bakes its unfinished work into the build.
- Work in your own git worktree so another session's uncommitted `lib/` edits don't reach
  your builds: `git worktree add ../davidvanvliet-<probe> -b <probe> main`, then run the
  harness from its `frontend/`. Never push the branch (Vercel would deploy a preview): rebase
  on `origin/main` and `git push origin HEAD:main`. Builds there run headless (the live
  Blender session only builds for the checkout it was started from). The dashboard on :3000
  reads every worktree: for each probe it shows the worktree changing that probe's files
  first, else the newest build, labelled with the worktree's name and switchable in the header.
  Never move or restart :3000 for this.

## Loop
1. `npm run model:new <probe> "Title"` (from `frontend/`), then research and fill in the spec
   with the `research-probe` skill, and get the user's review of it before modelling.
2. Put reference images in `refs/<probe>/` (the dashboard shows them beside the sheet).
3. Ask the user to start the live session (`npm run blender`) if they want to watch, and to
   open `localhost:3000/models?dashboard` (their iTerm2 browser pane works).
4. Start `npm run model:dev <probe>` in the background so every save rebuilds (the user sees
   each change on the dashboard and in Blender), then write `probes/<probe>.py`. Or build by
   hand with `npm run model <probe>`. Read the check table it prints;
   fix failing checks before looking at images.
5. With a reference model, run `npm run model:explode <probe> <model>` after each pass: it
   splits the reference into our parts and prints each part's centre offset and size against
   the reference, plus the reference pieces none of our parts claim (missing or misplaced
   parts). Read `out/<probe>/ref/explode.png`. Work down the unclaimed list and the largest
   offsets.
   To measure or identify reference pieces, use `model:pieces` / `model:idview`, and check
   each pass and bake with `model:compare` (README "Inspecting a reference model").
   Read `out/<probe>/sheet.png` (one image, four views, metric grid) against the
   references for proportions, then `out/<probe>/closeups.png` for joints and small parts:
   at sheet scale a bent boom or a floating part is a few pixels (both slipped through on
   Voyager until the user spotted them). Give the spec `closeups` for every joint and boom
   end, and look at every new part in a close-up before calling a pass done: passing checks
   only cover what is checked (Voyager's golden record sat on a corner, half buried, with
   every check green). Fix proportions, then details. Repeat 4-5.
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
- Measure the main body's orientation and height band from the reference model's side faces
  (normal directions, z extent), not from one large piece: Voyager's bus was first placed on
  a plate above it and turned 18°, which put the golden record on a corner, half buried.
- Every part that sits on a surface (plaques, sensors, horns) goes in the spec's `mounts`.
  The `mounted` check fails when its back face isn't on the host everywhere or when it is
  buried. When adding a check, show it failing on the bad case before trusting a pass.
- Positions of painted details (plaques, markings) can be read from the reference model's
  texture: sample the texture colour on candidate faces.
- Engraved or printed plates: a colour + normal map, not geometry (fine lines cost tens of
  thousands of triangles and don't show). Get the layout from a photo of the real plate:
  fit a clean drawing onto it with `tools/engraving.py` and check the overlay, since
  explanatory drawings space their parts differently. Build with `parts.disc` +
  `textures.engraved` (see the README's "Engraved plates").
- Give every marking its own assembly: the viewer focuses one assembly per click. Plates
  that aren't rectangles get `parts.outline_plate` (the shape as geometry), not a
  transparent image, which would also hide the plate's edges.
- Paint on a curved skin (lettering, insignia, stripes) is a decal, not a plate: `parts.decal`
  with a `textures.marking` image (masks traced from a photo, colours from the spec's sourced
  `materials`) on a `materials.image(..., cutout=True)` material, listed in `mounts`
  (README "Painted markings"). Never type the lettering in a font: trace it from a photo.
- A stand-in box sized from a reference object's bounds can be far off: Perseverance's
  deck box came out 0.11 m too tall from a thin stalk on top. Read a body's top from rays
  cast down on it before mounting anything there.

## Rovers, landers and capsules
- Build in a standing frame: z up, ground at z = 0, forward and left as the spec's `note` says.
- Declare structure while building: every part inside a `with parts.assembly(...)` block (the
  body with `core=True`), moving parts parented to `parts.joint`s, arms and masts with
  `parts.chain`. Explode and the dashboard group by assembly.
- Pose once, after building, from the spec's `joints` (`parts.pose`), each angle with a source
  and limits. Give the spec a `ground` (wheels or footpads as contacts) and `distance`
  dimensions for wheelbase, track, clearance and mast height. `testrover` shows all of it.
- Look at the wheels and suspension in close-ups from the side and from below: a wheel off the
  ground or a beam through a wheel is a few pixels on the sheet.

## Materials
- Use the spec's `materials` for the probe's own finishes and the shared names in
  `lib/materials.py` for the rest. Don't add a probe's colour to the shared list: a shared
  entry changes every probe (run `model:all` if you must).
- Don't invent a colour in the probe script. An unsourced finish goes in `open_questions`.

## When the user corrects something
Fix it at the level it belongs: a wrong number in the spec (with a better source), a
part's shape in `lib/parts.py`, a look in `lib/materials.py`. If the lesson applies to
future probes, add it to the rules above.
