# Hubble Space Telescope, as after Servicing Mission 4 (2009). Metres. Frame (spec facts.frame):
# z = V1 with the aft bulkhead at z = 0 and the aperture at +z, x = +V2 (solar arrays on +-V2),
# y = +V3 (high-gain antennas on +-V3, aperture-door hinge on +V3). Body stations come from
# Lockheed drawing 4171929: z = (STA - 100 in) x 0.0254. Checked sizes are in the spec's
# `dimensions`, positions in its `facts`; anything else is marked as estimated here.
import math
import os
from lib import materials, parts, textures, tiling

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HARNESS, "out", "hubble", "textures")

IN = 0.0254

def bpy_obj(name):
    import bpy
    return bpy.data.objects[name]

def sta(s):
    return (s - 100.0) * IN

def equipment_doors(R, z0, z1):
    """Twelve flat bay doors on the equipment section's flats (centred 15 + 30k deg from +V2),
    each built facing +x and turned into place. Door gaps, thickness and the radiator louvres
    (size and place) are estimated from sm4_photos s125e011763."""
    from mathutils import Matrix
    r_flat = R * math.cos(math.radians(15))
    w = 2 * R * math.sin(math.radians(15)) - 0.05
    h = (z1 - z0) - 0.08
    zm = (z0 + z1) / 2
    for k in range(12):
        a = 15 + 30 * k
        items = [((0.03, w, h), (r_flat + 0.015, 0, zm))]
        louvre = a in (75, 105)                       # either side of +V3
        objs = [parts.boxes(f"bay_door_{k + 1}", items, material="bay_doors")]
        if louvre:
            wz, ww = 0.6, 0.78
            zc = z1 - 0.06 - wz / 2
            x = r_flat + 0.03
            objs.append(parts.boxes(f"bay_door_{k + 1}_radiator", [((0.006, ww, wz), (x + 0.003, 0, zc))],
                                    material="black"))
            frame = [((0.05, ww + 0.06, 0.03), (x + 0.025, 0, zc + wz / 2 + 0.015)),
                     ((0.05, ww + 0.06, 0.03), (x + 0.025, 0, zc - wz / 2 - 0.015)),
                     ((0.05, 0.03, wz), (x + 0.025, ww / 2 + 0.015, zc)),
                     ((0.05, 0.03, wz), (x + 0.025, -ww / 2 - 0.015, zc)),
                     ((0.03, ww, 0.02), (x + 0.02, 0, zc))]
            slats = [((0.045, 0.012, wz), (x + 0.025, -ww / 2 + ww * (i + 0.5) / 11, zc)) for i in range(11)]
            objs.append(parts.boxes(f"bay_door_{k + 1}_louvres", frame + slats, material="bay_doors"))
        for obj in objs:
            obj.matrix_world = Matrix.Rotation(math.radians(a), 4, "Z") @ obj.matrix_world

def _frame(obj, centre, x_axis, y_axis, z_axis, scale=(1, 1, 1)):
    """Place a part built at the origin along world axes: its local x, y, z become the given
    world directions at `centre`, scaled (an ellipse from a disc)."""
    from mathutils import Matrix, Vector
    M = Matrix.Identity(4)
    for c, v, s_ in zip(range(3), (x_axis, y_axis, z_axis), scale):
        M.col[c][:3] = Vector(v).normalized() * s_
    M.col[3][:3] = centre
    obj.matrix_world = M @ obj.matrix_world
    return obj

def _az(a):
    return math.cos(math.radians(a)), math.sin(math.radians(a))

def aft_features(f, R):
    """Aft shroud doors, openings and panels, and the aft bulkhead's beams, vents, low-gain antenna
    and the Soft Capture Mechanism. Places from the spec's facts (measured on sm4_photos)."""
    A, B = f["aft_shroud_features"], f["aft_bulkhead_features"]
    with parts.assembly("aft_shroud_details"):
        def skin(name, az, z, dr, material):
            a0, a1 = az
            obj = parts.lathe(name, [(0, z[0]), (R + dr, z[0]), (R + dr, z[1]), (0, z[1])], segments=8,
                              sweep_deg=a1 - a0, roll_deg=(a0 + a1) / 2, material=material, smooth=True)
            return obj
        dz = A["door"]["z"]
        skin("aft_door_left", (A["door"]["az"][0], 90 - 0.3), dz, 0.008, "aft_fosr")
        skin("aft_door_right", (90 + 0.3, A["door"]["az"][1]), dz, 0.008, "aft_fosr")
        skin("aft_white_band", A["white_band"]["az"], A["white_band"]["z"], 0.006, "aft_white_panel")
        skin("aft_radiator", A["radiator"]["az"], A["radiator"]["z"], 0.006, "aft_white_panel")
        skin("aft_black_strip", A["black_strip"]["az"], A["black_strip"]["z"], 0.004, "black_tape")
        for k, o in enumerate(A["ovals"]):
            c, s_ = _az(o["az"])
            ov = parts.cylinder(f"aft_oval_{k + 1}", radius=0.5, length=0.012, segments=32, material="black")
            _frame(ov, (c * (R + 0.004), s_ * (R + 0.004), o["z"]), (-s_, c, 0), (0, 0, 1), (c, s_, 0),
                   (o["w"], o["h"], 1))
        c, s_ = _az(A["port"]["az"])
        parts.cylinder("aft_port", radius=A["port"]["d"] / 2, length=0.03, segments=32, material="black",
                       location=(c * (R - 0.01), s_ * (R - 0.01), A["port"]["z"]), direction=(c, s_, 0))
        parts.lathe("aft_port_rim", [(A["port"]["d"] / 2, 0), (A["port"]["d"] / 2 + 0.04, 0),
                                     (A["port"]["d"] / 2 + 0.04, 0.025), (A["port"]["d"] / 2, 0.025)],
                    closed=True, segments=32, material="aft_fosr",
                    location=(c * R, s_ * R, A["port"]["z"]), direction=(c, s_, 0))

    with parts.assembly("aft_bulkhead_details"):
        for k, a in enumerate(B["beams_az"]):
            c, s_ = _az(a)
            parts.box(f"aft_beam_{k + 1}", (R - 0.62, 0.1, 0.03), location=(c * (R + 0.62) / 2, s_ * (R + 0.62) / 2, -0.015),
                      roll_deg=a, material="beam_gold")
        for k, v in enumerate(B["vents"]):
            c, s_ = _az(v["az"])
            parts.disc(f"aft_vent_{k + 1}", radius=B["vent_d"] / 2, thickness=0.015,
                       location=(c * v["r"], s_ * v["r"], 0), direction=(0, 0, -1), material="vent_cover",
                       hole_material="black")
        L = B["lga"]
        c, s_ = _az(L["az"])
        parts.lathe("aft_lga", [(0, 0), (L["d"] / 2, 0), (L["d"] / 2, L["length"] * 0.7),
                                (L["d"] * 0.3, L["length"] * 0.95), (0, L["length"])],
                    segments=24, material="lga_white", location=(c * L["r"], s_ * L["r"], 0),
                    direction=(0, 0, -1))

    # Soft Capture Mechanism (pk125: about 72 in across, 24 in high): the grey docking ring at the
    # bottom (size from s125e011805) on three legs out to the berthing pins on the radial beams.
    S = B["scm_ring"]
    with parts.assembly("soft_capture"):
        h = 24 * IN
        parts.lathe("soft_capture_ring", [(S["r_in"], -h), (S["r_out"], -h), (S["r_out"], -h + S["thickness"]),
                                          (S["r_in"], -h + S["thickness"])], closed=True, segments=48,
                    material="scm_grey", smooth=False)
        legs = []
        for k, a in enumerate(B["beams_az"]):
            c, s_ = _az(a)
            # jaw's outer edge on the 36 in radius (72 in across)
            rp = 36 * IN - 0.09
            pin = (c * rp, s_ * rp, 0)
            for da in (-25, 25):
                c2, s2 = _az(a + da)
                foot = (c2 * (S["r_out"] - 0.03), s2 * (S["r_out"] - 0.03), -h + S["thickness"])
                legs.append(parts.strut(f"soft_capture_leg_{k + 1}{'ab'[da > 0]}", foot, pin, radius=0.035,
                                        material="scm_grey"))
            parts.box(f"soft_capture_jaw_{k + 1}", (0.18, 0.14, 0.1), location=(pin[0], pin[1], -0.05),
                      roll_deg=a, material="scm_grey")

def fittings(f, r_ls, r_fs, R_es, z_ls1):
    """Small fittings from drawing 4171929 (spec facts): magnetometers, forward LGA, grapple
    fixtures, magnetic torquers and scuff plates."""
    from mathutils import Vector
    with parts.assembly("fittings"):
        M = f["magnetometers"]
        for k, a in enumerate(M["az_deg"]):
            c, s_ = _az(a)
            sx, sy, sz = M["size"]
            r = (r_ls - 0.03 + M["r"]) / 2
            parts.box(f"magnetometer_{k + 1}", (M["r"] - r_ls + 0.03, sx, sz), location=(c * r, s_ * r, sta(M["sta"])),
                      roll_deg=a, material="foil_silver")
        L, La = f["lga_forward"], f["aft_bulkhead_features"]["lga"]
        c, s_ = _az(L["az_deg"])
        z = sta(L["sta"])
        parts.box("lga_forward_mount", (L["r"] - r_ls + 0.05, 0.08, 0.08), location=(c * (L["r"] + r_ls - 0.05) / 2, s_ * (L["r"] + r_ls - 0.05) / 2, z),
                  roll_deg=L["az_deg"], material="foil_silver")
        parts.lathe("lga_forward", [(0, 0), (La["d"] / 2, 0), (La["d"] / 2, La["length"] * 0.7),
                                    (La["d"] * 0.3, La["length"] * 0.95), (0, La["length"])],
                    segments=24, material="lga_white", location=(c * L["r"], s_ * L["r"], z + 0.04), direction=(0, 0, 1))
        G = f["grapple_fixtures"]
        for k, sg in enumerate((1, -1)):
            x, y = sg * G["v2_in"] * IN, sg * G["v3_in"] * IN
            ys = sg * -math.sqrt(max(r_fs ** 2 - x ** 2, 0)) + sg * 0.03     # skin below the fixture
            parts.box(f"grapple_post_{k + 1}", (0.12, abs(y - ys), 0.12), location=(x, (y + ys) / 2, sta(358)),
                      material="foil_silver")
            parts.box(f"grapple_base_{k + 1}", (G["base_in"] * IN, 0.03, G["base_in"] * IN), location=(x, y, sta(358)),
                      material="white_paint")
            parts.strut(f"grapple_pin_{k + 1}", (x, y, sta(358)), (x, y - sg * G["pin_in"] * IN, sta(358)), radius=0.03,
                        material="white_paint")
        T = f["magnetic_torquers"]
        for k, a in enumerate(T["az_deg"]):
            c, s_ = _az(a)
            centre = Vector((c * T["r"], s_ * T["r"], T["z"]))
            tang = Vector((-s_, c, 0))
            if tang.y * (1 if s_ > 0 else -1) < 0:   # toward the nearer V3 side
                tang = -tang
            d = (tang * T["across_m"] - Vector((0, 0, 1)) * T["along_m"]).normalized()
            half = 0.5 * math.hypot(T["across_m"], T["along_m"])
            e0, e1 = centre - d * half, centre + d * half
            parts.strut(f"magnetic_torquer_{k + 1}", e0, e1, radius=T["d"] / 2, segments=12, material="foil_silver")
            for i, e in enumerate((centre - d * half * 0.8, centre + d * half * 0.8)):
                rr = math.hypot(e.x, e.y)
                foot = Vector((e.x / rr * (r_fs - 0.03), e.y / rr * (r_fs - 0.03), e.z))
                parts.strut(f"magnetic_torquer_{k + 1}_mount_{i + 1}", foot, e, radius=0.025, material="foil_silver")
        P = f["scuff_plates"]
        for zi, (z, R) in enumerate(((P["forward_z"], r_ls), (P["aft_z"], R_es))):
            for a in P["az_deg"]:
                c, s_ = _az(a)
                tag = f"{'fwd' if zi == 0 else 'aft'}_{'pv2' if a == 0 else 'mv2'}"
                out = R + P["standoff_m"]
                parts.disc(f"scuff_plate_{tag}", radius=P["plate_d"] / 2, thickness=0.02,
                           location=(c * out, s_ * out, z), direction=(c, s_, 0), material="beam_gold",
                           hole_material="beam_gold")
                for i in range(4):
                    t = math.radians(45 + 90 * i)
                    off = Vector((-s_, c, 0)) * math.cos(t) * 0.35 + Vector((0, 0, 1)) * math.sin(t) * 0.35
                    foot = Vector((c * (R - 0.03), s_ * (R - 0.03), z)) + off
                    parts.strut(f"scuff_strut_{tag}_{i + 1}", foot, Vector((c * out, s_ * out, z)) + off * 0.3,
                                radius=0.025, material="beam_gold")

def build(spec):
    d = {k: v["value"] for k, v in spec["dimensions"].items()}
    f = {k: v["value"] for k, v in spec["facts"].items()}

    z_es0, z_es1 = sta(238.00), sta(299.25)      # equipment section
    z_fs1, z_ls1 = sta(455.30), sta(608.5)       # forward shell / light shield tops
    r_aft = d["aft_shroud_diameter"] / 2
    r_fs = d["forward_shell_diameter"] / 2
    r_ls = d["light_shield_diameter"] / 2 + 0.02  # outside of the 120 in bore: skin + blanket (estimated)

    # Blanket foil on the light shield and forward shell (the MLI-covered sections). The bulges
    # are geometry (parts.quilt, different everywhere); the fine creases are one sharp tiling
    # texture, 5 repeats round. Look tuned by eye against sm4_photos (no document gives sizes).
    sm = spec["materials"]
    fb, fn = tiling.crinkled_foil("hubble", "mli_foil", sm["mli_foil"]["hex"], facet=0.07, tilt_deg=7,
                                  wrinkle=0.3, wrinkle_deg=8, spread=0.05, stretch=2.5,
                                  repeat=(2 * math.pi * r_fs / 5, 2 * math.pi * r_fs / 5), px_per_m=700)
    foil = materials.image("mli_foil_crinkled", fb, normal=fn, metallic=sm["mli_foil"]["metallic"],
                           roughness=sm["mli_foil"]["roughness"])

    def blanket(name, r, z0, z1, seed):
        rows = max(2, int(math.ceil((z1 - z0) / 0.07)))
        rt = r - 0.02                          # tie lines sit just inside the nominal skin
        prof = [(rt, z0 + (z1 - z0) * k / rows) for k in range(rows + 1)]
        obj = parts.lathe(name, prof, segments=int(round(2 * math.pi * r / 0.07)), material=foil)
        parts.quilt(obj, rt, cell=0.35, height=0.045, seed=seed)
        tiling.cyl_uv(obj, 2 * math.pi * r / 5, 2 * math.pi * r / 5, r)
        return obj

    with parts.assembly("body", core=True):
        # Aft shroud: silvered tape in riveted panels (grid estimated from s125e011763), and the
        # aft bulkhead's tape as its own part.
        gb, gn = tiling.panel_grid("hubble", "aft_tape", sm["aft_fosr"]["hex"], cell=(0.75, 0.5))
        tape = materials.image("aft_tape", gb, normal=gn, metallic=sm["aft_fosr"]["metallic"],
                               roughness=sm["aft_fosr"]["roughness"])
        shroud = parts.lathe("aft_shroud", [(r_aft, 0), (r_aft, z_es0)], segments=96, material=tape,
                             smooth=True)
        tiling.cyl_uv(shroud, 2 * math.pi * r_aft / 6, 2.0, r_aft)
        parts.cylinder("aft_bulkhead", radius=r_aft - 0.002, length=0.02, location=(0, 0, 0), segments=96,
                       material="bulkhead_tape")
        # Equipment section: 12 bays (10 equipment, 2 trunnion) behind flat doors. A door seam
        # lies on +V3: the two doors either side of it carry the louvred radiators
        # (sm4_photos s125e011763, taken from +V3).
        R_es = d["equipment_section_diameter"] / 2
        parts.prism("equipment_section", sides=12, radius=R_es, height=z_es1 - z_es0,
                    location=(0, 0, z_es0), roll_deg=15, material="dark_metal")
        equipment_doors(R_es, z_es0, z_es1)
        blanket("forward_shell", r_fs, z_es1, z_fs1, 11)
        # Light shield: blanket outside, a rim at the front, flat black inside.
        ls = blanket("light_shield", r_ls, z_fs1, z_ls1, 12)
        # NASA worm and ESA logos on the +V3 side (spec facts.logo): official artwork, placed and
        # sized from s125e011763 (masks made by refs/hubble/logo, see its README).
        L = f["logo"]
        logo_dir = os.path.join(HARNESS, "refs", "hubble", "logo")
        im = textures.marking("hubble_logo", [(os.path.join(logo_dir, "mask_nasa.png"), materials.colour(sm["logo_red"])),
                                              (os.path.join(logo_dir, "mask_esa.png"), materials.colour(sm["logo_dark"]))], OUT)
        logo_mat = materials.image("hubble_logo", im, metallic=0.0, roughness=0.7, cutout=True)
        a = math.radians(L["az_deg"])
        parts.decal("light_shield_logo", ls, center=(r_ls * math.cos(a), r_ls * math.sin(a), z_ls1 - L["below_front_edge_m"]),
                    direction=(-math.cos(a), -math.sin(a), 0), up=(0, 0, 1), width=L["width_m"],
                    height=L["height_m"], material=logo_mat, lift=0.004)
        parts.lathe("light_shield_rim", [(r_ls - 0.031, z_ls1 - 0.01), (r_ls, z_ls1 - 0.01), (r_ls, z_ls1),
                                         (r_ls - 0.031, z_ls1)], closed=True, segments=64,
                    material="foil_silver", smooth=False)
        parts.lathe("light_shield_bore", [(r_ls - 0.031, z_ls1), (r_ls - 0.031, z_fs1)],
                    segments=64, material="black")
        parts.disc("light_shield_floor", radius=r_ls - 0.031, thickness=0.01,
                   location=(0, 0, z_fs1), material="black", hole_material="black")

    # OTA equipment section: nine bays in a 150-degree ring round the aft end of the forward shell,
    # on +V3, STA 299.425 to 337.75 (lmsc1985). Outer radius 2.05 m estimated from s125e011763; the
    # middle bay, under the +V3 antenna's hinge, sits lower (1.72 m, estimated from the same photo).
    o = f["ota_equipment_section"]
    z_o0, z_o1 = sta(o["sta"][0]), sta(o["sta"][1])
    bay = o["sweep_deg"] / o["bays"]
    with parts.assembly("ota_equipment_section"):
        for name, r, centre, n in (("ota_es_left", o["outer_radius"], 90 - bay * 2.5, 4),
                                   ("ota_es_middle", o["middle_radius"], 90, 1),
                                   ("ota_es_right", o["outer_radius"], 90 + bay * 2.5, 4)):
            obj = parts.lathe(name, [(0, z_o0), (r, z_o0), (r, z_o1), (0, z_o1)], segments=n,
                              sweep_deg=bay * n, roll_deg=centre, material=foil, smooth=False)
            tiling.cyl_uv(obj, 2 * math.pi * r_fs / 5, 2 * math.pi * r_fs / 5, r)

    # Aperture door: hinged on the +V3 edge at the front, opening up and over toward +V3.
    t = f["aperture_door_thickness"]
    r_door = d["aperture_door_diameter"] / 2
    z_door = sta(610.81) - t
    with parts.assembly("aperture_door"):
        # Hinge fitting on the rim (size estimated from s125e011763); the door turns about its edge.
        parts.box("aperture_door_hinge_fitting", (0.4, r_door + 0.06 - (r_ls - 0.03), 0.06),
                  location=(0, (r_door + 0.06 + r_ls - 0.03) / 2, z_door - 0.03), material="foil_silver")
        hinge = parts.joint("aperture_door_hinge", (0, r_door, z_door + t / 2), axis=(-1, 0, 0))
        # A "D": round on the far (-V3) side, square on the hinge side, full width along the
        # hinge (s125e012031; drawing 4171929 sh.2 shows the open door's straight hinge edge).
        # Tape strips across the hinge, faint seams (16 across, counted on s125e012031).
        D = f["aperture_door_shape"]
        outline = [(0.5 + 0.5 * math.cos(math.radians(a)), 0.5 + 0.5 * math.sin(math.radians(a)))
                   for a in range(0, -181, -6)] + [(0.0, 1.0), (1.0, 1.0)]
        db, dn = tiling.panel_grid("hubble", "door_tape", sm["door_fosr"]["hex"], cell=(2 * r_door / D["strips"], 2 * r_door),
                                   seam=0.006, darken=0.85, rivet=0.0, spread=0.02, cells=(D["strips"], 1))
        door_mat = materials.image("door_tape", db, normal=dn, metallic=sm["door_fosr"]["metallic"],
                                   roughness=sm["door_fosr"]["roughness"])
        parts.outline_plate("aperture_door", outline, 2 * r_door, 2 * r_door, t, location=(0, 0, z_door),
                            direction=(0, 0, 1), up=(0, 1, 0), material=door_mat, parent=hinge)
        zo = z_door + t
        bw, bh = D["hinge_beam"]
        parts.box("aperture_door_hinge_beam", (2 * r_door, bw, bh), location=(0, r_door - bw / 2, zo + bh / 2),
                  material="door_fosr", parent=hinge)
        lw, ld, lh = D["latch"]
        parts.box("aperture_door_latch", (lw, ld, lh), location=(0, -r_door + ld / 2 - 0.02, zo + lh / 2),
                  material="door_fosr", parent=hinge)
        for k, (x, y) in enumerate(D["handholds"]):
            x, y = x * r_door, y * r_door
            pts = [(x, y - 0.1, zo), (x, y - 0.1, zo + 0.06), (x, y + 0.1, zo + 0.06), (x, y + 0.1, zo)]
            for i in range(3):
                parts.strut(f"aperture_door_handhold_{k + 1}_{i + 1}", pts[i], pts[i + 1], radius=0.012,
                            material="handrail_paint", parent=hinge)

    # High-gain antennas on +-V3: hinge at STA 333, 72.30 in off the axis; deployed straight
    # out along V3 with the dish vertex at the drawing's 232.30 in. A square boom (about 0.1 m,
    # estimated from s125e012031) carries the Two-Axis Gimbal (lmsc1985 3.1.7.4, +-110 deg)
    # with the dish on its back; the waveguide runs along the boom.
    h = f["hga_hinge"]
    dish_d = f["hga_dish_diameter"]
    y_dish = f["hga_dish_centre_radial"]
    bw, g = 0.1, 0.16          # boom width, gimbal block size (estimated, s125e012031)
    for sign, tag in ((1, "pv3"), (-1, "mv3")):
        with parts.assembly(f"hga_{tag}"):
            # Support from the forward shell out to the hinge line (size estimated).
            parts.box(f"hga_hinge_{tag}", (0.25, h["radial"] - r_fs + 0.1, 0.25),
                      location=(0, sign * (r_fs + h["radial"] + 0.1) / 2 - sign * 0.05, h["z"]),
                      material="foil_silver")
            parts.cylinder(f"hga_hinge_drive_{tag}", radius=0.09, length=0.34, segments=20,
                           location=(-0.17, sign * h["radial"], h["z"]), direction=(1, 0, 0),
                           material="foil_gold")
            y0, y1 = h["radial"] + 0.09, y_dish - 2 * g - 0.02
            parts.box(f"hga_boom_{tag}", (bw, y1 - y0, bw), location=(0, sign * (y0 + y1) / 2, h["z"]),
                      material="foil_silver")
            parts.strut(f"hga_waveguide_{tag}", (bw / 2 + 0.02, sign * y0, h["z"] + 0.02),
                        (bw / 2 + 0.02, sign * y1, h["z"] + 0.02), radius=0.012, material="foil_gold")
            parts.box(f"hga_boom_tip_{tag}", (bw * 1.4, 0.04, bw * 1.4), location=(0, sign * (y1 + 0.02), h["z"]),
                      material="foil_silver")
            # Gimbal: outer axis along V1, inner along V2; the dish rides on the inner one.
            ja = parts.joint(f"hga_gimbal_{tag}_a", (0, sign * (y1 + 0.04 + g / 2), h["z"]), axis=(0, 0, 1))
            parts.box(f"hga_gimbal_outer_{tag}", (g, g, g), location=(0, sign * (y1 + 0.04 + g / 2), h["z"]),
                      material="foil_gold", parent=ja)
            jb = parts.joint(f"hga_gimbal_{tag}_b", (0, sign * (y1 + 0.04 + 1.5 * g), h["z"]), axis=(1, 0, 0),
                             parent=ja)
            parts.cylinder(f"hga_gimbal_inner_{tag}", radius=g / 2, length=g * 1.3, segments=16,
                           location=(-g * 0.65, sign * (y1 + 0.03 + 1.5 * g), h["z"]), direction=(1, 0, 0),
                           material="foil_gold", parent=jb)
            parts.dish(f"hga_dish_{tag}", diameter=dish_d, depth=0.15,
                       location=(0, sign * y_dish, h["z"]), direction=(0, sign, 0),
                       material="white_paint", parent=jb)
            parts.cylinder(f"hga_feed_{tag}", radius=0.04, length=0.12, segments=12,
                           location=(0, sign * y_dish, h["z"]), direction=(0, sign, 0),
                           material="foil_silver", parent=jb)

    # Solar arrays (SA3) on +-V2: drive at STA 320; each wing 2.6 m along V2 by 7.1 m along V1,
    # four panels (split at the mast and once along V1), cells on the -V3 face in the pose shown
    # (s125e011763, from +V3, sees the white backs), a foil-wrapped frame with crossbars and two
    # diagonal braces on the back, the mast across the wing's middle. The 1.0 m gap from the body,
    # the frame's member sizes and the crossbar places are estimated from s125e011763/s125e012031.
    zp = f["solar_array_pivot_z"]
    gap = 1.0
    w, L = d["solar_wing_width"], d["solar_wing_length"]
    for sign, tag in ((1, "pv2"), (-1, "mv2")):
        with parts.assembly(f"solar_array_{tag}"):
            drive = parts.joint(f"solar_drive_{tag}", (sign * r_fs, 0, zp), axis=(sign, 0, 0))
            x0, x1 = r_fs + gap, r_fs + gap + w           # inner and outer edge, as distances
            xm = (x0 + x1) / 2
            X = lambda u: sign * u
            parts.box(f"solar_array_{tag}", (w, 0.02, L), location=(X(xm), 0, zp),
                      material="panel_back", parent=drive)
            g = 0.03                                       # gap between panels
            cells = []
            for us in ((x0, xm - g / 2), (xm + g / 2, x1)):
                for vs in ((-L / 2, -g / 2), (g / 2, L / 2)):
                    cells.append(((us[1] - us[0], 0.004, vs[1] - vs[0]),
                                  (X((us[0] + us[1]) / 2), -0.012, zp + (vs[0] + vs[1]) / 2)))
            parts.boxes(f"solar_cells_{tag}", cells, material="solar_cells", parent=drive)
            m, yb = 0.05, 0.035                            # frame member size, its place behind
            frame = [((w, m, m), (X(xm), yb, zp + s_ * (L / 2 - m / 2))) for s_ in (1, -1)]
            frame += [((m, m, L), (X(u), yb, zp)) for u in (x0 + m / 2, x1 - m / 2)]
            frame += [((w, m, m), (X(xm), yb, zp + s_ * 1.95)) for s_ in (1, -1)]
            parts.boxes(f"solar_frame_{tag}", frame, material="foil_silver", parent=drive)
            for s_ in (1, -1):
                parts.strut(f"solar_brace_{tag}_{'a' if s_ > 0 else 'b'}", (X(x0 + m), yb, zp + s_ * 0.1),
                            (X(x1 - m), yb, zp + s_ * 1.9), radius=0.02, material="foil_silver",
                            parent=drive)
            parts.strut(f"solar_mast_{tag}", (X(r_fs), 0.07, zp), (X(x1), 0.07, zp), radius=0.06,
                        material="foil_silver", parent=drive)
            parts.box(f"solar_mast_root_{tag}", (0.12, 0.2, 0.25), location=(X(r_fs + 0.06), 0.03, zp),
                      material="foil_silver", parent=drive)

    aft_features(f, r_aft)
    fittings(f, r_ls, r_fs, R_es, z_ls1)

    # Handrails (layout estimated, spec facts.handrail_layout): lengthwise rails on the forward
    # tube and the aft shroud, clear of the array and antenna lines.
    with parts.assembly("handrails"):
        fwd = [parts.skin_line(r_fs, a, z_es1 + 0.15, z_fs1 - 0.1, steps=6) for a in (30, 60, 120, 150, 240, 300)]
        fwd += [parts.skin_line(r_ls, a, z_fs1 + 0.1, z_ls1 - 0.15, steps=6) for a in (30, 60, 120, 150, 240, 300)]
        aft = [parts.skin_line(r_aft, a, 0.2, z_es0 - 0.2, steps=6) for a in (30, 90, 150, 210, 270, 330)]
        parts.handrail("handrails", fwd + aft, standoff=0.06, radius=0.016, material="handrail_paint")

    parts.pose({"aperture_door_hinge": f["aperture_door_open_deg"],
                **{k: v["angle"] for k, v in spec["joints"].items()}})
