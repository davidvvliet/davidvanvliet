---
name: model-board
description: Build a circuit board with the circuit harness (frontend/scripts/circuit) for the site's /circuit page: write its recipe from building blocks, generate, route and check it with KiCad and Freerouting, and show it on the models dashboard. Use when asked to build, fix, change or publish a circuit board, import an open-source KiCad board, or change the circuit harness.
---

# Building a board

The harness lives in `frontend/scripts/circuit` (read its README first). Every board rebuilds from
the repo: an imported board from its KiCad files, our own from `recipe.json` and `blocks/`.
Nothing is edited by hand in KiCad's editors; a fix goes into the recipe, a block or `lib/`.

## Rules
- Blocks come from `research-board`: every part and value sourced. Never add a part or value from memory.
- Work in your own git worktree (repo CLAUDE.md). The dashboard (`localhost:3000/models?dashboard`)
  shows the board from whichever worktree built it last.
- A build passes only when KiCad's checks pass: design rules 0 errors, unconnected 0, electrical
  0 errors and schematic-matches-board 0 (once the board has a schematic). Warnings are listed, never
  a reason to stop; fix them when they point at something real.
- Web budget: at most 1.5 MB and 300,000 triangles; every part has a 3D model.
- `--publish` (copies the build to `public/circuit/`, the live page) only with the user's go-ahead,
  like `model:approve`.
- Imported boards: only with a licence that allows it, credited in `board.json` with the licence quoted.
- A change to `lib/` or a block affects every board that uses it: rebuild them all and compare.

## Loop
1. Blocks exist (`research-board`). Write `boards/<board>/recipe.json` (`templates/recipe.json`):
   board size, rules (`templates/rules.kicad_pro`), ground net, each block's instance and position,
   and the `connect` groups (`instance.port`). Check every port a block needs (power in, ground) is
   joined; unjoined ports are left open on purpose or are a mistake.
2. `python3 scripts/circuit/build.py <board>` (from `frontend/`). Read its check table.
3. Fix in order: generation errors (a footprint not found, a port name wrong), then
   unconnected (blocks too close for the router, or a port not joined), then design-rule errors
   (placement: move blocks apart; a block's own traces: fix the block). The generated KiCad board is
   in `out/<board>/kicad/board.kicad_pcb` for looking at in KiCad.
4. Tell the user the board is up on the dashboard (no screenshots): the blocks, the checks, and what
   is still open.
5. On the user's go-ahead: `build.py <board> --publish`, commit and push to main.

## Importing an open-source board
`boards/<board>/` with its `.kicad_pcb`, `.kicad_sch`, `.kicad_pro`, LICENSE and `board.json`
(title, purpose, pcb, sch, source with licence quote, `model_renames` for renamed 3D models). The
blocks are the schematic's titled boxes (`lib/sections.py`). Its checks show the designer's own result.

## Routing
`build.py` routes recipe boards (`lib/route.py`, README "Routing"). If routing keeps failing: give the
blocks more room, move the busiest block's ports toward each other, or add a via-friendly gap. Don't
change the clearance margin or the board rules to make a check pass.
