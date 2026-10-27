# Spacecraft materials (Principled BSDF only, so they survive glTF export).
# The shared list below is the base; a spec's "materials" adds finishes or overrides these
# for that probe only (see the README's "Materials").
import bpy

# name: (base colour RGB linear, metallic, roughness). Voyager pass 1 values, set by eye.
PALETTE = {
    "foil_gold":   ((0.80, 0.52, 0.16), 1.0, 0.30),  # aluminised Kapton blanket
    "foil_silver": ((0.80, 0.80, 0.82), 1.0, 0.25),
    "white_paint": ((0.82, 0.82, 0.80), 0.0, 0.55),  # dish faces, thermal paint
    "dark_metal":  ((0.10, 0.10, 0.11), 0.8, 0.45),  # booms, RTGs, struts
    "black":       ((0.02, 0.02, 0.02), 0.0, 0.70),
    "solar_cell":  ((0.03, 0.05, 0.16), 0.6, 0.25),
}

_ACTIVE = dict(PALETTE)  # what get() uses this build: PALETTE plus the spec's materials

def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def colour(entry):
    """Linear RGB of a spec material: "hex" (sRGB, as sampled from a photo) or "color" (linear)."""
    if "hex" in entry:
        h = entry["hex"].lstrip("#")
        return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    return tuple(entry["color"])

def use(spec_materials):
    """Set this build's materials: the shared list with the spec's entries merged over it.
    Spec entry: {"hex": "#rrggbb" or "color": [r, g, b], "metallic": 0..1, "roughness": 0..1,
    "source": ...}; metallic and roughness default to the shared entry of the same name, else 0
    and 0.5. Returns problems with the entries ([] when fine)."""
    _ACTIVE.clear()
    _ACTIVE.update(PALETTE)
    problems = []
    for name, e in (spec_materials or {}).items():
        base = PALETTE.get(name, ((0.5, 0.5, 0.5), 0.0, 0.5))
        try:
            col = colour(e) if ("hex" in e or "color" in e) else base[0]
            if len(col) != 3:
                raise ValueError("colour needs three channels")
        except (ValueError, TypeError) as err:
            problems.append(f"{name}: bad colour ({err})")
            continue
        _ACTIVE[name] = (col, e.get("metallic", base[1]), e.get("roughness", base[2]))
    return problems

def definition(name):
    """(linear colour, metallic, roughness) of a material this build, or None."""
    return _ACTIVE.get(name)

def get(name):
    if name not in _ACTIVE:
        raise KeyError(f"no material {name!r}: add it to the spec's materials or lib/materials.py")
    color, metallic, roughness = _ACTIVE[name]
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        if hasattr(mat, "use_nodes"):
            mat.use_nodes = True
    # Set every time: in the live session a material made by another probe's build may exist.
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)  # viewport solid-mode colour
    return mat

def image(name, base, normal=None, metallic=1.0, roughness=0.35):
    """Principled material with an image base colour and optional normal map, in the node
    layout the glTF exporter turns into baseColorTexture / normalTexture."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = base
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if normal is not None:
        ntex = nt.nodes.new("ShaderNodeTexImage")
        ntex.image = normal
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat
