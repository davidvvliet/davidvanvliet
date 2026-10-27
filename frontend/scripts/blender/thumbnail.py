# Renders a published model's thumbnail for the /models grid:
#   blender --background --factory-startup --python thumbnail.py -- <in.glb> <out.webp>
# The card shows it until the live model has loaded, then swaps to the model spinning from the
# same view, so the camera and lights here copy the site's grid card (app/models/PublishedModels.tsx).
import math, sys
import bpy
from mathutils import Matrix, Vector

PX = 512
FOV = math.radians(35)       # the card camera's vertical field of view
FIT = 1.15                   # bounding-sphere margin, as the card camera
# The card camera's direction from the model's centre, in three.js axes (y up) -> Blender (x, -z, y).
VIEW = Vector((0.6, -0.66, 0.45)).normalized()
# The site's directional lights (three.js position -> Blender axes, intensity).
LIGHTS = (((5, -6, 7), 3.0), ((-6, 3, -1), 0.6))

src, out = sys.argv[sys.argv.index("--") + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.update()
lo, hi = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
for o in meshes:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
centre, radius = (lo + hi) / 2, (hi - lo).length / 2

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = scene.render.resolution_y = PX
scene.render.film_transparent = True
scene.render.image_settings.file_format = "WEBP"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.quality = 90
scene.view_settings.view_transform = "Standard"  # three.js shows plain sRGB, not Filmic/AgX
scene.eevee.taa_render_samples = 32
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.25, 0.25, 0.25, 1)  # ambient + studio fill
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0

for i, (pos, energy) in enumerate(LIGHTS):
    light = bpy.data.objects.new(f"Sun{i}", bpy.data.lights.new(f"Sun{i}", "SUN"))
    light.data.energy = energy
    light.rotation_euler = (-Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(light)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
cam.data.sensor_fit = "VERTICAL"
cam.data.angle = FOV
dist = radius * FIT / math.sin(FOV / 2)
look = -VIEW
right = look.cross(Vector((0, 0, 1))).normalized()
up = right.cross(look)
cam.matrix_world = Matrix.Translation(centre + VIEW * dist) @ Matrix((right, up, -look)).transposed().to_4x4()
cam.data.clip_start, cam.data.clip_end = dist / 100, dist * 10
scene.camera = cam
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("THUMB_OK", out)
