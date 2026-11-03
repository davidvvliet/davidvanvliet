# Writes the STM32N657 (VFBGA178) symbol into startracker.kicad_sym and its footprint into
# footprints/startracker.pretty: KiCad's libraries have neither.
#   python3 symbols/stm32n657.py
# Balls from stm32n657_vfbga178.json (datasheet DS14791 Rev 11, Figure 10 and Table 18).
# Footprint from DS14791 Table 134 (VFBGA178 mechanical data) and Table 135 (PCB design rules, 0.80 mm pitch):
#   D = E = "12.00 BSC", D1 = E1 = "10.40 BSC", e "0.80 BSC", N "178", Dpad "0.400 mm", Dsm "0.470 mm typ.",
#   stencil opening "0.400 mm". Pads are non-solder-mask-defined (the mask opening Dsm is larger than the pad).
import json, os, re, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
HARNESS = os.path.dirname(HERE)
ROWS = "ABCDEFGHJKLMNP"          # Figure 10: rows A to P without I and O, columns 1 to 14
BALLS = json.load(open(os.path.join(HERE, "stm32n657_vfbga178.json")))["balls"]
NAME = "STM32N657I0H3Q"           # DS14791 section 7: I = 178 balls, 0 = no flash, H = VFBGA, 3 = -40 to 125 °C, Q = internal SMPS
FP = "ST_VFBGA-178_12x12mm_Layout14x14_P0.8mm"
DATASHEET = "https://www.st.com/resource/en/datasheet/stm32n657a0.pdf"

def uid(*k): return str(uuid.uuid5(uuid.NAMESPACE_URL, "stm32n657/" + "/".join(map(str, k))))

# ---- footprint ----
def footprint():
    P, BODY, PAD, MASK = 0.8, 12.0, 0.400, 0.470
    half = (len(ROWS) - 1) * P / 2                       # 5.2: the outer balls, D1 / 2
    s, b = [], BODY / 2
    def line(x0, y0, x1, y1, layer, w):
        s.append(f'\t(fp_line (start {x0:g} {y0:g}) (end {x1:g} {y1:g}) (stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{uid("l", len(s))}"))')
    # Fab: the body with A1's corner cut (DS14791 Table 134 note 8: the A1 corner is marked on top)
    c = 1.0
    for a, z in [((-b + c, -b), (b, -b)), ((b, -b), (b, b)), ((b, b), (-b, b)), ((-b, b), (-b, -b + c)), ((-b, -b + c), (-b + c, -b))]:
        line(*a, *z, "F.Fab", 0.1)
    # Silk: corners only, 0.11 outside the body; a filled triangle at A1
    o, k = b + 0.11, 1.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            if (sx, sy) == (-1, -1): continue
            line(sx * o, sy * o, sx * (o - k), sy * o, "F.SilkS", 0.12); line(sx * o, sy * o, sx * o, sy * (o - k), "F.SilkS", 0.12)
    line(-o + k, -o, -o + 0.5, -o, "F.SilkS", 0.12); line(-o, -o + k, -o, -o + 0.5, "F.SilkS", 0.12)
    s.append(f'\t(fp_poly (pts (xy {-o:g} {-o:g}) (xy {-o - 0.5:g} {-o:g}) (xy {-o:g} {-o - 0.5:g})) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS") (uuid "{uid("p1")}"))')
    cy = b + 1.0                                          # courtyard 1 mm round the body, as KiCad's BGAs
    s.append(f'\t(fp_rect (start {-cy:g} {-cy:g}) (end {cy:g} {cy:g}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") (uuid "{uid("cy")}"))')
    pads = []
    for ball in BALLS:
        r, col = ROWS.index(ball[0]), int(ball[1:])
        x, y = -half + (col - 1) * P, -half + r * P
        pads.append(f'\t(pad "{ball}" smd circle (at {x:.4g} {y:.4g}) (size {PAD} {PAD}) (property pad_prop_bga) '
                    f'(layers "F.Cu" "F.Mask" "F.Paste") (solder_mask_margin {(MASK - PAD) / 2:.3f}) (uuid "{uid("pad", ball)}"))')
    text = lambda name, val, y, layer, hide="": (
        f'\t(property "{name}" "{val}" (at 0 {y:g} 0) (layer "{layer}"){hide} (uuid "{uid("prop", name)}") (effects (font (size 1 1) (thickness 0.15))))')
    out = [f'(footprint "{FP}"', '\t(version 20260206)', '\t(generator "circuit_harness")', '\t(generator_version "10.0")', '\t(layer "F.Cu")',
           f'\t(descr "ST VFBGA178 (B0GL), 12x12 mm, 0.8 mm pitch, 14x14 grid less 18 centre balls; DS14791 Rev 11 Tables 134-135, {DATASHEET}")',
           '\t(tags "BGA VFBGA178 STM32N6")',
           text("Reference", "REF**", -b - 1.6, "F.SilkS"), text("Value", FP, b + 1.6, "F.Fab"),
           text("Datasheet", DATASHEET, 0, "F.Fab", " (hide yes)"), text("Description", "", 0, "F.Fab", " (hide yes)"),
           '\t(attr smd)', *s,
           f'\t(fp_text user "${{REFERENCE}}" (at 0 0 0) (layer "F.Fab") (uuid "{uid("ref")}") (effects (font (size 1 1) (thickness 0.15))))',
           *pads, '\t(embedded_fonts no)',
           '\t(model "${CIRCUIT_3DMODELS}/ST_VFBGA-178.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))', ')']
    path = os.path.join(HARNESS, "footprints", "startracker.pretty", f"{FP}.kicad_mod")
    open(path, "w").write("\n".join(out) + "\n")
    return len(pads)

# ---- symbol ----
# Pin types: supplies power_in (a repeated supply is one visible pin, the rest stacked behind it as passive, so
# they join without each needing a wire); the SMPS's switch node passive; GPIOs bidirectional.
SUPPLY = ["VDD", "VBAT", "VDDIO3", "VDDIO4", "VDD33USB", "VDDA18AON", "VDDA18PMU", "VDDA18PLL", "VDDA18CSI", "VDDA18ADC",
          "VDDA18USB", "VREF+", "VDDSMPS", "VLXSMPS", "VFBSMPS", "VDDCORE", "VDDCSI", "V08CAP"]
SYSTEM = ["NRST", "PDR_ON", "PWR_ON", "BOOT0", None, "CSI_CKP", "CSI_CKN", "CSI_D0P", "CSI_D0N", "CSI_D1P", "CSI_D1N", "CSI_REXT", None,
          "OTG1_HSDP", "OTG1_HSDM", "OTG1_ID", "OTG1_TXRTUNE", "OTG2_HSDP", "OTG2_HSDM", "OTG2_ID", "OTG2_TXRTUNE",
          "UCPD1_CC1", "UCPD1_CC2", None, "NC"]
GROUND = ["VSS", "VSSA", "VSSAON", "VSSAPMU", "VSSSMPS", "VREF-"]
TYPE = {"VLXSMPS": "passive", "V08CAP": "passive", "VFBSMPS": "input", "PWR_ON": "output", "NRST": "bidirectional",
        "PDR_ON": "input", "BOOT0": "input", "NC": "no_connect"}

def symbol():
    by_name = {}
    for ball, n in BALLS.items(): by_name.setdefault(n, []).append(ball)
    def gpio_key(n):
        m = re.match(r"P([A-Z])(\d+)", n); return (m.group(1), int(m.group(2)))
    gpios = sorted((n for n in by_name if re.match(r"P[A-Z]\d+", n)), key=gpio_key)
    left_ports, right_ports = "ABC", "DEFGHN"
    def column(names_ports):
        col, last = [], None
        for n in names_ports:
            p = gpio_key(n)[0]
            if last and p != last: col.append(None)
            col.append(n); last = p
        return col
    left = SUPPLY + [None] + SYSTEM + [None] + column([g for g in gpios if gpio_key(g)[0] in left_ports])
    right = column([g for g in gpios if gpio_key(g)[0] in right_ports])
    used = set(SUPPLY + SYSTEM + GROUND + gpios) - {None}
    assert used == set(by_name), set(by_name) ^ used
    G, L = 2.54, 5.08                                     # grid and pin length
    rows = max(len(left), len(right))
    W = 30 * G
    top = (rows // 2) * G
    bottom = top - (rows + 1) * G
    pins = []
    def pin(n, x, y, ang, typ=None):
        for i, ball in enumerate(sorted(by_name[n], key=lambda k: (ROWS.index(k[0]), int(k[1:])))):
            t = typ or TYPE.get(n, "bidirectional")
            hide = " (hide yes)" if i else ""
            if i: t = "passive"
            pins.append(f'\t\t\t(pin {t} line (at {x:g} {y:g} {ang}) (length {L:g}){hide} (name "{n}" (effects (font (size 1.27 1.27)))) '
                        f'(number "{ball}" (effects (font (size 1.27 1.27)))))')
    for i, n in enumerate(left):
        if n: pin(n, -W / 2 - L, top - i * G, 0, "power_in" if n in SUPPLY and n not in TYPE else None)
    for i, n in enumerate(right):
        if n: pin(n, W / 2 + L, top - i * G, 180)
    gx0 = -(len(GROUND) - 1) * 2 * G / 2
    for i, n in enumerate(GROUND):
        pin(n, gx0 + i * 2 * G, bottom - L, 90, "power_in")
    prop = lambda k, v, x, y, hide="": f'\t\t(property "{k}" "{v}" (at {x:g} {y:g} 0){hide} (effects (font (size 1.27 1.27))))'
    desc = ("Arm Cortex-M55 800 MHz MCU with NPU, 4.2 MB SRAM, MIPI CSI-2, no internal flash, VFBGA178 12x12 mm 0.8 mm pitch; "
            "balls from DS14791 Rev 11 Figure 10 and Table 18")
    return "\n".join([
        f'\t(symbol "{NAME}" (exclude_from_sim no) (in_bom yes) (on_board yes)',
        prop("Reference", "U", -W / 2, top + G), prop("Value", NAME, W / 2 - 10 * G, top + G),
        prop("Footprint", f"startracker:{FP}", 0, 0, " (hide yes)"), prop("Datasheet", DATASHEET, 0, 0, " (hide yes)"),
        prop("Description", desc, 0, 0, " (hide yes)"),
        f'\t\t(symbol "{NAME}_0_1" (rectangle (start {-W / 2:g} {top + G / 2:g}) (end {W / 2:g} {bottom:g}) (stroke (width 0.254) (type default)) (fill (type background))))',
        f'\t\t(symbol "{NAME}_1_1"', *pins, '\t\t)', '\t)'])

def write_symbol():
    path = os.path.join(HERE, "startracker.kicad_sym")
    text = open(path).read()
    new = symbol()
    m = re.search(rf'\n\t\(symbol "{NAME}".*?\n\t\)(?=\n)', text, re.S)
    text = text[:m.start()] + "\n" + new + text[m.end():] if m else text.rstrip()[:-1].rstrip() + "\n" + new + "\n)\n"
    open(path, "w").write(text)

if __name__ == "__main__":
    print(footprint(), "pads"); write_symbol()
