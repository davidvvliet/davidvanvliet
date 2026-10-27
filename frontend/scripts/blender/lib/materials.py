# Shared spacecraft materials (Principled BSDF only, so they survive glTF export).
import bpy

# name: (base colour RGB linear, metallic, roughness)
PALETTE = {
    "foil_gold":   ((0.80, 0.52, 0.16), 1.0, 0.30),  # aluminised Kapton blanket
    "foil_silver": ((0.80, 0.80, 0.82), 1.0, 0.25),
    "white_paint": ((0.82, 0.82, 0.80), 0.0, 0.55),  # dish faces, thermal paint
    "dark_metal":  ((0.10, 0.10, 0.11), 0.8, 0.45),  # booms, RTGs, struts
    "black":       ((0.02, 0.02, 0.02), 0.0, 0.70),
    "solar_cell":  ((0.03, 0.05, 0.16), 0.6, 0.25),
}

def get(name):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    color, metallic, roughness = PALETTE[name]
    mat = bpy.data.materials.new(name)
    if hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)  # viewport solid-mode colour
    return mat
