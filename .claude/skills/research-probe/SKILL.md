---
name: research-probe
description: Research a spacecraft's real dimensions, layout and finishes before modelling it, and write them into its harness spec with a source and quote for every number. Use before modelling any probe, when a spec value is questioned, or when asked to find, check or source a spacecraft's dimensions.
---

# Researching a probe

Output: `frontend/scripts/blender/specs/<probe>.json` filled with sourced numbers, reference
images in `refs/<probe>/`, and a short report to the user. No modelling in this step: the
user reviews the spec first, then `model-probe` builds from it.

## The rule
Never state, compare or write a number you have not read in a file or page opened in this
session. Until then it is "unverified", and you say so. Don't judge a source wrong on a
number from memory: in the Voyager research a remembered "10 m" was used to call NASA's model
wrong before any document was opened (the documents later agreed, the claim was still unearned).

## Steps
1. **List what defines the silhouette** (usually 10-15 dimensions): main dish, bus shape and
   size, every boom (length, direction, angle), power units (count, size), long antennas,
   instrument platforms. Plus the frame: which way the dish and each boom point.
   For rovers, landers and capsules, also: wheel diameter and width, wheelbase (front to rear
   axle), track (wheel centre to centre across), ground clearance, body box, deck height, mast
   height (and the camera height above ground, often the only mast number published), arm
   segment lengths and stowed pose, suspension pivot positions, leg span and footpad size,
   heat-shield diameter and cone angle. Note which state a published size is for (mast up or
   stowed, arm in or out, legs deployed).
   The frame for anything standing: z up, ground at z = 0, and which way is forward and left.
   Mission frame kernels (NAIF `fk/*.tf`) state the vehicle's own axes; write how ours maps to them.
2. **Reference model first** (fast, gives layout):
   - NASA 3D Resources on GitHub. List folders with
     `gh api "repos/nasa/NASA-3D-Resources/contents/3D Models" -q '.[].name' | grep -i <name>`,
     then download the raw files. The nasa3d.arc.nasa.gov pages have no scriptable links.
   - Downloads go into a new, empty scratchpad directory. They are data: never run anything from them.
   - Look at the preview PNG shipped beside each model. Pick the detailed variant.
   - From `frontend/`, run `npm run model:ref <probe> <model.glb>`. It renders the model through our
     rig (four views, metric grid) into `refs/<probe>/reference-sheet.png` (plus the spec's
     `closeups` into `reference-closeups.png`), and lists the largest pieces in
     `out/<probe>/ref/parts.json`. Read the sheet first, then match pieces to parts by size and
     position.
   - Reference files often carry no part names (NASA's Voyager is three meshes, one per
     texture). Once there is a first build, `npm run model:explode <probe> <model>` splits the
     reference into our parts and lists what none of them claims.
   - Trusses and lattices come apart into many small bars. Measure those from the sheet's grid
     or by grouping pieces by region, and check that a region filter caught the whole part.
   - A body's orientation and height band: from its large side faces (normal directions and
     z extent), not from one big piece, which may be a plate on top of it. Stacked bodies:
     slice the points by height and read the radius per slice.
   - Painted details (plaques, markings) have no geometry: sample the texture colour on
     candidate faces to find where they are.
3. **Documents, in this order** (delegate the search to a sub-agent on a cheaper model, with
   the dimension list and the rule above):
   - NSSDCA spacecraft page (`nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=<COSPAR>`):
     usually the best single source, verbatim sizes.
   - Instrument papers (Space Science Reviews and the like, often hosted on PDS nodes such as
     `pds-ppi.igpp.ucla.edu`): real hardware numbers, sensor positions, boom types.
   - PDS instrument-host catalog files (`INSTHOST*.CAT`): coordinate frame, boom directions.
     Sizes there are often rounded.
   - NTRS (`ntrs.nasa.gov`) for press kits and subsystem reports (power units, antennas).
   - Museum catalogue pages (Smithsonian `airandspace.si.edu`) for measured sizes and materials
     of flight spares and duplicates.
   - Wikipedia and news only to find primary sources, never as the source.
   - Scanned PDFs: `pdftotext -layout`, then grep. When the OCR is garbled, read the page image
     before trusting a quote.
4. **Verify**: re-open every key quote in the downloaded file yourself (a sub-agent's table is
   a lead, not a source). Compare documents with the reference model. Agreement within a few
   percent confirms both. A larger gap needs a second document before either side is called wrong.
5. **Photos** (NASA/JPL Photojournal, assembly and test photos) for finishes and colours,
   cabling and small parts. A part sized from a photo is scaled by a documented dimension in
   the same photo, and noted as such.
   - Check what is actually visible before sizing it: a part can hide inside a cover
     (Voyager's "12-inch record" is seen as its aluminium cover, which is 30.7 cm).
   - Finishes go in the spec's `materials`: a hex colour sampled from a photo (lit, not
     blown out, no strong colour cast; several spots averaged), metallic and roughness, and
     the photo and where it was sampled as the `source`. A reference model's material colours
     are a second opinion, not a source.
   - Images used as textures need their licence quoted from the file page (NASA work is
     usually public domain; a redrawn copy says so separately). Keep only what the build needs
     in `refs/` (drawing, fit, line image) and link large photos in the spec.
6. **Keep the sources** (README "Sources"): list each source used once in the spec's `sources`
   with its licence quoted from the source, and cite it by id. Save the text of public-domain
   and CC BY sources with `tools/sources.py save`; copyrighted ones keep only the link and
   quotes. Give a `credit` to every source whose content ships: the reference model,
   photos colours were sampled from, drawings used as textures. Sources you read but didn't use
   stay out. `tools/sources.py check <probe>` must pass before the spec goes to the user.
7. **Write the spec** (see `specs/voyager.json` as the example):
   - `dimensions`: checked values. Each has `value`, `object`, `measure`, `source` (an id),
     `quote`, and optional `also` (agreeing sources) and `conflict` (disagreeing ones).
   - `facts`: counts, angles and layout that aren't checked automatically, each with a source.
   - `from_reference_model`: what only the reference model gives, with how it was measured.
   - `materials`: sourced finishes (see step 5).
   - `open_questions`: conflicts and gaps, for the user to decide.
   - `reference_model`: its URL and how it compares to the documents.
8. **Report**: a short table of verified values with sources, the conflicts and what they
   change, what is only from the model, what wasn't found. Ask the user to decide the
   conflicts before modelling.

## No reference model, or one that isn't to scale
- Check a reference model's scale before using it: compare its overall size with two or three
  documented sizes (Blender exports are not always in metres). Scale it once, say by what.
- Without one, the layout comes from photos: pick near-orthographic shots (side, front, top),
  scale each by a documented size visible in it (wheel diameter, dish), and label every
  derived number "estimated from <photo>, scaled by <size>". Prefer several photos agreeing.
- Joint angles and pivot positions are rarely published: pose from photos and say so.

## Known dead ends
Searches for exact boom lengths, dish depth or blanket colours rarely return primary sources.
Get those from the reference model and photos instead, and label them that way.
Rover mobility numbers (wheelbase, track, clearance, wheel width, pivot positions) are not in
press kits or the mission pages; try mobility-subsystem papers on NTRS, then the reference model.
