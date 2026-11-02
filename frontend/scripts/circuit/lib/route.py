# Routing a generated board with Freerouting (README: "Routing"). Runs in KiCad's Python:
#   <kicad-python> lib/route.py export <board.kicad_pcb> <board.dsn>       copper fills off, the router's input
#   <kicad-python> lib/route.py import <board.kicad_pcb> <board.ses> <net>  traces back in, widened to the board's
#                                                                         minimum, then a fill of <net> on both sides
import sys
import pcbnew

def plane_fanout(b):
    """Every surface pad on a plane's net gets a short trace and a via down to the plane (the router leaves planes
    alone, routing those nets along the outer layers, which a BGA can't do). The via goes at the first free spot
    around the pad: 8 directions, diagonals first (a BGA's vias sit between four balls), each at the nearest
    distance that clears the pad itself, then clear of every other net's pads, vias, traces and keep-outs. A pad
    inside a footprint's keep-out has its block's own escape trace: the via goes at that trace's far end."""
    import math
    planes = {z.GetNetname() for z in b.Zones() if b.GetLayerType(z.GetLayer()) == pcbnew.LT_POWER}
    if not planes: return 0
    ds = b.GetDesignSettings(); nc = ds.m_NetSettings.GetDefaultNetclass()
    vd, vh, clr = nc.GetViaDiameter(), nc.GetViaDrill(), nc.GetClearance()
    tw = ds.m_TrackMinWidth
    keepouts = [z for z in list(b.Zones()) + [z for f in b.GetFootprints() for z in f.Zones()]
                if z.GetIsRuleArea() and (z.GetDoNotAllowVias() or z.GetDoNotAllowTracks())]
    def shapes():
        for f in b.GetFootprints():
            for p in f.Pads(): yield p.GetNetname(), p.GetBoundingBox()
        for t in b.GetTracks(): yield t.GetNetname(), t.GetBoundingBox()
        for z in keepouts: yield None, z.GetBoundingBox()
    sources = []  # (point, net item, reach, layer, outward angle: from the part's centre to the pad)
    for f in b.GetFootprints():
        for pad in f.Pads():
            if pad.GetNetname() not in planes or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD: continue
            layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
            c = pad.GetPosition()
            if any(z.Outline().Contains(c) for z in keepouts):
                for t in b.GetTracks():
                    if t.GetClass() == "PCB_TRACK" and t.GetNetCode() == pad.GetNetCode():
                        for near, far in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
                            if pad.HitTest(near) and not any(z.Outline().Contains(far) for z in keepouts):
                                sources.append((far, pad.GetNet(), t.GetWidth(), t.GetLayer(), math.atan2(far.y - f.GetPosition().y, far.x - f.GetPosition().x)))
                continue
            bb = pad.GetBoundingBox()
            sources.append((c, pad.GetNet(), math.hypot(bb.GetWidth(), bb.GetHeight()) / 2, layer, math.atan2(c.y - f.GetPosition().y, c.x - f.GetPosition().x)))
    placed = 0
    for c, net, reach, layer, out in sources:
        done = False
        # directions nearest the outward one first: out of a QFN's row, or towards a BGA's edge between four balls
        for a in sorted((k * math.pi / 4 for k in range(8)), key=lambda a: -math.cos(a - out)):
            for step in range(0, 10):
                d = reach * 0.5 + vd / 2 + clr * 0.5 + step * vd / 4
                v = pcbnew.VECTOR2I(int(c.x + d * math.cos(a)), int(c.y + d * math.sin(a)))
                # the via's square and a few squares along the trace to it, each grown by the clearance
                boxes = [pcbnew.BOX2I(pcbnew.VECTOR2I(v.x - vd // 2 - clr, v.y - vd // 2 - clr), pcbnew.VECTOR2I(vd + 2 * clr, vd + 2 * clr))]
                for q in (0.35, 0.6, 0.8):
                    p = pcbnew.VECTOR2I(int(c.x + (v.x - c.x) * q), int(c.y + (v.y - c.y) * q))
                    boxes.append(pcbnew.BOX2I(pcbnew.VECTOR2I(p.x - tw // 2 - clr, p.y - tw // 2 - clr), pcbnew.VECTOR2I(tw + 2 * clr, tw + 2 * clr)))
                if not b.GetBoardEdgesBoundingBox().Contains(boxes[0]): continue
                if any(n != net.GetNetname() and any(x.Intersects(sb) for x in boxes) for n, sb in shapes()): continue
                t = pcbnew.PCB_TRACK(b); t.SetStart(c); t.SetEnd(v); t.SetWidth(tw); t.SetLayer(layer); t.SetNet(net); b.Add(t)
                via = pcbnew.PCB_VIA(b); via.SetPosition(v); via.SetWidth(vd); via.SetDrill(vh); via.SetNet(net); b.Add(via)
                placed += 1; done = True
                break
            if done: break
    return placed

def export(pcb, dsn):
    b = pcbnew.LoadBoard(pcb)
    fanned = plane_fanout(b)
    for z in [b.GetArea(i) for i in range(b.GetAreaCount())]:
        # a filled zone blocks the router; planes (power-type inner layers) stay: the router connects to them by vias
        if not z.GetIsRuleArea() and b.GetLayerType(z.GetLayer()) != pcbnew.LT_POWER: b.Remove(z)
    pcbnew.SaveBoard(pcb, b)
    print("EXPORT", pcbnew.ExportSpecctraDSN(b, dsn), "plane vias", fanned, flush=True)

def ground_fill(b, net_name):
    """A copper fill of `net_name` over the whole board, on both copper layers."""
    net = b.FindNet(net_name)
    if not net: return 0
    e = b.GetBoardEdgesBoundingBox()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer); z.SetNet(net)
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetMinThickness(pcbnew.FromMM(0.2))
        o = z.Outline(); o.NewOutline()
        for x, y in ((e.GetLeft(), e.GetTop()), (e.GetRight(), e.GetTop()), (e.GetRight(), e.GetBottom()), (e.GetLeft(), e.GetBottom())):
            o.Append(x, y)
        b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return 2

def import_(pcb, ses, net_name):
    b = pcbnew.LoadBoard(pcb)
    ok = pcbnew.ImportSpecctraSES(b, ses)
    # Freerouting narrows some traces at pads below the board's minimum (see README): widen them back.
    m = b.GetDesignSettings().m_TrackMinWidth; widened = 0
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < m:
            t.SetWidth(m); widened += 1
    zones = ground_fill(b, net_name) if net_name else 0
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())  # the planes too
    pcbnew.SaveBoard(pcb, b)
    print("IMPORT", ok, "tracks", len(b.GetTracks()), "widened", widened, "fills", zones, flush=True)

if __name__ == "__main__":
    {"export": lambda: export(*sys.argv[2:4]), "import": lambda: import_(*sys.argv[2:5])}[sys.argv[1]]()
