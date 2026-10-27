# Probe-modelling harness (Blender)

Builds spacecraft models from Python scripts, checks them against sourced dimensions,
renders a contact sheet and exports `.glb` files for the site. Runs on Blender's bundled
Python; the command line needs only the system `python3`.

## Layout
- `lib/parts.py`: shared parts (dish, prism bus, box, truss/rod boom, RTG, panel, cylinder), in metres
- `lib/materials.py`: shared materials (foil, paint, metal, solar cells), Principled BSDF only
- `lib/rig.py`: review rig and contact sheet (front, three-quarter / side, top; metric grid on the orthographic views)
- `lib/checks.py`: dimension checks measured from the built geometry, triangle and file-size budgets
- `probes/<probe>.py`: one script per probe, `build(spec)` using `lib/`
- `specs/<probe>.json`: dimensions with sources and tolerances, budgets, reference model
- `refs/<probe>/`: reference images, shown on the dashboard
- `baselines/<probe>.png`: the approved contact sheet, for regression checks
- `templates/`: what `new` copies
- `addon/live_server.py`: runs inside Blender's GUI so builds land in the open session
- `build.py`: the build itself (spec → model → checks → render → export), headless or live
- `run.py`: the command line
- `blender.json`: pinned Blender version, path and live-server port
- `out/` (ignored): sheets, history, `.glb`/`.blend` per build and `status.json`

## Commands (from `frontend/`)
- `npm run blender`: open Blender with the live server (127.0.0.1 only)
- `npm run model <probe>`: build in the live session if one is open, else headless (`-- --headless` to force)
- `npm run model:all`: rebuild every probe; fails on a failing check or a sheet that changed against its baseline
- `npm run model:approve <probe>`: copy the last passing build to `public/models/` and make its sheet the baseline
- `npm run model:new <probe> "Title"`: start a probe from the templates
- `npm run model:status`, `npm run model:watch` (contact sheets inline in iTerm2)
- `python3 scripts/blender/run.py send <file.py>`: run any Python in the live session

The dev-only dashboard at `localhost:3000/models` follows builds as they happen: progress,
a 3D view of the export, the contact sheet, references, checks and history.

## From Blender to the site
1. Every build exports `out/<probe>/<probe>.glb` (ignored by git), so nothing reaches the site.
2. `npm run model:approve <probe>` copies the last passing build to `public/models/<probe>.glb`;
   once committed and deployed it is served at `/models/<probe>.glb`.
3. Not built yet: the scene loading it. A mission's craft is drawn as a small blue sphere
   (`marker` in `app/components/SolarSystem.tsx`, where the mission is set up). The plan is
   to load the `.glb` with three's glTF loader and show it in place of the sphere when the
   camera is close, keeping the dot further out.
   Scale: models are in real metres, but scene units are Earth radii x 1.3 (`EARTH_RADIUS`),
   so a 3.7 m dish at true scale is invisible. The craft must be drawn enlarged up close, as
   the dot already is far out.
   This step is the only one that changes the existing scene: it is its own change, made
   with the user's go-ahead.

## Spec dimensions
```json
"dish_diameter": {"value": 3.66, "object": "dish", "measure": "diameter",
                  "tolerance": 0.03, "source": "https://..."}
```
`object` is a part name, a list of names, or `"*"` for the whole probe. `measure` is `x`, `y`
or `z` (world extent), `length` (along the first object's local Z) or `diameter` (twice the
largest distance from that axis). Tolerance is relative, default 3%.

`testprobe` is a fixture (`"fixture": true`), not a spacecraft: one of every part with made-up
values, so changes to `lib/` show against its baseline. Fixtures are never published.
