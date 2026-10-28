# Livery: painted markings (lettering, insignia, stripes) baked into the probe's skin texture,
# so they cost no geometry. A spec's `livery` lists the markings; each is laid out like a decal
# (a sheet on the skin, parts.decal: centre, the way it is looked at, its top, width x height
# along the skin) with grey masks traced from photos, coloured by spec materials. The build:
#   1. unwraps every untextured part into one atlas (lib/bake.py, the same layout every time),
#   2. bakes each material's base colour, and its roughness and metalness, into the atlas,
#   3. lays each marking's sheet on the skin for a moment and bakes its paint onto the
#      surface under it (Cycles, selected to active), then removes the sheets,
#   4. gives every part's materials the two atlas images (glTF baseColor + metallicRoughness).
# A spec with a `bake` (colours from a reference model) paints over those colours.
# Results are cached in out/<probe>/livery/ against everything they depend on.
import hashlib, json, os
import bpy
import numpy as np
from lib import bake, materials, parts, textures

PAINT_ID = "_livery_id"

def _key(spec, objs, harness, probe):
    h = hashlib.sha1()
    h.update(bake.fingerprint(objs).encode())
    h.update(bake.layout(objs).encode())
    h.update(json.dumps(spec["livery"], sort_keys=True).encode())
    h.update(json.dumps(spec.get("materials"), sort_keys=True).encode())
    for m in spec["livery"].get("markings", []):
        for path, _ in m["layers"] + m.get("right_layers", []):
            h.update(open(os.path.join(harness, path), "rb").read())
    jpg, _ = bake.paths(harness, probe)
    if spec.get("bake") and os.path.exists(jpg):
        h.update(open(jpg, "rb").read())
    for m in {m for o in bake.targets(objs) for m in o.data.materials if m}:
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
        if b is not None:
            h.update(f"{m.name}{b.inputs['Roughness'].default_value}{b.inputs['Metallic'].default_value}".encode())
    return h.hexdigest()[:16]

def _bsdf(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m and m.node_tree else None

def _show_orm(mats, on):
    """Materials emit (1, roughness, metallic), glTF's metallicRoughness layout, or go back."""
    for m in mats:
        b = _bsdf(m)
        out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) if b else None
        if out is None:
            continue
        nt = m.node_tree
        if on:
            em = nt.nodes.get("_orm") or nt.nodes.new("ShaderNodeEmission")
            em.name = "_orm"
            em.inputs["Color"].default_value = (1.0, b.inputs["Roughness"].default_value, b.inputs["Metallic"].default_value, 1.0)
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        else:
            nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])

def _show_position(mats, on):
    """Materials emit their world position (for the finish's streaks), or go back."""
    for m in mats:
        b = _bsdf(m)
        out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) if b else None
        if out is None:
            continue
        nt = m.node_tree
        if on:
            geo = nt.nodes.get("_pos_geo") or nt.nodes.new("ShaderNodeNewGeometry")
            geo.name = "_pos_geo"
            em = nt.nodes.get("_pos") or nt.nodes.new("ShaderNodeEmission")
            em.name = "_pos"
            nt.links.new(geo.outputs["Position"], em.inputs["Color"])
            nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        else:
            nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])

def _noise(pts, seed):
    """Smooth value noise in 0..1 at points already divided by the feature size."""
    rng = np.random.default_rng(seed)
    table = rng.random(4096)
    i = np.floor(pts).astype(np.int64)
    f = pts - i
    f = f * f * (3 - 2 * f)
    def val(di, dj, dk):
        h = (i[..., 0] + di) * 73856093 ^ (i[..., 1] + dj) * 19349663 ^ (i[..., 2] + dk) * 83492791
        return table[h % 4096]
    out = 0.0
    for di in (0, 1):
        for dj in (0, 1):
            for dk in (0, 1):
                w = ((f[..., 0] if di else 1 - f[..., 0]) * (f[..., 1] if dj else 1 - f[..., 1])
                     * (f[..., 2] if dk else 1 - f[..., 2]))
                out = out + w * val(di, dj, dk)
    return out

def _finish(spec, O, pos, pix_mat, me, a):
    """A material's `finish` in the livery: its roughness varies in streaks (long along
    `along`, narrow across it) by up to +-`roughness_spread`, centred on its own value."""
    for k, m in enumerate(me.materials):
        base = m.name[:-len("_livery")] if m.name.endswith("_livery") else m.name
        cfg = spec["livery"].get("finish", {}).get(base)
        if cfg is None:
            continue
        sel = pix_mat == k
        if not sel.any():
            continue
        d = np.array(cfg.get("along", [1, 0, 0]), float)
        d /= np.linalg.norm(d)
        p = pos[sel]
        along = p @ d
        across = p - along[:, None] * d
        L, w = cfg["streak_m"]
        q = np.concatenate([along[:, None] / L, across / w], 1)
        n = _noise(q, 1)
        n = (n - np.median(n)) / max(float(np.percentile(np.abs(n - np.median(n)), 95)), 1e-6)
        rough = O[sel, 1] + cfg["roughness_spread"] * np.clip(n, -1, 1) * (1 - a[sel])
        O[sel, 1] = np.clip(rough, 0.02, 1.0)

def _sheet_material(name, img, channel):
    """Emission of a marking image for the bake: its colour ("colour"), or (alpha, id, 0)
    ("alpha") where id marks which marking it is."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    if channel == "colour":
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    else:
        comb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(tex.outputs["Alpha"], comb.inputs["Red"])
        val = nt.nodes.new("ShaderNodeValue")
        val.name = PAINT_ID
        nt.links.new(val.outputs[0], comb.inputs["Green"])
        nt.links.new(comb.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

def sheets(spec, harness, probe):
    """Every marking's sheet as (marking, name, frame, layers, flip). Mirrored ones come twice:
    left as given, right with y negated. The right side reads forwards like the left; with
    `"mirror": "shape"` its image is mirrored instead (a dart still points forward), and
    `right_layers` gives the right side its own masks (a stripe mirrored, its lettering not)."""
    out = []
    for m in spec["livery"].get("markings", []):
        sides = (("left", 1), ("right", -1)) if m.get("mirror") else ((None, 1),)
        for side, s in sides:
            flip = lambda v: (v[0], s * v[1], v[2])
            layers = m.get("right_layers", m["layers"]) if side == "right" else m["layers"]
            out.append((m, f"{m['name']}_{side}" if side else m["name"],
                        dict(host=m["host"], center=flip(m["center"]), direction=flip(m["direction"]),
                             up=flip(m["up"]), width=m["width"], height=m["height"]),
                        layers, side == "right" and m.get("mirror") == "shape"))
    return out

def _bake_paint(spec, objs, harness, probe, size, tex_dir):
    targets = bake.targets(objs)
    ours = bake.world_copy(targets, "_livery_target")
    sc = bpy.context.scene
    engine, samples = sc.render.engine, getattr(sc.cycles, "samples", 1)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 1
    mats = {m for m in ours.data.materials if m}
    bake.albedo(mats, True)
    base = bpy.data.images.new("_livery_base", size, size, alpha=True)
    bake.bake_into(ours, base)
    bake.albedo(mats, False)
    _show_orm(mats, True)
    orm = bpy.data.images.new("_livery_orm", size, size, alpha=True)
    orm.colorspace_settings.name = "Non-Color"
    bake.bake_into(ours, orm)
    _show_orm(mats, False)
    B, O = bake.pixels(base).copy(), bake.pixels(orm).copy()
    pos = None
    if spec["livery"].get("finish"):
        _show_position(mats, True)
        pimg = bpy.data.images.new("_livery_pos", size, size, alpha=True, float_buffer=True)
        pimg.colorspace_settings.name = "Non-Color"
        bake.bake_into(ours, pimg)
        _show_position(mats, False)
        pos = bake.pixels(pimg)[..., :3].copy()
        bpy.data.images.remove(pimg)
    face = bake.face_ids(ours, size)
    inside = face >= 0

    # The markings' sheets, briefly: colour bake, then alpha + id bake.
    made, report = [], []
    marks = sheets(spec, harness, probe)
    paint = {}
    for i, (m, name, fr, lay, mirrored) in enumerate(marks):
        layers = [(os.path.join(harness, p), materials.colour(spec["materials"][mat])) for p, mat in lay]
        key = f"livery_{name}" if lay is not m["layers"] else f"livery_{m['name']}"
        img = bpy.data.images.get(key) or textures.marking(key, layers, tex_dir)
        mc = _sheet_material(f"_sheet_c_{name}", img, "colour")
        ma = _sheet_material(f"_sheet_a_{name}", img, "alpha")
        ma.node_tree.nodes[PAINT_ID].outputs[0].default_value = (i + 1) / 256
        host = bpy.data.objects[fr["host"]]
        o = parts.decal(f"_sheet_{name}", host, fr["center"], fr["direction"], fr["up"], fr["width"], fr["height"], [mc, ma],
                        clip=bool(m.get("clip")))
        if mirrored:
            for d in o.data.uv_layers[0].data:
                d.uv = (1 - d.uv[0], d.uv[1])
        made.append((o, mc, ma))
        first = spec["materials"][lay[0][1]]
        paint[i] = (float(first.get("roughness", 0.5)), float(first.get("metallic", 0.0)))
        px = np.empty(img.size[0] * img.size[1] * 4, np.float32)
        img.pixels.foreach_get(px)
        report.append({"name": name, "expected_m2": float(px.reshape(-1, 4)[:, 3].mean()) * fr["width"] * fr["height"]})
    for slot in (0, 1):
        for o, mc, ma in made:
            for p in o.data.polygons:
                p.material_index = slot
        img = bpy.data.images.new(f"_livery_paint{slot}", size, size, alpha=True, float_buffer=slot == 1)
        if slot == 1:  # alpha and marking id are data, not colour
            img.colorspace_settings.name = "Non-Color"
        img.generated_color = (0, 0, 0, 0)
        bake.bake_into(ours, img, [o for o, *_ in made], extrusion=0.01, max_ray=0.02, kind="EMIT")
        if slot == 0:
            C = bake.pixels(img).copy()
        else:
            A = bake.pixels(img).copy()
    hit = (A[..., 3] > 0.5) & inside
    a = np.where(hit, np.clip(A[..., 0], 0, 1), 0.0)
    ids = np.where(hit & (a > 0.02), np.rint(A[..., 1] * 256).astype(int) - 1, -1)
    B[..., :3] = B[..., :3] * (1 - a[..., None]) + C[..., :3] * a[..., None]
    for i, (rough, metal) in paint.items():
        sel = ids == i
        O[sel, 1] = O[sel, 1] * (1 - a[sel]) + rough * a[sel]
        O[sel, 2] = O[sel, 2] * (1 - a[sel]) + metal * a[sel]

    # Painted area per marking: each pixel counts the skin area it covers on its own face
    # (lib/bake.py packs hidden faces at a lower density than visible ones).
    me = ours.data
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[bake.UV].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    dens = np.zeros(len(me.polygons))
    for p in me.polygons:
        if p.area <= 0:
            continue
        u = uv[p.loop_start:p.loop_start + p.loop_total]
        a2 = abs(sum(u[k][0] * u[(k + 1) % len(u)][1] - u[(k + 1) % len(u)][0] * u[k][1] for k in range(len(u)))) / 2
        dens[p.index] = (a2 / p.area) ** 0.5 * size
    px_m2 = np.where(inside, 1.0 / np.maximum(dens[np.maximum(face, 0)], 1e-9) ** 2, 0.0)
    areas = np.array([p.area for p in me.polygons])
    o_ = np.argsort(dens)
    cum = np.cumsum(areas[o_])
    texel_m = 1.0 / dens[o_][np.searchsorted(cum, cum[-1] / 2)]  # area-weighted median, for the report
    for i, r in enumerate(report):
        sel = ids == i
        r["painted_m2"] = float((a * px_m2)[sel].sum())
        low = sel & (dens[np.maximum(face, 0)] < 0.5 / texel_m)
        r["blurred"] = round(float((a * px_m2)[low].sum()) / max(r["painted_m2"], 1e-9), 3)
        r["coverage"] = round(r["painted_m2"] / r["expected_m2"], 3) if r["expected_m2"] > 0 else 0.0
    # The map against each material's own roughness and metalness, on its unpainted skin.
    mi = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("material_index", mi)
    pix_mat = np.where(inside, mi[np.maximum(face, 0)], -1)
    if pos is not None:
        _finish(spec, O, pos, pix_mat, me, a)
    orm_off = []
    for k, m in enumerate(me.materials):
        bs = _bsdf(m)
        sel = (pix_mat == k) & (a < 0.02)
        if bs is None or not sel.any():
            continue
        for ch, sock in ((1, "Roughness"), (2, "Metallic")):
            got, want = float(np.median(O[sel, ch])), bs.inputs[sock].default_value
            if abs(got - want) > 0.02:
                orm_off.append(f"{m.name} {sock.lower()} {got:.3f} in the map, {want:.3f} set")
    for o, mc, ma in made:
        bpy.data.objects.remove(o)
        bpy.data.materials.remove(mc)
        bpy.data.materials.remove(ma)
    bpy.data.objects.remove(ours)
    # The bake's own nodes go again: the materials are the parts' own, and a leftover image
    # node would make every part look textured (left out of the atlas, and of the export).
    for m in mats:
        for n in [n for n in m.node_tree.nodes if n.name in ("_bake", "_albedo", "_orm", "_pos", "_pos_geo")]:
            m.node_tree.nodes.remove(n)
    for img in (base, orm):
        bpy.data.images.remove(img)
    sc.render.engine = engine
    return B, O, report, round(texel_m * 1000, 2), orm_off

def _save(name, arr, path, colour, quality=88):
    h, w, _ = arr.shape
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=False)
    if not colour:
        img.colorspace_settings.name = "Non-Color"
    a = arr.copy()
    a[..., 3] = 1.0
    img.pixels.foreach_set(a.astype(np.float32).ravel())
    if path.endswith(".jpg") and not colour:  # data (roughness, metal): saved as is
        img.file_format = "JPEG"
        img.save(filepath=path, quality=quality)
        return
    if path.endswith(".jpg"):  # colour: JPEG keeps the export small
        sc = bpy.context.scene
        keep = (sc.render.image_settings.file_format, sc.render.image_settings.color_mode, sc.render.image_settings.quality)
        bake.jpeg(sc, quality)
        img.save_render(path, scene=sc)
        s_ = sc.render.image_settings
        s_.file_format, s_.color_mode, s_.quality = keep
        return
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()

def apply(objs, base_path, orm_path):
    """Every target's materials take the atlas: base colour, and roughness (G) and metalness
    (B) through a Separate Color node, which the glTF exporter writes as metallicRoughness.
    Each material is copied once, shared by all targets that used it."""
    base = bpy.data.images.load(base_path, check_existing=True)
    base.reload()
    orm = bpy.data.images.load(orm_path, check_existing=True)
    orm.reload()
    orm.colorspace_settings.name = "Non-Color"
    done = {}
    for o in bake.targets(objs):
        for slot in o.material_slots:
            m = slot.material
            if m is None or _bsdf(m) is None:
                continue
            if m.name not in done:
                b = m.copy()
                b.name = m.name + "_livery"
                nt = b.node_tree
                bsdf = _bsdf(b)
                uvn = nt.nodes.new("ShaderNodeUVMap")
                uvn.uv_map = bake.UV
                tex = nt.nodes.new("ShaderNodeTexImage")
                tex.image = base
                nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
                nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                otex = nt.nodes.new("ShaderNodeTexImage")
                otex.image = orm
                nt.links.new(uvn.outputs["UV"], otex.inputs["Vector"])
                sep = nt.nodes.new("ShaderNodeSeparateColor")
                nt.links.new(otex.outputs["Color"], sep.inputs["Color"])
                nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
                nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
                done[m.name] = b
            slot.material = done[m.name]

def paint(spec, objs, harness, probe, unwrapped=False):
    """The build's livery step. Returns a check result."""
    cfg = spec["livery"]
    size = cfg.get("size", 2048)
    out = os.path.join(harness, "out", probe, "livery")
    os.makedirs(out, exist_ok=True)
    if not unwrapped:
        bake.unwrap(objs, fold=bake.HIDDEN_FOLD)  # a bent panel is not hidden by itself
    key = _key(spec, objs, harness, probe)
    base_p, orm_p, info_p = (os.path.join(out, f) for f in ("base.jpg", "orm.jpg", "livery.json"))
    try:
        info = json.load(open(info_p))
    except (OSError, ValueError):
        info = {}
    if info.get("key") != key or not (os.path.exists(base_p) and os.path.exists(orm_p)):
        B, O, report, texel_mm, orm_off = _bake_paint(spec, objs, harness, probe, size, os.path.join(out, "masks"))
        _save("livery_base", B, base_p, True, cfg.get("jpeg_quality", 88))
        # Roughness and metal only change between materials and markings: half size is plenty.
        k = max(1, size // cfg.get("orm_size", size // 2))
        h, w = O.shape[0] // k * k, O.shape[1] // k * k
        _save("livery_orm", O[:h, :w].reshape(h // k, k, w // k, k, 4).mean((1, 3)), orm_p, False, cfg.get("orm_quality", 75))
        info = {"key": key, "size": size, "texel_mm": texel_mm, "markings": report, "map_off": orm_off}
        json.dump(info, open(info_p, "w"), indent=1)
    apply(objs, base_p, orm_p)
    def fault(m):
        if not 0.9 <= m["coverage"] <= 1.15:
            return f"{m['name']} {m['coverage']:.0%} painted"
        if m.get("blurred", 0) > 0.05:  # on faces the atlas keeps at low resolution
            return f"{m['name']} {m['blurred']:.0%} on hidden faces (blurred)"
    marks = [f for f in map(fault, info["markings"]) if f]
    bad = marks + info.get("map_off", ["no map check (stale cache)"])
    n = len(info["markings"])
    return {"name": "livery", "ok": not bad, "measured": f"{n - len(marks)}/{n} on skin",
            "expected": "every marking painted, sharp", "unit": "",
            "detail": "; ".join(bad) or f"{n} markings, {info['texel_mm']} mm texels, textures "
                      f"{os.path.getsize(base_p) // 1024} + {os.path.getsize(orm_p) // 1024} KB (colour + roughness/metal)"}
