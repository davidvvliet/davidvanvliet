# Apollo 15/16/17 trajectory reconstruction.
#  - Lunar orbit: Apollo Image Archive metric-camera state vectors (Moon-centred, B1950 equatorial, km).
#  - TLI cutoff, LOI, TEI, entry interface: mission report Table 3-III (lat/lon/alt/speed/FPA/heading).
#  - Translunar and transearth legs: numerically integrated (Earth+Moon+Sun point masses, DE432s),
#    with the injection velocity adjusted (shooting) so the leg lands on the tabulated arrival point.
import sys, json, csv, datetime as dt, numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import (solar_system_ephemeris, get_body_barycentric, SkyCoord, ICRS,
    GeocentricMeanEcliptic, ITRS, GCRS, CartesianRepresentation, EarthLocation, FK4NoETerms)
from frames import load, kabsch, b1950_to_icrs_matrix
solar_system_ephemeris.set('de432s')

GM_E, GM_M, GM_S = 398600.4418, 4902.800, 1.32712440018e11   # km^3/s^2
NMI, FT, AU = 1.852, 0.0003048, 149597870.7
R_MOON_REF = 1738.09   # km, the archive's altitude reference (spacecraft_radius - altitude)

def utc(s): return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc)
def get(rz, hms):  # ground elapsed time "hhh:mm:ss.s" -> datetime
    h, m, s = hms.split(':'); return rz + dt.timedelta(seconds=int(h)*3600 + int(m)*60 + float(s))
def jd(t): return Time(t).jd
B1950 = b1950_to_icrs_matrix()

# ---- ephemeris (geocentric ICRS, km) on a spline grid ----
class Eph:
    def __init__(self, t0, t1):
        ts = np.arange((t0 - dt.timedelta(days=1)).timestamp(), (t1 + dt.timedelta(days=1)).timestamp(), 300.0)
        T = Time(ts, format='unix')
        e = get_body_barycentric('earth', T); m = get_body_barycentric('moon', T); s = get_body_barycentric('sun', T)
        self.t0 = ts[0]
        self.moon = CubicSpline(ts - ts[0], (m - e).xyz.to(u.km).value.T)
        self.sun = CubicSpline(ts - ts[0], (s - e).xyz.to(u.km).value.T)
    def m(self, t): return self.moon(t - self.t0)
    def s(self, t): return self.sun(t - self.t0)

def accel_earth(t, y, eph):
    r = y[:3]; rm = eph.m(t); rs = eph.s(t)
    dm = rm - r; ds = rs - r
    a = -GM_E * r / np.linalg.norm(r)**3 \
        + GM_M * (dm / np.linalg.norm(dm)**3 - rm / np.linalg.norm(rm)**3) \
        + GM_S * (ds / np.linalg.norm(ds)**3 - rs / np.linalg.norm(rs)**3)
    return np.concatenate([y[3:], a])

def accel_moon(t, y, eph):  # Moon-centred, Earth as third body
    r = y[:3]; re = -eph.m(t); d = re - r
    a = -GM_M * r / np.linalg.norm(r)**3 + GM_E * (d / np.linalg.norm(d)**3 - re / np.linalg.norm(re)**3)
    return np.concatenate([y[3:], a])

def propagate(f, y0, t0, t1, eph, step=None):
    ts = np.arange(t0, t1, step) if step else None
    if ts is not None: ts = np.append(ts, t1)
    sol = solve_ivp(f, (t0, t1), y0, args=(eph,), method='DOP853', rtol=1e-10, atol=1e-9, t_eval=ts, dense_output=ts is None)
    return sol

# ---- Earth: geodetic lat/lon/alt + speed/FPA/heading -> GCRS state (km, km/s) ----
def earth_state(t, lat, lon, alt_km, v_kms, fpa, hdg):
    T = Time(t)
    loc = EarthLocation.from_geodetic(lon*u.deg, lat*u.deg, alt_km*u.km)
    pos = loc.get_gcrs(T).cartesian.xyz.to(u.km).value
    la, lo = np.radians(lat), np.radians(lon)
    up = np.array([np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)])
    east = np.array([-np.sin(lo), np.cos(lo), 0.0]); north = np.cross(up, east)
    def rot(v):  # ITRS direction -> GCRS direction (no translation for a geocentric vector)
        c = ITRS(CartesianRepresentation(v[0], v[1], v[2], unit=u.km), obstime=T).transform_to(GCRS(obstime=T))
        return c.cartesian.xyz.to(u.km).value
    E, N, U = rot(east), rot(north), rot(up)
    g, h = np.radians(fpa), np.radians(hdg)
    vel = v_kms * (np.cos(g) * (np.sin(h)*E + np.cos(h)*N) + np.sin(g)*U)
    return pos, vel

# ---- Moon: selenographic -> Moon-centred ICRS using the archive's own frame pairs ----
class MoonFrame:
    def __init__(self, rows, heading_pole):
        self.heading_pole = heading_pole
        # fit selenographic->B1950 rotation on the first and last 3 hours, deduce spin rate about the pole
        def fit(sel):
            P = np.array([r[3] for r in sel]).T; Q = np.array([r[1] for r in sel]).T
            for _ in range(8):  # trim inconsistent rows until the fit is tight
                R = kabsch(P, Q); res = np.linalg.norm(R@P - Q, axis=0)
                if res.max() < 5.0: break
                keep = res < max(5.0, np.median(res)); P, Q = P[:, keep], Q[:, keep]
            return R, res.max(), P.shape[1]
        t0, t1 = rows[0][0], rows[-1][0]
        self.R0, res0, n0 = fit([r for r in rows if (r[0]-t0).total_seconds() < 10800])
        R1, res1, n1 = fit([r for r in rows if (t1-r[0]).total_seconds() < 10800])
        self.t0 = t0
        D = self.R0.T @ R1  # rotation in the body frame between the two fits: about z (the pole)
        ang = np.arctan2(D[1, 0], D[0, 0])
        self.w = ang / (t1 - t0).total_seconds()
        print(f'  moon frame: fit residuals {res0:.2f}/{res1:.2f} km on {n0}/{n1} rows, spin {np.degrees(self.w)*86400:.3f} deg/day')
    def R(self, t):  # selenographic -> ICRS at time t
        a = self.w * (t - self.t0).total_seconds()
        Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        return B1950 @ self.R0 @ Rz
    def state(self, t, lat, lon, alt_km, v_kms, fpa, hdg):
        la, lo = np.radians(lat), np.radians(lon)
        up = np.array([np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)])
        east = np.array([-np.sin(lo), np.cos(lo), 0.0]); north = np.cross(up, east)
        R = self.R(t)
        pos = R @ (up * (R_MOON_REF + alt_km))
        # "North" for the reports' lunar heading: Earth's equatorial pole for Apollo 15,
        # the Moon's pole for 16 and 17 (each verified against the archive rows to ~1 deg).
        pole = np.array([0, 0, 1.0]) if self.heading_pole == 'earth' else R @ np.array([0, 0, 1.0])
        u_ = pos / np.linalg.norm(pos); e_ = np.cross(pole, u_); e_ /= np.linalg.norm(e_); n_ = np.cross(u_, e_)
        g, h = np.radians(fpa), np.radians(hdg)
        vel = v_kms * (np.cos(g) * (np.sin(h)*e_ + np.cos(h)*n_) + np.sin(g)*u_)
        return pos, vel

# ---- shooting: adjust v0 so the state at t1 reaches target position ----
def shoot(f, r0, v0, t0, t1, target, eph, label):
    v = v0.copy()
    for it in range(25):
        def endpos(vv):
            return propagate(f, np.concatenate([r0, vv]), t0, t1, eph).y[:3, -1]
        miss = endpos(v) - target
        print(f'  {label} iter {it}: miss {np.linalg.norm(miss):.1f} km, dv {np.linalg.norm(v - v0)*1000:.2f} m/s')
        if np.linalg.norm(miss) < 1.0: break
        J = np.zeros((3, 3)); h = 1e-4
        for k in range(3):
            dv = np.zeros(3); dv[k] = h
            J[:, k] = (endpos(v + dv) - endpos(v - dv)) / (2*h)
        step = np.linalg.solve(J, miss)
        for _ in range(8):  # damped: only accept a step that reduces the miss
            trial = v - step
            if np.linalg.norm(endpos(trial) - target) < np.linalg.norm(miss): break
            step *= 0.5
        v = trial
    return v

def bridge(f, sA, tA, sB, tB, eph, step):
    """Propagate A forward and B backward, blend by time so both ends match. Returns [(t, r)]."""
    fw = propagate(f, sA, tA, tB, eph, step)
    bw = propagate(f, sB, tB, tA, eph, -step)
    ts = fw.t; rb = bw.sol(ts) if bw.sol is not None else None
    # bw evaluated at same times: re-run dense
    bw = solve_ivp(f, (tB, tA), sB, args=(eph,), method='DOP853', rtol=1e-10, atol=1e-9, dense_output=True)
    out = []
    for i, t in enumerate(ts):
        w = (t - tA) / (tB - tA)
        r = (1-w) * fw.y[:3, i] + w * bw.sol(t)[:3]
        out.append((t, r))
    return out

# ICRS/J2000 equatorial -> ecliptic J2000: rotation about x by the mean obliquity (IAU 1976 value, as Horizons uses).
_EPS = np.radians(84381.448 / 3600)
ECL = np.array([[1, 0, 0], [0, np.cos(_EPS), np.sin(_EPS)], [0, -np.sin(_EPS), np.cos(_EPS)]])

from lunar import moon_j2000_km
def onto_scene_moon(trail, eph, ta, tb, ramp=3600.0):
    """Earth-centred (t, r km) trail. Between ta and tb (with ramps) shift by the difference
    between the site's lunar-theory Moon and the DE Moon, so the lunar part sits on the Moon
    the scene draws while the legs stay exactly as integrated."""
    out = []
    for t, r in trail:
        w = min(1.0, max(0.0, (t - ta) / ramp), ) if t < ta + ramp else 1.0
        w = min(w, max(0.0, (tb - t) / ramp))
        if w > 0:
            jd = Time(t, format='unix').jd
            r = r + w * (ECL.T @ np.array(moon_j2000_km(jd)) - eph.m(t))
        out.append((t, r))
    return out

def build(spec):
    print('==', spec['name'])
    rz = utc(spec['range_zero'])
    tli = get(rz, spec['tli'][0]); loi = get(rz, spec['loi_ign'][0]); loic = get(rz, spec['loi_cut'][0])
    tei = get(rz, spec['tei_ign'][0]); teic = get(rz, spec['tei_cut'][0]); ent = get(rz, spec['entry'][0]); land = get(rz, spec['landing'][0])
    eph = Eph(tli, land)
    rows = load(spec['csv'])
    mf = MoonFrame(rows, spec['heading_pole'])
    ts = lambda t: t.timestamp()
    # ---- outbound ----
    a = spec['tli']; r0, v0 = earth_state(tli, a[1], a[2], a[3]*NMI, a[4]*FT, a[5], a[6])
    b = spec['loi_ign']; rl, vl = mf.state(loi, b[1], b[2], b[3]*NMI, b[4]*FT, b[5], b[6])
    target = eph.m(ts(loi)) + rl
    v = shoot(accel_earth, r0, v0, ts(tli), ts(loi), target, eph, 'outbound')
    out = propagate(accel_earth, np.concatenate([r0, v]), ts(tli), ts(loi), eph, 300.0)
    print(f'  arrival speed (Moon-relative) {np.linalg.norm(out.y[3:, -1] - eph.moon(ts(loi) - eph.t0, 1)):.3f} km/s vs table {b[4]*FT:.3f}; min Moon dist {min(np.linalg.norm(out.y[:3, i] - eph.m(out.t[i])) for i in range(len(out.t))) - 1737.4:.0f} km alt')
    # ---- lunar orbit ----
    c = spec['loi_cut']; rc, vc = mf.state(loic, c[1], c[2], c[3]*NMI, c[4]*FT, c[5], c[6])
    # archive rows: keep rows consistent with their neighbours (position vs velocity*dt)
    good = []
    for i, r in enumerate(rows):
        ok = True
        for j in (i-1, i+1):
            if 0 <= j < len(rows):
                d = (rows[j][0] - r[0]).total_seconds()
                if abs(d) < 600 and np.linalg.norm(rows[j][1] - (r[1] + r[2]*d)) > 3.0 + 0.002*abs(d)**1.5: ok = False
        if ok: good.append(r)
    print(f'  archive rows kept {len(good)}/{len(rows)}')
    orbit = [(ts(r[0]), B1950 @ r[1], B1950 @ r[2]) for r in good]
    # states for bridging: LOI cutoff -> first row, gaps, last row -> TEI ignition
    d = spec['tei_ign']; rt, vt = mf.state(tei, d[1], d[2], d[3]*NMI, d[4]*FT, d[5], d[6])
    e = spec['tei_cut']; rtc, vtc = mf.state(teic, e[1], e[2], e[3]*NMI, e[4]*FT, e[5], e[6])
    nodes = [(ts(loic), rc, vc)] + orbit + [(ts(tei), rt, vt)]
    moon_pts = []
    # LOI burn: straight from ignition to cutoff
    moon_pts.append((ts(loi), rl)); 
    for i in range(len(nodes) - 1):
        tA, rA, vA = nodes[i]; tB, rB, vB = nodes[i+1]
        moon_pts.append((tA, rA))
        if tB - tA > 300:
            moon_pts += bridge(accel_moon, np.concatenate([rA, vA]), tA, np.concatenate([rB, vB]), tB, eph, 120.0)[1:-1]
    moon_pts.append((ts(tei), rt)); moon_pts.append((ts(teic), rtc))
    # ---- return ----
    f = spec['entry']; re_, ve = earth_state(ent, f[1], f[2], f[3]*NMI, f[4]*FT, f[5], f[6])
    r0 = eph.m(ts(teic)) + rtc; v0 = vtc + eph.moon(ts(teic) - eph.t0, 1)
    v = shoot(accel_earth, r0, v0, ts(teic), ts(ent), re_, eph, 'return')
    ret = propagate(accel_earth, np.concatenate([r0, v]), ts(teic), ts(ent), eph, 300.0)
    print(f'  entry speed {np.linalg.norm(ret.y[3:, -1]):.3f} km/s vs table {f[4]*FT:.3f}')
    g = spec['landing']; rland, _ = earth_state(land, g[1], g[2], 0.0, 0.0, 0, 0)
    # ---- assemble one Earth-centred trail, AU, ecliptic ----
    trail = [(t, out.y[:3, i]) for i, t in enumerate(out.t)]
    trail += [(t, eph.m(t) + r) for t, r in moon_pts]
    trail += [(t, ret.y[:3, i]) for i, t in enumerate(ret.t)]
    trail.append((ts(land), rland))
    trail = [p for i, p in enumerate(trail) if i == 0 or p[0] > trail[i-1][0]]
    thin = [trail[0]]
    for p in trail[1:]:  # the archive samples every ~25 s; one a minute is plenty for a 2-hour orbit
        if p[0] - thin[-1][0] >= 60: thin.append(p)
    trail = onto_scene_moon(thin, eph, ts(loi), ts(teic))
    ev = lambda t, l: {'jd': round(Time(t).jd, 5), 'label': l}
    points = [[round(Time(t, format='unix').jd, 5)] + [round(x, 8) for x in (ECL @ r) / AU] for t, r in trail]
    data = {'id': spec['id'], 'name': spec['name'], 'units': 'AU', 'frame': 'geocentric ecliptic J2000', 'points': points,
            'source': 'Lunar orbit: Apollo Image Archive metric camera state vectors. Injection/entry points: NASA mission report Table 3-III. Translunar legs integrated to join them.',
            'launchJD': round(Time(rz).jd, 5),
            'events': [ev(tli, 'Translunar injection'), ev(loi, 'Lunar orbit insertion'), ev(get(rz, spec['lunar_landing']), 'Lunar landing'),
                       ev(get(rz, spec['ascent']), 'Lunar liftoff'), ev(tei, 'Transearth injection'), ev(ent, 'Entry interface'), ev(land, 'Splashdown')]}
    print(f'  points {len(points)}')
    json.dump(data, open(f"{spec['id']}.json", 'w'), separators=(',', ':'))

# lat N+, lon E+; altitude n.mi.; speed ft/s; FPA deg; heading deg E of N
SPECS = {
 'apollo15': dict(id='apollo15', name='Apollo 15', heading_pole='earth', csv='15', range_zero='1971-07-26 13:34:00',
    tli=('02:56:03.6', 24.97, -142.13, 173.0, 35582.8, 7.48, 73.19),
    loi_ign=('78:31:46.7', -27.79, -172.05, 86.7, 8188.6, -8.93, -54.45),
    loi_cut=('78:38:25.1', -21.03, 160.08, 74.1, 5407.5, 2.17, -50.45),
    tei_ign=('223:48:45.8', -14.34, -167.97, 67.6, 5305.9, 0.52, -128.90),
    tei_cut=('223:51:06.8', -18.30, -176.32, 71.8, 8272.4, 4.43, -129.08),
    entry=('294:58:54.7', 14.23, -175.02, 65.9, 36096.4, -6.51, 52.06),
    landing=('295:11:53.0', 26.13, -158.14), lunar_landing='104:42:29', ascent='171:37:23'),
 'apollo16': dict(id='apollo16', name='Apollo 16', heading_pole='moon', csv='16', range_zero='1972-04-16 17:54:00',
    tli=('02:39:28', -(11+59/60), 162+29/60, 171.0, 35565.7, 7.47, 59.5),
    loi_ign=('74:28:28', 8+9/60, -(166+38/60), 93.9, 8105.4, -9.51, -89.95),
    loi_cut=('74:34:43', 7+7/60, 169+19/60, 75.3, 5399.2, 2.22, -95.5),
    tei_ign=('200:21:33', 9+43/60, 175+16/60, 52.2, 5383.6, -0.15, -85.80),
    tei_cut=('200:24:15', 10+58/60, 164+21/60, 59.7, 8663.0, 5.12, -82.37),
    entry=('265:37:31', -(19+52/60), -(162+8/60), 65.8, 36196.1, -6.55, 21.08),
    landing=('265:51:05', -(0+42/60), -(156+13/60)), lunar_landing='104:29:35', ascent='175:31:48'),
 'apollo17': dict(id='apollo17', name='Apollo 17', heading_pole='moon', csv='17', range_zero='1972-12-07 05:33:00',
    tli=('03:18:28', 5.14, -53.86, 162.4, 35589.6, 6.947, 118.040),
    loi_ign=('86:14:23', -11.33, 177.38, 76.8, 8110.2, -9.90, 273.70),
    loi_cut=('86:20:56', -6.81, 151.84, 51.2, 5512.1, 0.43, 288.89),
    tei_ign=('234:02:09', -19.65, -170.02, 62.1, 5337.1, -0.18, 257.32),
    tei_cut=('234:04:33', -21.52, -179.69, 63.1, 8374.3, 2.46, 259.47),
    entry=('301:38:38', 0.71, -173.34, 65.8, 36090.3, -6.49, 156.53),
    landing=('301:51:59', -17.88, -166.11), lunar_landing='110:21:57', ascent='185:21:37'),
}
if __name__ == '__main__':
    for k in sys.argv[1:] or SPECS: build(SPECS[k])
