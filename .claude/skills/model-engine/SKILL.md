---
name: model-engine
description: Research and model a rocket engine or jet engine in detail with the Blender harness (lib/engines.py), as a model of its own that vehicles then reuse. Use when asked to model, research, refine or add an engine (Raptor, Merlin, RS-25, F-1, J58...), or to put a modelled engine on a rocket or aircraft.
---

# Modelling an engine

Engines use the same harness as every model (`frontend/scripts/blender`, read its README,
section "Engines", and the top of `lib/engines.py`). The rules of `model-probe` and
`research-probe` apply: every number in the spec has a source, nothing typed from memory,
`model:approve` only with the user's go-ahead. This skill adds what is particular to engines.

## Output
- `specs/<engine>.json`: `sources`, an `engine` block (keys in `lib/engines.py`, each value
  sourced), `dimensions` that check the build, `materials`, `open_questions`, `budget`.
- `probes/<engine>.py`: `engines.build(spec["engine"], "<engine>", lod="full")`, plus any
  part `lib/engines.py` can't make yet (add it to `lib/engines.py` if another engine will need it).
- Reference photos in `refs/<engine>/` only if their licence allows; otherwise link them.

## Research: what defines an engine's look
List these first and mark each "unverified" until read in a source opened this session.
- **Rocket**: nozzle exit diameter, throat diameter or area (expansion) ratio, nozzle length
  (throat to exit), overall length and diameter, the bell's shape (contour and wall angles),
  chamber diameter and length, powerhead layout (turbopumps: how many, where, which way their
  axes point), main pipes, gimbal mount and actuators, nozzle extension (vacuum engines), the
  cooling tubes or channels on the nozzle, finishes (bare metal, heat-tinted, painted, wrapped).
  Note which version: sea-level and vacuum variants, and engine generations, differ a lot.
- **Jet**: length, maximum diameter, inlet and exhaust diameters, fan diameter and blade
  count, hub (spinner) size, fan depth behind the inlet lip, bypass duct and core exhaust,
  afterburner and nozzle petals, accessory gearbox and pipes on the casing.
- Published engine numbers often state a ratio rather than diameters (area ratio, bypass ratio):
  a ratio plus one diameter fixes the other. Write which numbers were derived and how.

## Where to look
- Manufacturer pages and press material (engine specification tables).
- NASA technical reports (`ntrs.nasa.gov`) and engine handbooks for NASA engines (F-1, J-2,
  RS-25, RL10): dimensions, drawings, contour data.
- FAA environmental documents for commercial engines (they quote nozzle sizes for plume
  calculations: the Starship work used one).
- Museum catalogue pages (Smithsonian `airandspace.si.edu`, others) for measured sizes of
  displayed engines, and their CC0 photos.
- NASA 3D Resources for a reference model (check its scale before using it).
- Wikipedia only to find primary sources.

## Photos
- Side-on photos of the engine alone are the most useful: the bell's profile, the powerhead's
  layout and the plumbing all show. Scale by a documented size in the same photo (exit diameter
  or overall length) and label everything measured "estimated from <photo>, scaled by <size>".
- Trace the nozzle's wall for a `traced` contour: 4-8 (r, z) points from the exit up to the
  throat, as fractions of the exit radius and of the nozzle length. Correct for perspective: in
  a photo from below or above the exit looks elliptical; use its long axis.
- Note how many of each part are visible and from which side; a photo shows half the engine.

## Modelling
1. Write the spec's `engine` block, then its `dimensions`: at least `nozzle` `diameter`
   (outer, at the exit), `throat_diameter`, `area_ratio`, `length`, and the overall height.
   These measure the built geometry, so a wrong contour or a mixed-up radius shows.
2. Build with `npm run model <engine>`; read the check table, then the sheet and close-ups
   (powerhead, nozzle lip, gimbal). Compare the side view with the side photo.
3. Add plumbing as `parts` in the spec (pumps, pipes, boxes, actuators), each with its source.
4. Check the `simple` version too (`engines.place(..., lod="simple")`): it is what vehicles
   show, so it has to keep the silhouette (nozzle, chamber, powerhead).

## Putting an engine on a vehicle
- List it in the vehicle's spec: `"engines": ["<engine>"]`, then in the vehicle's probe
  `engines.place(engines.load(spec, "<engine>"), "<name>", location, direction, lod="simple")`.
- `direction` is the engine's thrust axis from the exit up through the engine (on a rocket
  standing on its engines, (0, 0, 1)). The exit centre goes at `location`.
- Watch the vehicle's triangle budget: 33 engines at full detail don't fit.
- An engine's spec change marks every vehicle that lists it as behind; rebuild those too.

## Lessons from the F-1
- Agree on what a reference shows before modelling it. Describe it back to the user (which
  part, where it sits, how many, what shape) and get a yes. On the F-1, plates went on the
  wrong bands, tube crowns showing between double rings were read as plates, and ribs as
  bare tubes; each cost a round.
- Look early for one detailed illustration or cutaway of the whole engine (the F-1 used
  Steve Karp's, HistoryNet). Manuals and photos give sizes; an illustration shows how the
  parts are put together: band layers, straps, the dome, ducts, the interface panel. List it
  in `sources` with its page URL, and keep a copyrighted image out of the repo.
- Fittings are rarely a uniform pattern. Brackets come in clusters, dense rows on some bands
  and sparse groups on others, and nozzles in layers with their own band spacing, colour and
  fittings. Use per-ring `angles` lists and groups of `hoops` rather than "N evenly round".
- The outside of a nozzle is not its inner contour: covers, bands and manifolds hide the
  throat. Give the bell an `outer_profile`, but keep it shaped like a bell (wall angle easing
  towards the exit). A traced illustration outline can come out as a cone; check its slope
  from top to bottom, not just its end points.
- Every change in size can collide with a neighbour. Widening the F-1's bell pushed it into
  the heat exchanger, and moving that opened a gap at the turbopump. After each geometry change,
  look for parts cutting into the body of revolution and for parts no longer touching what they
  hang from.
- Compare renders taken from the reference's own viewpoint, side by side with it. That
  shows what is wrong far faster than the check table or the sheet.
- Detail fills the budget fast (hundreds of plates and brackets). Leave out faces that can't
  be seen (a band ring's inside, a plate's back and bottom) before thinning the detail.
- Write new features into `lib/engines.py` as options any engine can use (outer profile,
  ribs, hoop groups, double rings, straps, dome powerhead), so the next engine starts with them.
- A change to `lib/engines.py` only affects engines and the vehicles that list them. While
  working, rebuild those (and `testengine`) only, not every model; `published.py` still asks
  for the others before publishing.
