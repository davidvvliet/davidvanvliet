# Probe-modelling harness (Blender)

Builds spacecraft models from Python scripts, checks them against sourced dimensions,
renders a contact sheet and exports `.glb` files for the site. Runs on Blender's bundled
Python; the command line needs only the system `python3`.

## Layout
- `lib/parts.py`: shared parts, in metres, used as `parts.<name>`; it gathers four files, and a new part goes in the one it belongs to:
  - `lib/parts_core.py`: the collection, assemblies, `_object` (bmesh to object), joints and poses
  - `lib/parts_shapes.py`: dish, prism bus, box, truss/rod boom, RTG, panel, cylinder, strut, disc with UVs and hub, plate, lathe, wheel, bent tube, joint chain
  - `lib/parts_aero.py`: fuselage sections and lofts, wings, tails and fins (`surface`, with pieces for control surfaces), grid fins
  - `lib/parts_skin.py`: operations on a skin: `cap_hole`, `shell`, `decal`
- `lib/materials.py`: the shared material list (foil, paint, metal, solar cells), merged with a spec's `materials`, and `image()` (image colour + normal map, optionally cut out by the image's alpha), Principled BSDF only
- `lib/textures.py`: textures made at build time from `refs/` data (`engraved()`: colour + normal map from a line image; `marking()`: colour + cut-out for a decal from traced masks)
- `lib/engines.py`: rocket and jet engines from an engine spec (nozzle contour, chamber, powerhead, pumps, pipes; nacelle, fan, core), full or simple, and `place` for putting them on a vehicle
- `lib/rig.py`: review rig and contact sheet (front, three-quarter / side, top; metric grid on the orthographic views)
- `lib/checks.py`: dimension checks measured from the built geometry, `attached`, `mounted`, `ground`, `joints`, `materials`, `textures`, triangle and file-size budgets (plus `sources`, from `lib/sources.py`)
- `probes/<probe>.py`: one script per probe, `build(spec)` using `lib/`
- `specs/<probe>.json`: dimensions with sources and tolerances, budgets, reference model
- `refs/<probe>/`: reference images, shown on the dashboard
- `baselines/<probe>.png`: the approved contact sheet, for regression checks
- `templates/`: what `new` copies
- `addon/live_server.py`: runs inside Blender's GUI so builds land in the open session
- `ref.py`: reference-model measuring (same rig, pieces with sizes and main-axis lengths)
- `explode.py`: splits a reference model into our parts (offsets, unclaimed pieces)
- `bake.py`, `lib/bake.py`: bakes a reference model's colours onto a probe (one atlas)
- `tools/pieces.py`, `tools/idview.py`, `tools/compare.py`: reference-model inspection (Blender scripts; see "Inspecting a reference model")
- `tools/engraving.py`: fits a line drawing of an engraved plate onto a photo of it (plain Python)
- `lib/sources.py`, `tools/sources.py`: a spec's sources (check, save texts; plain Python)
- `refs/<probe>/sources/`: saved texts of the sources a spec uses
- `build.py`: the build itself (spec → model → checks → render → export), headless or live
- `run.py`: the command line
- `blender.json`: pinned Blender version, path and live-server port
- `out/` (ignored): sheets, history, `.glb`/`.blend` per build and `status.json`

## Commands (from `frontend/`)
- `npm run blender`: open Blender with the live server (127.0.0.1 only)
- `npm run model <probe>`: build in the live session if one is open, else headless (`-- --headless` to force)
- `npm run model:dev [probe]`: rebuild on every save of a probe script, spec or `lib/` file (a `lib/` change rebuilds the given probe, or the last one built)
- `npm run model:all`: rebuild every probe; fails on a failing check or a sheet that changed against its baseline
- `npm run model:approve <probe>`: copy the last passing build to `public/models/` (with a thumbnail for the `/models` grid) and make its sheet the baseline. It records what the build read in `published.json`, so `run.py status` and the dashboard header can say when the live version is behind the repo (see `lib/published.py`). It refuses a build when anything that build read has changed since: rebuild, then approve
- `npm run model:new <probe> "Title"`: start a probe from the templates
- `npm run model:ref <probe> <model.glb>`: measure a reference model (sheet, and close-ups through the spec's views, in `refs/<probe>/`; largest pieces in `out/<probe>/ref/parts.json`)
- `npm run model:explode <probe> <model.glb>`: after a build, split the reference model into our parts (`out/<probe>/ref/explode.json` and `explode.png`)
- `npm run model:bake <probe> <model.glb>`: project the reference model's colours onto the probe (`refs/<probe>/baked.jpg`); see "Baked colour"
- `npm run model:pieces <model.glb> x0 y0 z0 x1 y1 z1 [--min M] [--max M] [--struts] [--dump]`, `model:idview`, `model:compare`: inspect a reference model region by region; see "Inspecting a reference model"
- `npm run model:photo get|fit|view|trace|cast <probe> ...`: photos of the real vehicle: fetch at full size, fit a camera, the model beside the photo, a photo flattened onto the skin, photo pixels cast onto the model; see "Photos of the real vehicle"
- `npm run model:status`, `npm run model:watch` (contact sheets inline in iTerm2)
- `python3 scripts/blender/run.py send <file.py>`: run any Python in the live session

The dev-only dashboard at `localhost:3000/models?dashboard` follows builds as they happen: progress,
a 3D view of the export, the contact sheet, references, checks and history. In the 3D view,
Explode (top left) slides the parts apart; hovering shows a part's name, size and, after
`model:explode`, its offset from the reference; clicking a part focuses the camera on it
(click again, click empty space or press Escape to return). Parts are grouped by assembly
when the model has them (see "Assemblies, joints and poses"), else by name family.

The dashboard reads every git worktree of the repo, not just the checkout it runs from, so
sessions working in their own worktrees share one dashboard. Each probe lists the worktrees
that have built it or are changing it (uncommitted changes to its spec, script or refs, or commits
not on `origin/main`): those changing it first, then newest build first. The header names the
worktree shown ("from x15") and, when there are several, switches between them; a build
starting in any worktree takes the page there. File URLs carry the worktree:
`/api/models/file/<worktree folder>/out/<probe>/sheet.png`. The "live version" check is always
the server's own checkout, which is what the site ships.

## Assemblies, joints and poses

Rovers, landers and capsules have moving parts, so their scripts declare structure as they build:

- `with parts.assembly("arm"):` tags every part made inside the block with its assembly (and
  `core=True` for the body the rest hangs off). The tag is exported as glTF extras. Explode
  (`model:explode` and the dashboard) groups by assembly and pushes groups away from the core;
  models without assemblies group by name family, and a part named `bus` is the core.
- `parts.joint(name, location, axis, parent)` is an empty with a turning axis; parts parented
  to it turn with it. `parts.chain(name, base, direction, links)` builds an arm or mast: a joint
  then a link per entry (`<name>_j1`, `<name>_1`, ...).
- `parts.pose({"arm_j1": -20, ...})` turns joints by name, in degrees about each joint's axis.
  Angles are absolute, so posing again replaces the earlier pose. Pose after building, from
  the spec's `joints`, so the posed angle is a sourced number.
- `parts.sides()` gives `(1, "left"), (-1, "right")` for building a mirrored pair.
- Shapes: `lathe` (a profile of `(r, z)` points turned about an axis: heads, cans, nozzles),
  `wheel` (tyre with rim, cleats, spokes and hub) and `tube` (a path of points with rounded
  bends: rocker and bogie beams, pipes).
- Aircraft shapes: `section` (a superellipse cross-section as `(y, z)` points), `loft` (a skin
  through rings of points: fairings, canopies), `fuselage` (a loft along x from
  `(x, half_width, top, bottom)` stations) and `surface` (a wing, tail or fin from its root and
  tip chords, with a lens or single-wedge section). `testplane` is their fixture.

Frame for anything standing on a surface: z up, ground at z = 0, and the spec's `note` says which
way is forward and which is left (the fixture: forward +y, left +x).

Specs for these probes can also use:

```json
"wheelbase": {"value": 1.2, "measure": "distance", "from": {"object": "wheel_left_front"},
              "to": {"object": "wheel_left_rear"}, "axis": "y", "source": "..."},
"ground": {"z": 0.0, "contacts": ["wheel_*"]},
"joints": {"arm_j1": {"angle": -20, "min": -90, "max": 10, "source": "..."}}
```

- `distance` measures between two points: `{"object": name, "at": "centre" | "bottom" | "top" |
  "origin"}` (default centre of its bounds) or the name of a spec `points` entry. With `axis`
  (`x`, `y` or `z`) it is the distance along that axis, else the straight distance.
- `ground`: every part matching a `contacts` glob touches z (within 5 mm, `tolerance`), nothing
  goes through it, and no other part reaches it.
- `joints`: every listed joint exists and its posed angle is inside `min`..`max`.

`testrover` is the rover fixture: a body, rocker-bogie suspension, six wheels, a mast and a
two-joint arm, with made-up values.

## Materials

A part asks for a material by name (`material="dark_metal"`). The names come from the shared
list in `lib/materials.py` plus the spec's `materials`, which add finishes or override a shared
one for that probe only:

```json
"materials": {
  "body_paint": {"hex": "#d9d4c7", "metallic": 0.0, "roughness": 0.6,
                 "source": "photo URL; sampled on the lit side of the deck"}
}
```

`hex` is sRGB, as sampled from a photo (or `color`: linear RGB, 0-1). `metallic` and `roughness`
default to the shared entry of the same name. Every spec material needs a `source`, like a
dimension (fixtures excepted). The shared list's values were set by eye for Voyager; a probe
that cares about a shared finish overrides it with a sourced one.

Every build checks `materials`: spec entries have sources, and each material's colour, metallic
and roughness in the export match Blender's (what the site shows is what was built).

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

Printed plates (flags, logos, calibration targets) are an image on `parts.plate()`, or on
`parts.outline_plate()` when the plate isn't rectangular: that takes the plate's edge as
(u, v) points in its image, kept beside the image in `refs/<probe>/<name>.json`, so the shape
is geometry and the image needs no transparency.

Builds with textured parts also check `textures`: every image has pixels, textured parts have
UVs inside the image, and the export carries every image.

## Painted markings (decals)

Paint on a curved skin (lettering, insignia, stripes) is a decal: `parts.decal()` lays a sheet
on the host part, 2 mm off its skin (`lift`), so it follows the curve and never flickers:

```python
paint = materials.colour(spec["materials"]["marking_paint"])          # a sourced spec material
img = textures.marking("lettering", [(os.path.join(REFS, "lettering-mask.png"), paint)],
                       os.path.join(HARNESS, "out", probe, "textures"))
mat = materials.image("lettering", img, metallic=0.0, roughness=0.5, cutout=True)
with parts.assembly("lettering_left"):
    parts.decal("lettering_left", body, center=(x, y, z), direction=(0, -1, 0), up=(0, 0, 1),
                width=1.8, height=0.35, material=mat)
```

- `center` is the marking's middle, on or near the skin; `direction` is the way it is looked
  at (into the skin); `up` is the image's top. `width` x `height` are measured along the skin:
  the sheet wraps by arc length, so a marking keeps its painted size where the skin curves away
  (a flat projection of the fixture's 0.6 m nose decal would be 13% short). It raises if any of
  it misses the host.
- The image is a mask per colour, traced from a photo (white = paint, grey PNG, all the same
  size, covering the decal), painted in the spec's sourced colours by `textures.marking()`.
  Colours never come from the mask.
- `materials.image(..., cutout=True)` rounds the image's alpha into the shader, which exports as
  glTF `alphaMode: MASK`: sharp edges, no transparency sorting, drawn as a cut-out by the site.
- Give every decal its own assembly (the viewer focuses one per click) and list it in the
  spec's `mounts`. Decal vertices are in the vertex group "back", which `mounted` reads as the
  face on the host, so a decal floating more than 3 mm off or sunk more than 2 mm in fails.
  `textures` also fails a cut-out material that doesn't export as MASK, or whose image has no
  transparent pixels (it would show as a rectangle).
- Place a marking from photos: fit a camera to the photo, flatten the photo onto the marking's
  sheet (`model:photo trace`), draw the mask over it, and note it as traced from that photo
  (see "Photos of the real vehicle").
- `testplane` has two decals (a flat-ish side and the curved nose).

## Photos of the real vehicle

Positions, shapes and markings taken from photos all go the same way: a camera fitted to the
photo, then the model checked against it, or the photo laid onto the model. From `frontend/`,
after a build:

    npm run model:photo get x15 NASM-SI-2008-5559          # or a URL
    # write refs/x15/photos/NASM-SI-2008-5559.fit.json (landmarks: tools/photo_fit.py)
    npm run model:photo fit x15 NASM-SI-2008-5559          # -> .camera.json beside it, an overlay
    npm run model:photo view x15 NASM-SI-2008-5559         # photo | model through that camera
    npm run model:photo trace x15 NASM-SI-2008-5559 frame.json out.png 400
    npm run model:photo cast x15 NASM-SI-2008-5559 1500,1300

- Always work from the largest copy. Smithsonian (`ids.si.edu`) serves photos up to 4000 px
  when asked for more than it has (`get` does); the 1600 px copies linked from collection
  pages lose fine detail (thin lines, small stencils) that the full size shows clearly.
- Photos are data: they go in `out/<probe>/photos/` (not in git), nothing in them is run.
  `refs/<probe>/photos/` keeps what to fetch again (`photos.json`), each photo's fit settings
  and its camera, so the next session reuses the camera instead of refitting.
- A fit starts from 4 or more landmarks (a part's extreme point, or a world point, with its
  pixel), then matches outlines; it prints the landmarks' error and the outline overlap
  (`1 - IoU`; below 0.07 is a good fit). Check `view` before using a camera: a fit that is off
  by a few cm puts everything traced through it off by the same.
- Note when each photo was taken. A vehicle on display changes (the X-15's nose dart circle
  is plain yellow in the museum's 2007-2018 photos, with the NASA insignia in later ones):
  build the state the user asked for, and say which photos show it.
- `trace` and `cast` need the camera fitted at the photo's own size; `get` keeps it that way.

## Baked colour

A spec with a `bake` section (see `specs/perseverance.json`) gets one colour atlas for all
its untextured parts, projected from the reference model, plus an optional normal map.
`run.py bake <probe> <model>` (npm `model:bake`):
- builds the probe and unwraps every part into one atlas (`lib/bake.py`, at rest pose, world
  scale, packed). Faces nobody can see (rays from them hit another part within 1 cm, or the
  inside of one) are unwrapped separately at 5% of the texel size, so the atlas goes to
  visible surfaces;
- poses the reference at `bake.frame` (its animation frame) and drops `bake.ignore` objects;
- bakes base colour, not lit colour: every material is switched to an emission of its base
  colour for the colour bake (a diffuse bake reads metal and glass as black);
- projects in `passes`, nearest first: each pass's rays start `extrusion_m` outside our
  surface and reach `max_ray_m`. Per face, all or nothing: a face takes the first pass that
  hits at least `min_face_hit` (default 0.5) of it; a face no pass reaches keeps its sourced
  colour (no patchwork). A far pass lets stand-in shapes pick up the reference's detail;
- with `normal_size`, bakes the reference's surface detail (its geometry and its own normal
  maps) as a tangent-space normal map on the faces that took its colour, flat elsewhere;
- writes `refs/<probe>/baked.jpg`, `baked_normal.jpg` and `baked.json` (geometry fingerprint,
  atlas layout hash, coverage, atlas use, hidden faces), plus `out/<probe>/bake_projection.png`
  and `bake_flat.png` (the projection alone and the fallback, to see misses and smears).

Every build unwraps the same way and applies both maps; metal and roughness stay as sourced.
The atlas is laid out with every joint at 0, so posing needs no re-bake. The `bake` check
fails when the geometry changed since the bake, or the layout differs: re-run it. Smears
show where our shape is more than a few cm off the reference: shorten `max_ray_m`, or fix
the shape. Parts with their own image (plates) are left out. Images export at JPEG quality
90; Perseverance (4096 px colour and normal map) has a 7 MB budget (`budget.glb_bytes`).

## Inspecting a reference model
NASA's models are untitled piles of loose pieces (Voyager's bus area alone is hundreds). To
measure one part, narrow down by region (all in metres, the reference model's frame):

- `run.py pieces <model> x0 y0 z0 x1 y1 z1`: every loose piece whose bounds centre is in the
  box: size, centre, principal axis, largest first. `--min/--max` filter by size (a thruster
  hunt is `--max 0.16`). `--struts` merges the flat faces a strut is built from and prints its
  end points and thickness (Voyager's under-bus legs, ring struts). `--dump` prints each
  piece's vertices to fit a shape to (Voyager's bus-top blanket profile, the scan platform's
  half cylinder).
- `run.py idview <model> <out.png> <region> <target> <offset>`: the same pieces, one colour
  each, with a legend: the quickest way to see which piece is which.
- `run.py compare <probe> <model> <out.png> "tx,ty,tz,dx,dy,dz" ...`: the reference (top) and
  our last build (bottom) from the same cameras, textures on. Run it after every pass and
  every bake: a part shaped differently from the reference shows here first, as missing
  geometry or as bake texture landing wrong (Voyager's scan platform underside was a box where
  NASA's is a half cylinder, and the bake printed the cylinder's end flat on the box's side).

Write what you measure into the spec's `from_reference_model` with how it was measured.

## From Blender to the site
1. Every build exports `out/<probe>/<probe>.glb` (ignored by git), so nothing reaches the site.
2. `npm run model:approve <probe>` copies the last passing build to `public/models/<probe>.glb`;
   once committed and deployed it is served at `/models/<probe>.glb`. The /models page shows the
   spec's `"logos"` in the card's corner: who built the real vehicle first (`nasa`, `spacex`), then
   partners (`jpl`, `naa`, `rocketdyne`); the images are listed in `app/models/PublishedModels.tsx`.
3. Not built yet: the scene loading it. A mission's craft is drawn as a small blue sphere
   (`marker` in `app/components/SolarSystem.tsx`, where the mission is set up). The plan is
   to load the `.glb` with three's glTF loader and show it in place of the sphere when the
   camera is close, keeping the dot further out.
   Scale: models are in real metres, but scene units are Earth radii x 1.3 (`EARTH_RADIUS`),
   so a 3.7 m dish at true scale is invisible. The craft must be drawn enlarged up close, as
   the dot already is far out.
   This step is the only one that changes the existing scene: it is its own change, made
   with the user's go-ahead.

## Sources

A spec lists every source it uses once, in `sources`, and cites them by id everywhere else:

```json
"sources": [
  {"id": "nssdca", "title": "NSSDCA: Voyager 1", "url": "https://...", "read": "2026-10-27",
   "licence": "public domain (NASA)", "saved": "refs/voyager/sources/nssdca.txt"},
  {"id": "kohlhase1977", "title": "...", "url": "https://...", "licence": "© 1977 Kluwer: quoted, not kept",
   "archive": "https://web.archive.org/web/..."},
  {"id": "nasa_3d_voyager", "...": "...", "credit": "NASA 3D Resources, Voyager model (layout reference): ..."}
],
"dimensions": {"hga_diameter": {"value": 3.66, "source": "nssdca", "quote": "..."}},
"facts": {"science_boom": {"value": "...", "source": "kohlhase1977, p.83"}}
```

- A citation is an id, or an id followed by where or how (`"kohlhase1977, p.83"`), a list of
  those, or `"sources": [{"source": id, "quote": ...}]`. Second sources go in `also`/`conflict`
  as `{"source": id, "quote": ...}`, not in free text, so they count as used.
- `saved`: its text in `refs/<probe>/sources/`, only when the licence allows it (public domain,
  CC BY). Copyrighted sources keep just the link and the quotes. `archive` (an existing Wayback
  snapshot or a commit permalink) is optional. The licence is quoted from the source.
- `credit`: a line for the site's credits, for sources whose content ships (the reference model,
  photos colours were sampled from, drawings used as textures). `model:approve` writes the
  published probe's credit lines to `app/terminal/commands/model-credits.json`, which the
  `credits` command shows.

Every build checks `sources`: every citation is a listed id, every listed source is cited, saved
files exist, and the reference model's source has a credit. Fixtures may cite "design
value". The same check runs without Blender, during research:

    python3 -I tools/sources.py check <probe>
    python3 -I tools/sources.py save <probe> <id> <downloaded file>   # PDF/HTML -> text

## Spec dimensions
```json
"dish_diameter": {"value": 3.66, "object": "dish", "measure": "diameter",
                  "tolerance": 0.03, "source": "https://..."}
```
`object` is a part name, a list of names, or `"*"` for the whole probe. `measure` is `x`, `y`
or `z` (world extent), `length` (along the first object's local Z) or `diameter` (twice the
largest distance from that axis). For nozzles (a hollow shell, measured alone): `throat_diameter`
(the narrowest inner diameter along that axis) and `area_ratio` (exit over throat area, inner
wall). Tolerance is relative, default 3%.

Every build also checks `attached`: each part must touch (within 2 cm) or sit inside another,
so nothing floats. A spec can list checks to skip in `skip_checks` (only the fixture does).

Parts that sit on a surface go in the spec's `mounts` (`{"golden_record": {"on": "bus"}}`).
The `mounted` check fails if the part's back face (its lowest local Z, where parts are built
from, or its vertex group "back": decals) is more than 3 mm off the host anywhere, or if any of it is more than 2 mm inside the host.
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

`testprobe`, `testrover`, `testplane` and `testengine` are fixtures (`"fixture": true`), not spacecraft: one of every part
with made-up values, so changes to `lib/` show against their baselines. Fixtures are never published.

## Engines
Engines are models of their own and parts other models use (`lib/engines.py`; the
`model-engine` skill covers research and modelling).
- An engine's spec has an `engine` block (see the top of `lib/engines.py` for every key), each
  value sourced like a dimension, plus the usual `sources`, `dimensions` (check the nozzle with
  `diameter`, `throat_diameter`, `area_ratio`, `length`), `materials` and `budget`. Its probe
  is two lines: `engines.build(spec["engine"], "<engine>", lod="full")`.
- Frame: the thrust axis is local z, the nozzle exit (a jet's exhaust plane) at z = 0.
- Optional rocket parts: a nozzle `extension` (z = 0 moves to its exit), stiffening `hoops` on
  the nozzle and extension, a turbine exhaust `manifold` torus that can taper, and `lathe` parts
  (the F-1 uses all of them).
- Nozzle contours: `parabola` (initial and exit wall angles, the usual approximation of a bell),
  `cone`, or `traced` (the wall's profile measured from a side photo, scaled by the exit).
- A vehicle lists the engines it uses in its spec (`"engines": ["raptor3"]`) and calls
  `engines.place(engines.load(spec, "raptor3"), name, location, direction, lod="simple")`.
  The list makes the vehicle behind when the engine's spec changes (`lib/published.py`) and
  adds the engine's credits to the vehicle's. `lod="simple"` drops the plumbing and most
  segments, for vehicles with a few engines; `lod="low"` (12 segments) is for clusters of
  dozens (Super Heavy's 33).
- Until an engine has a spec of its own, a vehicle can pass a sourced `engine` block from its
  own spec straight to `engines.place` (Super Heavy's `from_photos.engine`, a Raptor stand-in).
