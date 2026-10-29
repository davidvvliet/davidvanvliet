# The programs the circuit harness runs, and where they live (override any with its environment variable).
#   KiCad 10      kicad-cli (export, checks) and KiCad's own Python (scripting the board editor)
#   Freerouting   the automatic router (a Java program; needs Java 25 or newer)
#   Blender       packs the exported board for the web (lib/pack.py)
import json, os, shutil, subprocess, sys

HOME = os.path.expanduser("~")
HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.dirname(os.path.dirname(HARNESS))
KICAD_APP = os.environ.get("KICAD_APP", os.path.join(HOME, "Applications/KiCad/KiCad.app"))

def _blender():
    cfg = os.path.join(FRONTEND, "scripts", "blender", "blender.json")
    try: return json.load(open(cfg))["path"]
    except (OSError, ValueError, KeyError): return "/Applications/Blender.app/Contents/MacOS/Blender"

def _java():
    brew = shutil.which("brew")
    if brew:
        r = subprocess.run([brew, "--prefix", "openjdk"], capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(os.path.join(r.stdout.strip(), "bin", "java")):
            return os.path.join(r.stdout.strip(), "bin", "java")
    return "java"

TOOLS = {
    "kicad-cli": (os.environ.get("KICAD_CLI", os.path.join(KICAD_APP, "Contents/MacOS/kicad-cli")),
                  "KiCad 10: copy KiCad.app from the disk image at kicad.org into ~/Applications/KiCad/"),
    "kicad-python": (os.environ.get("KICAD_PYTHON", os.path.join(KICAD_APP, "Contents/Frameworks/Python.framework/Versions/Current/bin/python3")),
                     "comes with KiCad"),
    "freerouting": (os.environ.get("FREEROUTING", os.path.join(HOME, "Applications/freerouting/freerouting-2.5.0.jar")),
                    "github.com/freerouting/freerouting/releases (the .jar) into ~/Applications/freerouting/"),
    "java": (os.environ.get("JAVA", "") or _java(), "Java 25 or newer: brew install openjdk"),
    "blender": (os.environ.get("BLENDER", "") or _blender(), "Blender 5: blender.org"),
}

def tool(name):
    """The path of `name`, or exit saying how to install it."""
    path, how = TOOLS[name]
    if os.path.exists(path) or shutil.which(path):
        return path
    sys.exit(f"{name} not found at {path}: {how}")
