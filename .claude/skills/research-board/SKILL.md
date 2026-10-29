---
name: research-board
description: Research a circuit board before it is built with the circuit harness (frontend/scripts/circuit): choose its parts, read their datasheets and reference designs, and write the building blocks it needs with a source and quote for every part and value. Use when asked for a new board ("a camera board", "a motor driver"), a new block, or to check a block's values.
---

# Researching a board

Output: the blocks the board needs in `frontend/scripts/circuit/blocks/<block>.json`
(`templates/block.json`), each part and value sourced, and a short plan for the user. No board is
built in this step: the user agrees to the plan first, then `model-board` builds it.
Read `frontend/scripts/circuit/README.md` first.

## The rule
Never write a part, value, pin or dimension you have not read in a document opened in this session.
Until then it is "unverified", and you say so. The same rule as `research-probe`.

## Steps
1. **Turn the request into a plan**: what the board does, the main chip(s) that do it, how it is
   powered, what it connects to (USB, headers, sensors). Find two or three real candidates (chips
   that are made, documented and sold), pick one with reasons, and ask the user before going on.
2. **Reuse blocks**: list `blocks/` and use what exists (USB-C power, 3.3 V regulator, RP2040 core,
   LED...). Check a reused block's ports fit (voltage, current, which pins).
3. **Documents for each new block, in this order** (delegate the downloading to a sub-agent on a
   cheaper model, with the list of values to find and the rule above):
   - The chip maker's datasheet: pinout, recommended circuit (the "typical application"), capacitor
     and resistor values, layout guidelines, package drawing.
   - The maker's reference design or evaluation board (schematic and layout), often the best layout source.
   - Application notes for the hard parts (crystals, USB, switching regulators, RF, cameras).
   - Standards for interfaces (USB Type-C spec for CC resistors, and so on).
   - Open-source boards (KiCad files, licence that allows reuse: MIT, CERN-OHL-P, CC BY) for a proven
     layout; `lib/extract.py` lifts a block out of one.
   - Distributor pages only to find the maker's documents, never as the source. Archive.org is not a source.
   - Downloads go into a new empty scratchpad folder each; never run anything from them;
     `pdftotext -layout`, then grep; read a page image when the text is garbled (package tables).
4. **Verify**: re-open every quote in the downloaded text yourself (a sub-agent's table is a lead,
   not a source). Where the open board and the datasheet disagree, write both in `open_questions`.
5. **Parts in KiCad**: each part's symbol and footprint by their KiCad library names
   (`~/Applications/KiCad/KiCad.app/Contents/SharedSupport/{symbols,footprints}`). Check the
   footprint against the datasheet's package drawing (body, pitch, exposed pad). A footprint KiCad
   doesn't have is copied from an open board into `footprints/<board>.pretty` (licence allowing) or
   flagged: drawing one from the package drawing is its own task.
6. **Write the block**: parts (ref, value, symbol, footprint, `source` id and page, `quote`), nets,
   ports (with `kind`: power_in, power_out, ground, data, gpio...), layout (placement, the
   datasheet's layout rules), `sources` (with licence: copyrighted datasheets keep only link and
   quotes) and `open_questions`.
7. **Report**: per block, a short table of the values confirmed and where; the open questions;
   what isn't sourced yet. Ask the user to decide conflicts before building.

## Known gaps
Crystal load capacitance is often not in the crystal maker's general sheet (it is in the part's
ordering code or its own sheet). Connector makers' datasheets are often behind download walls
(HRO's returned 403): note it and use the footprint from an open board or KiCad's library.
