# Apollo 11 from mission report MSC-00171 Table 7-II (Moon-referenced states) and 7-VII (entry).
# No tracking data exists: the translunar legs are shot between the tabulated points, the lunar
# orbit is propagated between the tabulated CSM states and blended at the joins.
import json, datetime as dt, numpy as np
from astropy.time import Time
from apollo import (Eph, accel_earth, accel_moon, propagate, shoot, bridge, earth_state, onto_scene_moon,
                    utc, get, NMI, FT, AU, ECL, R_MOON_REF)
from apollo13 import MoonModel

RZ = utc('1969-07-16 13:32:00')
TLI   = ('2:50:13.5', 9.98, -164.84, 180.6, 35546.0, 7.37, 60.07)          # Table 7-II (cutoff + 10 s; 7-III gives ignition 2:44:16.2, 347.3 s)
LOI_I = ('75:49:50.4', -1.57, -169.58, 86.7, 8250.0, -9.99, -62.80)
LOI_C = ('75:55:48.0', 0.16, 167.13, 60.1, 5479.0, -0.20, -66.89)
CIRC_I = ('80:11:36.8', -0.02, 170.09, 61.8, 5477.3, -0.49, -66.55)
CIRC_C = ('80:11:53.5', -0.02, 169.16, 61.6, 5338.3, 0.32, -66.77)
UNDOCK = ('100:12:00.0', 1.11, 116.21, 62.3, 5333.8, 0.16, -89.13)
SEP_I = ('100:39:52.9', 0.99, 31.86, 62.7, 5332.7, -0.13, -106.99)
SEP_C = ('100:40:01.3', 1.05, 31.41, 62.5, 5332.2, -0.16, -106.90)
JETT = ('130:09:31.2', 1.13, 41.35, 61.6, 5335.9, 0.15, -97.81)
TEI_I = ('135:23:42.3', -0.16, 164.02, 62.4, 5376.0, -0.03, -62.77)
TEI_C = ('135:26:13.7', 0.50, 154.02, 59.1, 8589.0, 5.13, -62.60)
ENTRY = ('195:03:05.7', -3.19, 171.96, 65.8, 36194.0, -6.48, 50.18)      # Table 7-VII
LANDING = ('195:18:35', 13.30, -169.15)                                    # onboard guidance, Table 7-VII

def build(heading_pole):
    print('== Apollo 11, lunar heading from', heading_pole, 'pole')
    tli, ent, land = get(RZ, TLI[0]), get(RZ, ENTRY[0]), get(RZ, LANDING[0])
    eph = Eph(tli, land); mm = MoonModel(); ts = lambda t: t.timestamp()
    ms = lambda e: (get(RZ, e[0]),) + mm.state(get(RZ, e[0]), e[1], e[2], e[3]*NMI, e[4]*FT, e[5], e[6], heading_pole)
    # heading convention check: propagate LOI cutoff to circularization ignition (4 h) and measure the miss
    t0, r0, v0 = ms(LOI_C); t1, r1, _ = ms(CIRC_I)
    s = propagate(accel_moon, np.concatenate([r0, v0]), ts(t0), ts(t1), eph)
    miss = np.linalg.norm(s.y[:3, -1] - r1); print(f'  LOI cutoff -> circularization: miss {miss:.0f} km')
    # ---- outbound ----
    a = TLI; re0, ve0 = earth_state(tli, a[1], a[2], a[3]*NMI, a[4]*FT, a[5], a[6])
    tl, rl, vl = ms(LOI_I)
    v = shoot(accel_earth, re0, ve0, ts(tli), ts(tl), eph.m(ts(tl)) + rl, eph, 'outbound')
    out = propagate(accel_earth, np.concatenate([re0, v]), ts(tli), ts(tl), eph, 300.0)
    print(f'  outbound dv {np.linalg.norm(v-ve0)*1000:.1f} m/s; arrival speed {np.linalg.norm(out.y[3:, -1] - eph.moon(ts(tl) - eph.t0, 1)):.3f} km/s vs table {LOI_I[4]*FT:.3f}')
    # ---- lunar orbit: burns straight, coasts propagated from both ends and blended ----
    nodes = [ms(LOI_C), ms(CIRC_I), ms(CIRC_C), ms(UNDOCK), ms(SEP_I), ms(SEP_C), ms(JETT), ms(TEI_I)]
    moon_pts = [(ts(tl), rl)]
    for i in range(len(nodes) - 1):
        tA, rA, vA = nodes[i]; tB, rB, vB = nodes[i+1]
        moon_pts.append((ts(tA), rA))
        if ts(tB) - ts(tA) > 300:
            moon_pts += bridge(accel_moon, np.concatenate([rA, vA]), ts(tA), np.concatenate([rB, vB]), ts(tB), eph, 120.0)[1:-1]
    tt, rt, vt = nodes[-1]; tc, rc, vc = ms(TEI_C)
    moon_pts += [(ts(tt), rt), (ts(tc), rc)]
    # ---- return ----
    f = ENTRY; rE, vE = earth_state(ent, f[1], f[2], f[3]*NMI, f[4]*FT, f[5], f[6])
    r0 = eph.m(ts(tc)) + rc; v0 = vc + eph.moon(ts(tc) - eph.t0, 1)
    v = shoot(accel_earth, r0, v0, ts(tc), ts(ent), rE, eph, 'return')
    ret = propagate(accel_earth, np.concatenate([r0, v]), ts(tc), ts(ent), eph, 300.0)
    print(f'  return dv {np.linalg.norm(v-v0)*1000:.1f} m/s; entry speed {np.linalg.norm(ret.y[3:, -1]):.3f} km/s vs table {f[4]*FT:.3f}')
    rland, _ = earth_state(land, LANDING[1], LANDING[2], 0.0, 0.0, 0, 0)
    # ---- one Earth-centred trail ----
    trail = [(t, out.y[:3, i]) for i, t in enumerate(out.t)]
    trail += [(t, eph.m(t) + r) for t, r in moon_pts]
    trail += [(t, ret.y[:3, i]) for i, t in enumerate(ret.t)]
    trail.append((ts(land), rland))
    trail.sort(key=lambda p: p[0]); trail = [p for i, p in enumerate(trail) if i == 0 or p[0] > trail[i-1][0]]
    thin = [trail[0]]
    for p in trail[1:]:
        if p[0] - thin[-1][0] >= 60: thin.append(p)
    trail = onto_scene_moon(thin, eph, ts(tl), ts(tc))
    points = [[round(Time(t, format='unix').jd, 5)] + [round(x, 8) for x in (ECL @ r) / AU] for t, r in trail]
    ev = lambda g, l: {'jd': round(Time(get(RZ, g)).jd, 5), 'label': l}
    data = {'id': 'apollo11', 'name': 'Apollo 11', 'units': 'AU', 'frame': 'geocentric ecliptic J2000', 'points': points,
            'source': 'NASA Apollo 11 Mission Report MSC-00171, Tables 7-II and 7-VII; legs integrated and shot between the tabulated states, lunar orbit propagated between them.',
            'launchJD': round(Time(RZ).jd, 5),
            'events': [ev(TLI[0], 'Translunar injection'), ev(LOI_I[0], 'Lunar orbit insertion'), ev('102:45:39.9', 'Lunar landing'),
                       ev('124:22:00.8', 'Lunar liftoff'), ev(TEI_I[0], 'Transearth injection'), ev(ENTRY[0], 'Entry interface'), ev(LANDING[0], 'Splashdown')]}
    print(f'  points {len(points)}')
    return miss, data

if __name__ == '__main__':
    results = {hp: build(hp) for hp in ('earth', 'moon')}
    hp = min(results, key=lambda k: results[k][0]); print('using heading pole', hp)
    json.dump(results[hp][1], open('apollo11.json', 'w'), separators=(',', ':'))
    for g in ('102:37:03', '102:45:40', '102:45:58', '102:46:31', '109:24:23'):
        print(g, round(Time(get(RZ, g)).jd, 5))
