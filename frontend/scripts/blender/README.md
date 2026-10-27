# Probe-modelling harness (Blender)

Builds spacecraft models from Python scripts, checks them against sourced dimensions,
renders a contact sheet and exports `.glb` files for the site. Runs on Blender's bundled
Python; the command line needs only the system `python3`.

## Layout
- `lib/parts.py`: shared parts (dish, prism bus, box, truss/rod boom, RTG, panel, cylinder, strut, disc with UVs and hub, lathe, wheel, bent tube), assemblies, joints and poses, in metres
- `lib/materials.py`: the shared material list (foil, paint, metal, solar cells), merged with a spec's `materials`, and `image()` (image colour + normal map), Principled BSDF only
- `lib/textures.py`: textures made at build time from `refs/` data (`engraved()`: colour + normal map from a line image)
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
- `npm run model:approve <probe>`: copy the last passing build to `public/models/` and make its sheet the baseline
- `npm run model:new <probe> "Title"`: start a probe from the templates
- `npm run model:ref <probe> <model.glb>`: measure a reference model (sheet, and close-ups through the spec's views, in `refs/<probe>/`; largest pieces in `out/<probe>/ref/parts.json`)
- `npm run model:explode <probe> <model.glb>`: after a build, split the reference model into our parts (`out/<probe>/ref/explode.json` and `explode.png`)
- `npm run model:status`, `npm run model:watch` (contact sheets inline in iTerm2)
- `python3 scripts/blender/run.py send <file.py>`: run any Python in the live session

The dev-only dashboard at `localhost:3000/models` follows builds as they happen: progress,
a 3D view of the export, the contact sheet, references, checks and history. In the 3D view,
Explode (top left) slides the parts apart; hovering shows a part's name, size and, after
`model:explode`, its offset from the reference; clicking a part focuses the camera on it
(click again, click empty space or press Escape to return). Parts are grouped by assembly
when the model has them (see "Assemblies, joints and poses"), else by name family.

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

`testprobe` and `testrover` are fixtures (`"fixture": true`), not spacecraft: one of every part
with made-up values, so changes to `lib/` show against their baselines. Fixtures are never published.
