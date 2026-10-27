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
- `ref.py`: reference-model measuring (same rig, pieces with sizes and main-axis lengths)
- `build.py`: the build itself (spec → model → checks → render → export), headless or live
- `run.py`: the command line
- `blender.json`: pinned Blender version, path and live-server port
- `out/` (ignored): sheets, history, `.glb`/`.blend` per build and `status.json`

## Commands (from `frontend/`)
- `npm run blender`: open Blender with the live server (127.0.0.1 only)
- `npm run model <probe>`: build in the live session if one is open, else headless (`-- --headless` to force)
- `npm run model:dev [probe]`: rebuild on every save of a probe script, spec or `lib/` file (a `lib/` change rebuilds the given probe, or the last one built)
- `npm run model:all`: rebuild every probe; fails on a failing check or a sheet that changed against its baseline
- `npm run model:approve <probe>`: copy the last passing build to `public/models/` and make its sheet the baseline
- `npm run model:new <probe> "Title"`: start a probe from the templates
- `npm run model:ref <probe> <model.glb>`: measure a reference model (sheet, and close-ups through the spec's views, in `refs/<probe>/`; largest pieces in `out/<probe>/ref/parts.json`)
- `npm run model:status`, `npm run model:watch` (contact sheets inline in iTerm2)
- `python3 scripts/blender/run.py send <file.py>`: run any Python in the live session

The dev-only dashboard at `localhost:3000/models` follows builds as they happen: progress,
a 3D view of the export, the contact sheet, references, checks and history.

## Engraved plates (textures)

Plates with engravings (Voyager's golden record cover) get a colour map and a normal map, made
at build time by `lib/textures.engraved()` from a line image in `refs/<probe>/` (white =
engraved). `parts.disc()` maps that square image onto the plate's front face. The normal map
makes the lines catch the light like grooves without extra triangles.

The line image comes from `tools/engraving.py` (macOS: renders SVG with Quick Look):

    python3 -I tools/engraving.py fit refs/voyager/record-cover.svg <photo> refs/voyager/record-cover-fit.json --groups A,B,...
    python3 -I tools/engraving.py lines refs/voyager/record-cover.svg refs/voyager/record-cover-fit.json refs/voyager/record-cover-lines.png
    python3 -I tools/engraving.py overlay refs/voyager/record-cover.svg <photo> refs/voyager/record-cover-fit.json overlay.png

`fit` finds the plate's rim in a photo of the real plate and places each named group of a line
drawing where its lines best overlap the photo's engraved lines (groups left out, such as
labels and arrows, are dropped). Drawings made to explain a plate often space their parts
differently from the plate, so each group is fitted on its own. Check `overlay` by eye. Only
the fit, the drawing and the line image are kept in the repo; the photo is linked in the spec.

Builds with textured parts also check `textures`: every image has pixels, textured parts have
UVs inside the image, and the export carries every image.

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

Every build also checks `attached`: each part must touch (within 2 cm) or sit inside another,
so nothing floats. A spec can list checks to skip in `skip_checks` (only the fixture does).

Parts that sit on a surface go in the spec's `mounts` (`{"golden_record": {"on": "bus"}}`).
The `mounted` check fails if the part's back face (its lowest local Z, where parts are built
from) is more than 3 mm off the host anywhere, or if any of it is more than 2 mm inside the host.
That catches a plaque hanging over an edge, half buried, or floating.

`run.py explode <probe> <model>` (npm `model:explode`, after a build) breaks a reference
model into our parts. Reference files often have no part names, so our build labels it: each
loose reference piece belongs to the nearest of our parts if it lies within 5 cm of that
part's convex hull (median of its points). It writes `out/<probe>/ref/explode.json` (per
part family: reference box vs ours and centre offset; then the unclaimed groups, with their
nearest part) and `explode.png`: an overview coloured by part (red: unclaimed), an exploded
overview, one tile per part family (reference pieces with ours as a cyan wireframe), and
one tile per unclaimed group. Unclaimed groups are what we haven't built or built in the
wrong place. Touching pieces form one group, so a large group can span several parts.

Each build also renders close-ups (`out/<probe>/closeups.png`, tiled three to a row) for joints
and small parts. A spec's `closeups` lists them: `{"name", "target": [x, y, z], "look": [x, y, z],
"radius": m}`; without it there is one view of the craft's core (everything but the long booms).

A spec's `sheet_frame` (`{"min": [x, y, z], "max": [...]}`) fixes the contact-sheet framing for
both the build and `model:ref`, so the two sheets overlay exactly (the dashboard's build/reference
toggle then works as a blink comparator). Build the probe in the reference model's frame.

`testprobe` is a fixture (`"fixture": true`), not a spacecraft: one of every part with made-up
values, so changes to `lib/` show against its baseline. Fixtures are never published.
