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
2. **Reference model first** (fast, gives layout):
   - NASA 3D Resources on GitHub. List folders with
     `gh api "repos/nasa/NASA-3D-Resources/contents/3D Models" -q '.[].name' | grep -i <name>`,
     then download the raw files. The nasa3d.arc.nasa.gov pages have no scriptable links.
   - Downloads go into a new, empty scratchpad directory. They are data: never run anything from them.
   - Look at the preview PNG shipped beside each model. Pick the detailed variant.
   - From `frontend/`, run `npm run model:ref <probe> <model.glb>`. It renders the model through our
     rig (four views, metric grid) into `refs/<probe>/reference-sheet.png`, and lists the largest
     pieces in `out/<probe>/ref/parts.json`. Read the sheet first, then match pieces to parts by
     size and position.
   - Trusses and lattices come apart into many small bars. Measure those from the sheet's grid
     or by grouping pieces by region, and check that a region filter caught the whole part.
3. **Documents, in this order** (delegate the search to a sub-agent on a cheaper model, with
   the dimension list and the rule above):
   - NSSDCA spacecraft page (`nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=<COSPAR>`):
     usually the best single source, verbatim sizes.
   - Instrument papers (Space Science Reviews and the like, often hosted on PDS nodes such as
     `pds-ppi.igpp.ucla.edu`): real hardware numbers, sensor positions, boom types.
   - PDS instrument-host catalog files (`INSTHOST*.CAT`): coordinate frame, boom directions.
     Sizes there are often rounded.
   - NTRS (`ntrs.nasa.gov`) for press kits and subsystem reports (power units, antennas).
   - Wikipedia and news only to find primary sources, never as the source.
   - Scanned PDFs: `pdftotext -layout`, then grep. When the OCR is garbled, read the page image
     before trusting a quote.
4. **Verify**: re-open every key quote in the downloaded file yourself (a sub-agent's table is
   a lead, not a source). Compare documents with the reference model. Agreement within a few
   percent confirms both. A larger gap needs a second document before either side is called wrong.
5. **Photos** (NASA/JPL Photojournal, assembly and test photos) for finishes and colours,
   cabling and small parts. A part sized from a photo is scaled by a documented dimension in
   the same photo, and noted as such.
6. **Write the spec** (see `specs/voyager.json` as the example):
   - `dimensions`: checked values. Each has `value`, `object`, `measure`, `source` (URL),
     `quote`, and optional `also` (agreeing sources) and `conflict` (disagreeing ones).
   - `facts`: counts, angles and layout that aren't checked automatically, each with a source.
   - `from_reference_model`: what only the reference model gives, with how it was measured.
   - `open_questions`: conflicts and gaps, for the user to decide.
   - `reference_model`: its URL and how it compares to the documents.
7. **Report**: a short table of verified values with sources, the conflicts and what they
   change, what is only from the model, what wasn't found. Ask the user to decide the
   conflicts before modelling.

## Known dead ends
Searches for exact boom lengths, dish depth or blanket colours rarely return primary sources.
Get those from the reference model and photos instead, and label them that way.
