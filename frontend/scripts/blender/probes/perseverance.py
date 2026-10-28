# Perseverance (Mars 2020). Built from lib/parts in metres, in the NASA reference model's
# frame (specs/perseverance.json "note": z up, ground z = 0, forward -y, left +x).
# Documented sizes come from the spec's dimensions; layout comes from the spec's
# from_reference_model (measured on NASA's model, which agrees with the documents).
# Numbers marked "est." are estimated from the reference model's sheet or the photos.
import json, math, os
import bpy
from mathutils import Matrix, Vector
from lib import materials, parts

REFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "refs", "perseverance")

BODY = "white_paint"      # spec materials (sourced from photos)
BLACK = "anodized_black"
TI = "bare_titanium"
MAST_RADIUS = 0.065      # lower mast tube (from_reference_model.mast_raised.mast_tube)

def _frame_from(centre, x_axis, y_axis):
    """World matrix with local x, y along the given axes (z completes the right-hand set)."""
    x = Vector(x_axis).normalized()
    y = Vector(y_axis).normalized()
    z = x.cross(y).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(centre)
    return m

def oriented_box(name, size, centre, x_axis, y_axis, material, parent=None):
    """Box of `size` along (x_axis, y_axis, their cross product), centred on `centre`."""
    obj = parts.box(name, size, material=material)
    obj.matrix_world = _frame_from(centre, x_axis, y_axis)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

def shapes(items, prefix, material, parent=None):
    """Build a list of measured pieces (spec from_reference_model): {"box": size, "at": centre}
    or {"cyl": radius, "from": point, "to": point}, each named <prefix>_<part>."""
    for it in items:
        name = f"{prefix}_{it['part']}"
        if "box" in it:
            parts.box(name, tuple(it["box"]), location=tuple(it["at"]), material=material, parent=parent)
        else:
            a, b = Vector(it["from"]), Vector(it["to"])
            parts.cylinder(name, it["cyl"], (b - a).length, location=tuple(a), direction=tuple(b - a),
                           segments=24, material=material, parent=parent)

def build(spec):
    ref = spec["from_reference_model"]
    d = {k: v["value"] for k, v in spec["dimensions"].items()}

    # --- Body: warm electronics box, the raised rear that carries the RTG, deck boxes --------
    web = ref["web_box"]["value"]
    z0, z1 = web["z"]
    deck_z = ref["deck_z"]["value"]
    with parts.assembly("body", core=True):
        parts.box("body", (web["width"], web["length"], z1 - z0),
                  location=(0, -0.0245, (z0 + z1) / 2), material=BODY)  # y -0.878..0.829
        # Raised rear (from the model's body profile: |x| 0.605, y 0.83-1.0 up to z 1.47,
        # a shelf at z 1.38-1.44 back to y 1.18).
        parts.box("body_rear", (1.21, 0.17, 0.78), location=(0, 0.915, 1.08), material=BODY)
        parts.box("body_shelf", (1.15, 0.19, 0.06), location=(0, 1.085, 1.41), material=BODY)
        # Deck equipment (model objects 'box', 'Body_Parts.001', 'lab', 'RIMFAX').
        # deck_box: model 'box' (the RPFA box); top z 1.3035 from rays down on it (its bounding
        # box reaches 1.41 only through the SuperCam target's stalk).
        parts.box("deck_box", (0.412, 0.387, 1.3035 - deck_z), location=(-0.419, 0.4925, (deck_z + 1.3035) / 2), material=BODY)
        parts.box("deck_box_2", (0.225, 0.17, 0.149), location=(0.3015, -0.099, deck_z + 0.0745), material=BODY)
        parts.box("sample_system", (0.556, 0.49, 0.505), location=(-0.032, -0.809, 1.1435), material=BODY)
        parts.box("rimfax", (0.612, 0.382, 0.204), location=(0, 1.056, 0.779), material=BODY)
        # Equipment bays on the front corners (model 'Body' |x| 0.573-0.774, z 0.674-1.198;
        # left bay y -0.903..-0.308, right y -0.903..-0.58) and the arm's cable tray.
        parts.box("side_bay_left", (0.2, 0.595, 0.524), location=(0.673, -0.6055, 0.936), material=BODY)
        parts.box("side_bay_right", (0.2, 0.323, 0.524), location=(-0.673, -0.7415, 0.936), material=BODY)
        parts.box("arm_cable_tray", (0.21, 0.485, 0.24), location=(0.558, -0.7525, 1.16), material=BLACK)
        parts.box("cal_target_bracket", (0.239, 0.354, 0.226), location=(-0.376, -1.042, 0.813), material=BLACK)
        parts.box("hazcams_front", (0.42, 0.19, 0.162), location=(-0.077, -0.972, 0.751), material="black")
        for sign, side in parts.sides():
            parts.box(f"hazcam_rear_{side}", (0.09, 0.21, 0.13), location=(sign * 0.49, 1.095, 0.83),
                      material="black")

    # --- Mobility: rocker-bogie suspension, steering, six wheels ------------------------------
    wc = ref["wheel_centres"]["value"]
    axle_z = wc["axle_z"]
    wheel_d = d["wheel_diameter"]
    cleat = 0.008                       # est.: model's grouser tips r 0.263, tyre r ~0.255
    wheel_w = ref["wheel_width"]["value"]
    # Curved titanium flexure spokes (facts.wheel_build), path from the NASA model; the path is
    # for a left wheel and mirrors on the right (sign flips the angle about the axle).
    ws = ref["wheel_spokes"]["value"]
    hub = ref["wheel_hub"]["value"]   # lathed hub with the flange the spokes stand on, and its axle stub
    diff = ref["differential_bar"]["value"]
    with parts.assembly("differential"):
        parts.box("differential_bar", (diff["width"], 0.159, 0.046), location=tuple(diff["centre"]), material=BLACK)
        parts.cylinder("differential_pivot", 0.05, 0.06, location=(0, diff["centre"][1], deck_z), material=BLACK)

    for sign, side in parts.sides():
        x = lambda v: sign * v
        rp = (x(0.80), -0.214, 0.894)           # rocker pivot (suspension_pivots)
        bp = (x(0.87), 0.54, 0.664)             # bogie pivot
        with parts.assembly(f"rocker_{side}"):
            parts.cylinder(f"rocker_axle_{side}", 0.045, 0.31, location=(x(0.57), -0.214, 0.894),
                           direction=(sign, 0, 0), material=BLACK)
            rocker = parts.joint(f"rocker_{side}_j", rp, axis=(1, 0, 0))
            parts.cylinder(f"rocker_hub_{side}", 0.08, 0.14, location=(x(0.73), -0.214, 0.894),
                           direction=(sign, 0, 0), material=BLACK, parent=rocker)
            # Front arm to the front steering actuator; rear arm to the bogie pivot.
            parts.tube(f"rocker_{side}", [(x(1.035), -1.0, 0.73), (x(0.93), -0.66, 0.80), rp, bp],
                       0.04, bend_radius=0.1, material=BLACK, parent=rocker)
            # Link from the differential bar's end down to the rocker hub.
            parts.tube(f"differential_link_{side}", [(x(0.638), diff["centre"][1], diff["centre"][2]),
                       (x(0.638), -0.214, diff["centre"][2]), (x(0.638), -0.214, 0.92)],
                       0.018, bend_radius=0.03, material=BLACK)
        with parts.assembly(f"bogie_{side}"):
            parts.cylinder(f"bogie_axle_{side}", 0.06, 0.24, location=(x(0.75), 0.54, 0.664),
                           direction=(sign, 0, 0), material=BLACK)
            bogie = parts.joint(f"bogie_{side}_j", bp, axis=(1, 0, 0), parent=rocker)
            parts.tube(f"bogie_{side}", [(x(1.05), wc["middle_y"], axle_z), (x(0.98), 0.107, 0.343),
                       (x(0.92), 0.2, 0.47), bp, (x(0.987), 0.836, 0.698), (x(1.055), 1.12, 0.73)],
                       0.032, bend_radius=0.08, material=BLACK, parent=bogie)

        for pos, y in (("front", wc["front_y"]), ("middle", wc["middle_y"]), ("rear", wc["rear_y"])):
            wx = wc["middle_x"] if pos == "middle" else wc["front_rear_x"]
            carrier = rocker if pos == "front" else bogie
            with parts.assembly(f"wheel_{side}_{pos}"):
                if pos != "middle":
                    # Steering actuator above the wheel, leg down the inside to the hub.
                    steer = parts.joint(f"steer_{side}_{pos}", (x(wx), y, 0.74), axis=(0, 0, 1), parent=carrier)
                    parts.cylinder(f"steer_housing_{side}_{pos}", 0.08, 0.24, location=(x(wx), y, 0.62),
                                   material=BLACK, parent=steer)
                    parts.tube(f"leg_{side}_{pos}", [(x(wx), y, 0.63), (x(0.83), y, 0.60), (x(0.83), y, axle_z),
                               (x(0.97), y, axle_z)], 0.035, bend_radius=0.06, material=BLACK, parent=steer)
                    carrier = steer
                parts.wheel(f"wheel_{side}_{pos}", wheel_d - 2 * cleat, wheel_w, location=(x(wx), y, axle_z),
                            axle=(sign, 0, 0), rim=0.02, cleats=48, cleat_height=cleat, cleat_width=0.006,
                            spokes=ws["count"], hub_profile=[tuple(p) for p in hub["profile"]],
                            spoke_path=[(r, z, sign * (g + ws["phase_deg"]), wd, th) for r, z, g, wd, th in ws["path"]],
                            spoke_material=TI, material=BLACK, parent=carrier)
                ha = hub["axle"]
                parts.cylinder(f"hub_{side}_{pos}", ha["radius"], ha["axial"][1] - ha["axial"][0],
                               location=(x(wx + ha["axial"][0]), y, axle_z), direction=(sign, 0, 0), material=TI, parent=carrier)

    # --- Power: MMRTG between its heat-exchanger panels, tilted 30° up at the back -----------
    with parts.assembly("rtg"):
        axis = Vector((0, 0.866, 0.5))           # model panels' main axis
        normal = Vector((0, -0.5, 0.866))
        centre = Vector((0, 1.276, 1.209))       # model panels' centre
        parts.rtg("rtg", d["rtg_length"], 0.11, fins=8, fin_span=d["rtg_diameter"],  # core radius est.
                  location=tuple(centre - axis * d["rtg_length"] / 2), direction=tuple(axis), material="dark_metal")
        for sign, side in parts.sides():
            oriented_box(f"rtg_panel_{side}", (0.75, 0.52, 0.09), (sign * 0.336, 1.276, 1.209), axis, normal, BODY)

    # --- Telecom: high-gain antenna on its gimbal, UHF can, X-band low-gain -----------------
    hga = ref["hga"]["value"]
    with parts.assembly("hga"):
        shapes(ref["hga_gimbal_parts"]["value"], "hga", BLACK)   # measured gimbal pieces
        # Hex plate where the model's dish sits (unclaimed group: centre 0.391, 0.309, 1.401).
        parts.prism("hga", 6, d["hga_diameter"] / 2, 0.04, location=(0.391, 0.309, 1.37),
                    material=BODY)
    uhf = ref["uhf_antenna"]["value"]
    with parts.assembly("uhf"):
        r, h, c = uhf["diameter"] / 2, uhf["height"], uhf["centre"]
        zb = c[2] - h / 2
        parts.lathe("uhf_antenna", [(0, 0), (r, 0), (r, h * 0.85), (r * 0.6, h), (0, h)],
                    location=(c[0], c[1], zb), material="black")
    with parts.assembly("lga"):
        parts.lathe("lga", [(0, 0), (0.025, 0), (0.02, 0.08), (0.033, 0.13), (0.02, 0.175), (0, 0.175)],
                    location=(0.495, 0.939, 1.422), material=BODY)  # model antenna_lg bounds

    # --- Remote sensing mast, raised (model's own raised pose, mast_raised) -----------------
    m = ref["mast_raised"]["value"]
    with parts.assembly("mast"):
        parts.box("mast_base", (0.287, 0.227, 0.155), location=(-0.5635, -0.7205, 1.2115), material=BODY)
        deploy = parts.joint("mast_deploy", tuple(m["deploy_hinge"]["at"]), axis=tuple(m["deploy_hinge"]["axis"]))
        mx, my = -0.557, -0.713                  # mast axis (azimuth axis)
        parts.cylinder("mast", MAST_RADIUS, m["upper_mast"]["z"][0] - 1.17, location=(mx, my, 1.17), material=BODY, parent=deploy)
        az = parts.joint("mast_azimuth", (mx, my, m["upper_mast"]["z"][0]), axis=(0, 0, 1), parent=deploy)
        parts.cylinder("mast_upper", 0.06, m["elevation_pivot"]["at"][2] - m["upper_mast"]["z"][0],
                       location=(mx, my, m["upper_mast"]["z"][0]), material=BODY, parent=az)
        parts.cylinder("mast_ring", 0.13, 0.04, location=(mx, my, 1.78), material=BODY, parent=az)
        ez = m["elevation_pivot"]["at"][2]
        side = Vector(m["elevation_pivot"]["axis"]).normalized()
        look = Vector((side.y, -side.x, 0))      # (0.84, 0.54): the head's facing in the model
        el = parts.joint("mast_elevation", (mx, my, ez), axis=tuple(side), parent=az)
        e = Vector((mx, my, ez))
        # Head, as NASA's model lays it out (from_reference_model.mast_head_parts), in the head's
        # frame: l forward (look), s along the elevation axis, u up, from the elevation pivot.
        hp = ref["mast_head_parts"]["value"]
        def at(l, s_, u):
            return tuple(e + look * l + side * s_ + Vector((0, 0, u)))
        def span_box(name, b, s_range, material):
            (l0, l1), (s0, s1), (u0, u1) = b["l"], s_range, b["u"]
            oriented_box(name, (l1 - l0, s1 - s0, u1 - u0), at((l0 + l1) / 2, (s0 + s1) / 2, (u0 + u1) / 2),
                         look, side, material, parent=el)
        span_box("supercam", hp["supercam_box"], hp["supercam_box"]["s"], BODY)
        span_box("supercam_floor", hp["supercam_floor"], hp["supercam_floor"]["s"], BODY)
        w = hp["supercam_window"]
        parts.cylinder("supercam_window", w["diameter"] / 2, w["l"][1] - w["l"][0], location=at(w["l"][0], w["s"], w["u"]),
                       direction=tuple(look), material=BODY, parent=el)
        span_box("mast_head_block", hp["centre_block"], hp["centre_block"]["s"], BODY)
        dr = hp["elevation_drum"]
        parts.cylinder("mast_elevation_drive", dr["diameter"] / 2, dr["s"][1] - dr["s"][0],
                       location=at(0, dr["s"][0], dr["u_centre"]), direction=tuple(side), material=BLACK, parent=el)
        for sg, tag in ((1, "left"), (-1, "right")):
            def mirrored(b):
                a0, a1 = b["s_abs"]
                return (a0, a1) if sg > 0 else (-a1, -a0)
            nc = hp["navcam"]
            span_box(f"navcam_{tag}", nc, mirrored(nc), BODY)
            sm = sum(mirrored(nc)) / 2
            parts.cylinder(f"navcam_{tag}_lens", nc["lens_diameter"] / 2, 0.006,
                           location=at(nc["l"][1], sm, sum(nc["u"]) / 2), direction=tuple(look), material="black", parent=el)
            span_box(f"mastcam_z_{tag}", hp["mastcam_z_body"], mirrored(hp["mastcam_z_body"]), BODY)
            hd = hp["mastcam_z_hood"]
            span_box(f"mastcam_z_{tag}_hood", hd, mirrored(hd), BODY)
            sm = sum(mirrored(hd)) / 2
            oriented_box(f"mastcam_z_{tag}_window", (0.004, 0.05, 0.045), at(hd["l"][1] + 0.002, sm, sum(hd["u"]) / 2),
                         look, side, "black", parent=el)
        parts.cylinder("mast_neck", 0.05, 0.09, location=(mx, my, ez), material=BODY, parent=el)

    # --- Robotic arm, stowed across the front (arm_stowed) ----------------------------------
    a = ref["arm_stowed"]["value"]
    with parts.assembly("arm"):
        ae = ref["arm_end_parts"]["value"]      # measured pieces, keyed by the joint they move with
        shoulder = parts.joint("arm_shoulder", tuple(a["shoulder"]), axis=(0, 0, 1))
        shapes(ae["shoulder"], "arm", BLACK, parent=shoulder)
        j2 = parts.joint("arm_elevation", tuple(a["joint_2"]), axis=(0, 1, 0), parent=shoulder)
        shapes(ae["arm_elevation"], "arm", BLACK, parent=j2)
        parts.tube("arm_upper", [(0.30, -0.996, 0.92), (-0.50, -0.996, 0.96)], 0.055, material=BODY, parent=j2)
        elbow = parts.joint("arm_elbow", tuple(a["elbow"]), axis=(0, 1, 0), parent=j2)
        parts.cylinder("arm_elbow", 0.09, 0.30, location=(-0.52, -0.94, 1.0), direction=(0, -1, 0), material=BLACK, parent=elbow)
        parts.tube("arm_fore", [(-0.52, -1.18, 1.05), (0.25, -1.18, 1.06)], 0.055, material=BODY, parent=elbow)
        wrist = parts.joint("arm_wrist", tuple(a["wrist"]), axis=(0, 1, 0), parent=elbow)
        shapes(ae["arm_wrist"], "arm", BLACK, parent=wrist)
        turret = parts.joint("arm_turret", tuple(a["turret"]), axis=(1, 0, 0), parent=wrist)
        shapes(ae["arm_turret"], "arm", BLACK, parent=turret)
        parts.cylinder("turret_drill", 0.04, 0.20, location=(0.39, -1.226, 1.30), material=TI, parent=turret)

    # --- Markings (spec "markings"): image plates, each its own assembly so the viewer can
    # focus it; positions in the spec's placement notes ---
    def img(n):
        return bpy.data.images.load(os.path.join(REFS, n if "." in n else f"{n}.png"), check_existing=True)
    def outline(n):
        with open(os.path.join(REFS, f"{n}.json")) as f:
            return json.load(f)
    mk = spec["markings"]
    with parts.assembly("name_chips_placard"):
        p = mk["name_chips_placard"]["placement"]
        n = Vector(p["normal"]).normalized()
        parts.plate("name_chips_mount", p["size"][0], p["size"][1], 0.03, location=tuple(Vector(p["centre"]) - n * 0.03),
                    direction=tuple(n), up=(0, 1, 0), material=BODY)
        parts.plate("name_chips_placard", p["size"][0], p["size"][1], 0.002, location=tuple(p["centre"]), direction=tuple(n),
                    up=(0, 1, 0), material=materials.image("name_chips_placard", img("name_chips_placard"), metallic=0.3, roughness=0.5))
    with parts.assembly("sherloc_cal_target"):
        p = mk["sherloc_cal_target"]["placement"]
        c = Vector(p["centre"])
        parts.box("sherloc_target_mount", (p["size"][0], 0.02, p["size"][1]), location=tuple(c + Vector((0, 0.01, 0))), material=BLACK)
        parts.plate("sherloc_cal_target", p["size"][0], p["size"][1], 0.002, location=tuple(c), direction=(0, -1, 0), up=(0, 0, 1),
                    material=materials.image("sherloc_cal_target", img("sherloc_target.jpg"), metallic=0.6, roughness=0.4))
    with parts.assembly("healthcare_plaque"):
        p = mk["healthcare_plaque"]["placement"]
        parts.plate("healthcare_plaque", p["size"][0], p["size"][1], 0.003, location=tuple(p["centre"]), direction=(1, 0, 0),
                    up=(0, 0, 1), material=materials.image("healthcare_plaque", img("healthcare_plaque"), metallic=0.3, roughness=0.5))
    with parts.assembly("mastcam_z_cal_target"):
        p = mk["mastcam_z_cal_target"]["placement"]
        o = outline("mastcam_z_target")
        c = Vector(p["centre"])
        parts.outline_plate("mastcam_z_cal_target", o["outline"], p["size"][0], p["size"][1], p["thickness"],
                            location=tuple(c), up=tuple(p["up"]), side_uv=tuple(o["side_uv"]),
                            material=materials.image("mastcam_z_cal_target", img("mastcam_z_target.jpg"), metallic=0.3, roughness=0.5))
        g = p["gnomon"]
        top = c + Vector((0, 0, p["thickness"]))
        parts.cylinder("mastcam_z_gnomon_base", g["base_radius"], g["base_height"], location=tuple(top), material=BLACK)
        parts.cylinder("mastcam_z_gnomon", g["shaft_radius"], g["height"] - g["knob_height"], location=tuple(top), material=BLACK)
        parts.cylinder("mastcam_z_gnomon_knob", g["knob_radius"], g["knob_height"],
                       location=tuple(top + Vector((0, 0, g["height"] - g["knob_height"]))), material=BLACK)
    with parts.assembly("jpl_logo_plate"):
        p = mk["jpl_logo_plate"]["placement"]
        o = outline("jpl_plate")
        parts.outline_plate("jpl_logo_plate", o["outline"], p["size"][0], p["size"][1], p["thickness"],
                            location=tuple(p["centre"]), direction=(0, -1, 0), up=(0, 0, 1), side_uv=tuple(o["side_uv"]),
                            material=materials.image("jpl_logo_plate", img("jpl_plate.jpg"), metallic=0.5, roughness=0.45))
    with parts.assembly("flag_plate"):
        p = mk["flag_plate"]["placement"]
        a = math.radians(p["facing_azimuth_deg"])
        f = (math.cos(a), math.sin(a), 0)
        parts.plate("flag_plate", p["size"][0], p["size"][1], 0.002,
                    location=tuple(Vector(p["axis_point"]) + Vector(f) * MAST_RADIUS), direction=f, up=(0, 0, 1),
                    material=materials.image("flag_plate", img("flag_plate"), metallic=0.5, roughness=0.45), parent=deploy)

    parts.pose({name: j["angle"] for name, j in spec.get("joints", {}).items()})
