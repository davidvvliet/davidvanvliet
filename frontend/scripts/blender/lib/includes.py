# A probe that is a model of its own and also part of another (Huygens on Cassini), the way
# an engine is (lib/engines.py): the carrier lists it in its spec's "includes" and calls
# `place`, which runs the included probe's own build script and moves what it made into place.
# The listing is what marks the carrier behind when the included probe changes (published.py)
# and carries the included probe's credits (sources.py). The included probe's checks run on
# its own build, not the carrier's.
import importlib.util, json, os

from mathutils import Matrix

from lib import materials, parts

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def spec(carrier_spec, probe):
    """The included probe's spec, for a carrier whose spec lists it in "includes"."""
    if probe not in carrier_spec.get("includes", []):
        raise ValueError(f"{probe}: list it in the spec's \"includes\" before using it")
    with open(os.path.join(HERE, "specs", f"{probe}.json")) as f:
        return json.load(f)

def place(carrier_spec, probe, location=(0, 0, 0), direction=(0, 0, 1), roll_deg=0.0):
    """Build `probe` (probes/<probe>.py, its own spec) and move it so its origin is at
    `location` and its +z points along `direction`, rolled by `roll_deg` about it. Its
    finishes join the build's (the carrier's own win on a name clash). On the carrier it is one
    part, its assembly the probe's name (`viewer.explode: ["<probe>"]` takes it off, as the X-15
    gives up its engine); its own assemblies are for its own model. The included script sees
    spec["included_in"] (the carrier's title), to leave to the carrier what the carrier does
    for every part (a foil pass). Returns its objects."""
    ps = dict(spec(carrier_spec, probe), included_in=carrier_spec.get("title", ""))
    materials.extend(ps.get("materials", {}))
    path = os.path.join(HERE, "probes", f"{probe}.py")
    mod_spec = importlib.util.spec_from_file_location(f"included_{probe}", path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    before = set(parts.collection().all_objects)
    mod.build(ps)
    made = [o for o in parts.collection().all_objects if o not in before]
    m = parts.frame(location, direction, roll_deg)
    for o in made:
        if o.parent is None or o.parent not in made:
            o.matrix_world = m @ o.matrix_world
        o["assembly"] = probe
        for k in ("within", "core"):
            if k in o:
                del o[k]
    return made
