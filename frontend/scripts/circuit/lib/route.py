# Routing a generated board with Freerouting (README: "Routing"). Runs in KiCad's Python:
#   <kicad-python> lib/route.py export <board.kicad_pcb> <board.dsn>       copper fills off, the router's input
#   <kicad-python> lib/route.py import <board.kicad_pcb> <board.ses> <net>  traces back in, widened to the board's
#                                                                         minimum, then a fill of <net> on both sides
import sys
import pcbnew

def export(pcb, dsn):
    b = pcbnew.LoadBoard(pcb)
    for z in [b.GetArea(i) for i in range(b.GetAreaCount())]:
        if not z.GetIsRuleArea(): b.Remove(z)  # a filled zone blocks the router
    pcbnew.SaveBoard(pcb, b)
    print("EXPORT", pcbnew.ExportSpecctraDSN(b, dsn), flush=True)

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
    pcbnew.SaveBoard(pcb, b)
    print("IMPORT", ok, "tracks", len(b.GetTracks()), "widened", widened, "fills", zones, flush=True)

if __name__ == "__main__":
    {"export": lambda: export(*sys.argv[2:4]), "import": lambda: import_(*sys.argv[2:5])}[sys.argv[1]]()
