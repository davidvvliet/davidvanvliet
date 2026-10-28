# Textures made at build time from data in refs/ (so a model rebuilds from the repo).
import os
import bpy
import numpy as np

def _load_gray(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[..., :3].mean(2)  # rows bottom-up, like Blender's UV v

def _shrink(a, size):
    f = a.shape[0] // size
    return a[:f * size, :f * size].reshape(size, f, size, f).mean((1, 3)) if f > 1 else a

def _blur(a, r):
    if r <= 0:
        return a
    p = np.pad(a, r, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    k = 2 * r + 1
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)

def _save(name, rgb, out_dir, colorspace, alpha=None):
    """Save linear `rgb` (rows bottom-up) as a PNG; `alpha` (same rows) makes it RGBA."""
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    img.colorspace_settings.name = colorspace
    if colorspace == "sRGB":  # pixels of an sRGB image are stored encoded; `rgb` is linear
        rgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(np.clip(rgb, 0, None), 1 / 2.4) - 0.055)
    a = np.ones((h, w, 1), np.float32) if alpha is None else np.asarray(alpha, np.float32)[..., None]
    rgba = np.concatenate([rgb, a], 2)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    path = os.path.join(out_dir, f"{name}.png")
    img.filepath_raw = path
    img.file_format = "PNG"
    if alpha is not None:
        img.alpha_mode = "STRAIGHT"
    img.save()
    return img

def engraved(name, lines_path, out_dir, size=1024, base=(0.85, 0.65, 0.08), line_lift=0.25,
             depth=2.5, soften_px=1):
    """Base colour and normal map for a plate with engraved lines.
    `lines_path`: grey image, white = engraved, square over the plate's face (as the disc
    part's UVs expect). Lines are drawn `line_lift` lighter (cut metal catches more light);
    the normal map treats them as grooves `depth` times as steep as wide, softened by
    `soften_px`. Returns (base_image, normal_image), saved as PNGs in `out_dir`."""
    os.makedirs(out_dir, exist_ok=True)
    lines = np.clip(_shrink(_load_gray(lines_path), size), 0, 1)
    base_rgb = np.array(base, np.float32)
    lit = base_rgb + (1 - base_rgb) * line_lift
    colour = base_rgb[None, None] * (1 - lines[..., None]) + lit[None, None] * lines[..., None]
    h = -_blur(lines, soften_px)  # grooves sit below the surface
    dy, dx = np.gradient(h)       # rows run bottom-up, so dy is along +v (glTF normal maps: +y = +v)
    n = np.stack([-dx * depth, -dy * depth, np.ones_like(h)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (_save(f"{name}_base", colour.astype(np.float32), out_dir, "sRGB"),
            _save(f"{name}_normal", (n * 0.5 + 0.5).astype(np.float32), out_dir, "Non-Color"))

def marking(name, layers, out_dir, size=None):
    """Colour + cut-out image for a painted marking (lettering, an insignia), for a decal.
    `layers`: [(mask_path, linear_rgb), ...] painted in order, each mask a grey image traced
    from a photo (white = paint), all the same size and covering the decal's [0, 1]^2. The
    colours come from the spec's sourced `materials` (`materials.colour`), not the masks.
    Alpha is where any layer paints; unpainted pixels take the first colour so edges don't
    fringe. Returns the image, saved as an RGBA PNG in `out_dir`."""
    os.makedirs(out_dir, exist_ok=True)
    rgb, alpha = None, None
    for path, colour in layers:
        m = np.clip(_load_gray(path), 0, 1)
        if size:
            m = _shrink(m, size)
        c = np.array(colour, np.float32)[None, None]
        if rgb is None:
            rgb, alpha = np.repeat(np.repeat(c, m.shape[0], 0), m.shape[1], 1), np.zeros(m.shape, np.float32)
        elif m.shape != alpha.shape:
            raise ValueError(f"marking {name}: {path} is {m.shape[1]}x{m.shape[0]}, the first mask {alpha.shape[1]}x{alpha.shape[0]}")
        rgb = rgb * (1 - m[..., None]) + c * m[..., None]
        alpha = np.maximum(alpha, m)
    return _save(name, rgb.astype(np.float32), out_dir, "sRGB", alpha=alpha)
