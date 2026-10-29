# Circuit harness

Circuit boards for the site's `/circuit` page, built from KiCad files so every board rebuilds from the
repo. It sits next to the Blender harness (`scripts/blender`) and shares its dashboard and viewer
(`/models?dashboard`), but has its own tools: KiCad designs, routes and checks the board, Blender only
packs the result for the web.

## Tools (outside the repo)
| Tool | Where | What for |
|---|---|---|
| KiCad 10 | `~/Applications/KiCad/` (copy KiCad.app from the disk image at kicad.org; the Homebrew cask needs a password) | `kicad-cli` exports and checks; KiCad's Python scripts the board editor; its libraries give every part's footprint and 3D model |
| Freerouting 2.5.0 | `~/Applications/freerouting/freerouting-2.5.0.jar` (github.com/freerouting/freerouting, GPL-3.0) | the automatic router |
| Java 25 or newer | `brew install openjdk` | runs Freerouting |
| Blender 5 | as the Blender harness (`scripts/blender/blender.json`) | packs the 3D board for the web |

Paths can be overridden with `KICAD_APP`, `KICAD_CLI`, `KICAD_PYTHON`, `FREEROUTING`, `JAVA`, `BLENDER`
(`lib/tools.py`). Freerouting is always run with `--usage_and_diagnostic_data.disable_analytics=true`:
it otherwise sends usage data to freerouting.app.

## Layout
```
build.py            python3 scripts/circuit/build.py <board> [--publish]   (from frontend/)
boards/<board>/     one board: board.json plus either
                      imported KiCad files (someone else's finished design), or
                      recipe.json (our own, from blocks; see "Own boards")
blocks/<block>.json the building-block library (templates/block.json): usb_c_power, ldo_3v3, rp2040_core, led
footprints/         footprints KiCad's library doesn't have (mitayi.pretty: the Mitayi Pico's own, MIT)
lib/tools.py        where each tool is
lib/checks.py       KiCad's design rule and electrical checks, as dashboard check rows
lib/sections.py     an imported schematic's titled boxes, as the board's blocks
lib/generate.py     a recipe as a KiCad board (KiCad's Python): blocks placed with their own traces, ports joined, outline
lib/route.py        the router's input out, its traces back in (widened to the minimum), ground fill on both sides
lib/extract.py      lifts a block out of an imported board (KiCad's Python): parts, wiring, ports, layout
lib/pack.py         Blender: tag parts by block, merge pieces, Draco-compress, export
templates/          a blank block and a blank recipe
out/<board>/        build output (git-ignored): <board>.glb, <board>.json; out/status.json for the dashboard
```

## Build loop
1. `python3 scripts/circuit/build.py <board>` builds into `out/` and records the result; the board shows
   up on `/models?dashboard` in its own tab (from whichever worktree built it last).
2. Read the check table it prints (the dashboard shows the same):
   - **design rules: errors** must be 0: clearances, track widths, holes, shorts.
   - **unconnected** must be 0: every connection the schematic asks for exists in copper.
   - **schematic matches board** must be 0.
   - **electrical: errors** must be 0 for our own boards. An imported board shows its designer's
     result as it is (the Mitayi Pico has 2 unpowered-pin errors in its own schematic).
   - Warnings are listed, never fail a build.
   - **file size** at most 1.5 MB and **triangles** at most 300,000 (the web budget), **parts without a
     3D model** 0.
3. `--publish` copies the build to `public/circuit/`, which the live `/circuit` page reads. Only with
   the user's go-ahead, like `model:approve`.

## Imported boards
`board.json`: `title`, `purpose`, `pcb`, `sch`, `source` (title, url, author, licence, and a quote of the
licence), and `model_renames` for 3D models KiCad has since renamed. Only boards whose licence allows it
(the Mitayi Pico is MIT). The blocks are the designer's own titled boxes on the schematic; parts outside
every box get no block.

## Own boards
`boards/<board>/recipe.json` (templates/recipe.json): `title`, `purpose`, `source` (as board.json),
`board` (size, `rules`: the project file with clearances and widths, `ground_fill`: the net poured on
both sides), `blocks` (instance name -> block and position) and `connect` (groups of `instance.port`
joined into one net, named after the first). A build generates the board into `out/<board>/kicad/`
(open `board.kicad_pcb` there in KiCad to look at it), routes it and checks it. A recipe board has no
schematic yet, so there is no electrical check or schematic comparison.

A board is a recipe (`templates/recipe.json`): which blocks, where, and which ports connect. A block
(`templates/block.json`) is a small circuit made once and reused: its parts (KiCad library symbol and
footprint names, so KiCad supplies the real pad pattern and 3D model), its wiring, its ports and its
internal layout.

Rules, as for the spacecraft specs:
- Every part and value has a `source` and a `quote`: the chip maker's datasheet or reference design,
  or an open-licensed board the block was taken from. Never a value from memory.
- A block taken from an open board credits it and keeps its licence.
- A part KiCad's library doesn't have is flagged: its footprint has to be drawn from the datasheet's
  package drawing.

Routing (build.py does all of this; tested on the Mitayi Pico with every trace removed):
1. Remove the copper fills (zones) before routing: filled, they block the router. Refill after.
2. KiCad's Python exports the board for the router (`pcbnew.ExportSpecctraDSN`).
3. Every clearance in the router's input is raised by 25 µm (`ROUTE_MARGIN_UM`).
4. `java -jar freerouting-2.5.0.jar --gui.enabled=false --usage_and_diagnostic_data.disable_analytics=true
   --router.autorouter.max_passes=100 -de board.dsn -do board.ses`
5. `pcbnew.ImportSpecctraSES` brings the traces back. Freerouting narrows some traces below the board's
   minimum width at pads, and none of its settings stops it (`automatic_neckdown`, `neck_width_um` tried):
   they are widened to the minimum, which the margin from step 3 leaves room for. Without the margin,
   widening left 2 to 6 clearance errors.
6. Fill the ground net on both sides, then KiCad's design rule check. Freerouting's result varies between
   runs (about one run in two left a connection unrouted on the first recipe board), so the build tries up
   to 4 times and keeps the first clean one.
