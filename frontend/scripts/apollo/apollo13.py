# Apollo 13: no orbit data exists, so the whole path is integrated burn to burn between the
# tabulated states of mission report MSC-02680 (Table 4-II), each leg shot onto the next point.
import json, datetime as dt, numpy as np
from astropy.time import Time
from frames import load, kabsch, b1950_to_icrs_matrix
from apollo import (onto_scene_moon, Eph, accel_earth, propagate, shoot, earth_state, utc, get, R_MOON_REF, NMI, FT, AU, ECL)

class MoonModel:
    """Moon orientation (selenographic -> ICRS) fitted to the Apollo 15/16/17 archive vectors:
    pole drifting linearly, prime meridian W = W0 + w t. Residuals ~0.1 deg, so a few km at the surface."""
    def __init__(self):
        B = b1950_to_icrs_matrix(); fits = []
        for m in ('15', '16', '17'):
            rows = load(m)
            for sel in (rows[:len(rows)//2], rows[len(rows)//2:]):
                t0 = sel[0][0]; w = [r for r in sel if (r[0]-t0).total_seconds() < 10800]
                P = np.array([r[3] for r in w]).T; Q = np.array([r[1] for r in w]).T
                for _ in range(8):
                    R = kabsch(P, Q); res = np.linalg.norm(R@P - Q, axis=0)
                    if res.max() < 5: break
                    keep = res < max(5, np.median(res)); P, Q = P[:, keep], Q[:, keep]
                tm = t0 + dt.timedelta(seconds=np.mean([(r[0]-t0).total_seconds() for r in w]))
                fits.append((tm.timestamp(), B@R))
        self.t0 = fits[0][0]
        T = np.array([(f[0]-self.t0)/86400 for f in fits]); A = np.vstack([np.ones_like(T), T]).T
        poles = np.array([f[1][:, 2] for f in fits])
        self.pole0, self.pole1 = np.linalg.lstsq(A, poles, rcond=None)[0]
        pm = poles.mean(0); pm /= np.linalg.norm(pm)
        self.ref = np.cross(pm, [0, 0, 1.0]); self.ref /= np.linalg.norm(self.ref); self.ref2 = np.cross(pm, self.ref)
        Wd = np.array([np.degrees(np.arctan2(f[1][:, 0]@self.ref2, f[1][:, 0]@self.ref)) for f in fits])
        Wu = Wd + np.round((13.176*T - Wd)/360)*360
        self.W0, self.w = np.linalg.lstsq(A, Wu, rcond=None)[0]
        print(f'  moon model: rate {self.w:.4f} deg/day, W residuals {np.round(Wu-(self.W0+self.w*T), 3)}, pole drift {np.degrees(np.linalg.norm(self.pole1))*365:.2f} deg/yr')
    def R(self, t):
        d = (t.timestamp() - self.t0)/86400
        z = self.pole0 + self.pole1*d; z /= np.linalg.norm(z)
        W = np.radians(self.W0 + self.w*d); x = np.cos(W)*self.ref + np.sin(W)*self.ref2
        x -= (x@z)*z; x /= np.linalg.norm(x); y = np.cross(z, x)
        return np.array([x, y, z]).T
    def state(self, t, lat, lon, alt_km, v_kms, fpa, hdg, heading_pole):
        la, lo = np.radians(lat), np.radians(lon)
        up = np.array([np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)])
        R = self.R(t); pos = R @ (up * (R_MOON_REF + alt_km))
        pole = np.array([0, 0, 1.0]) if heading_pole == 'earth' else R @ np.array([0, 0, 1.0])
        u_ = pos/np.linalg.norm(pos); e_ = np.cross(pole, u_); e_ /= np.linalg.norm(e_); n_ = np.cross(u_, e_)
        g, h = np.radians(fpa), np.radians(hdg)
        return pos, v_kms*(np.cos(g)*(np.sin(h)*e_ + np.cos(h)*n_) + np.sin(g)*u_)

# (GET, body, lat N+, lon E+, altitude n.mi., speed ft/s, FPA, heading)  -- Table 4-II
RZ = '1970-04-11 19:13:00'
EVENTS = [
 ('Translunar injection',        [('2:41:47.2', 'E', -8.92, 167.21, 182.45, 35538.4, 7.635, 59.318)]),
 ('First midcourse correction',  [('30:40:49.6', 'E', 22.93, -101.85, 121381.93, 4682.5, 77.464, 112.843), ('30:40:53.1', 'E', 22.80, -101.86, 121385.43, 4685.6, 77.743, 112.751)]),
 ('Second midcourse correction', [('61:29:43.5', 'E', 20.85, 159.70, 188371.38, 3065.8, 79.364, 115.464), ('61:30:17.7', 'E', 20.74, 159.56, 188393.19, 3093.2, 79.934, 116.54)]),
 ('Transearth injection',        [('79:27:39.0', 'M', 3.73, 65.46, 5465.26, 4547.7, 72.645, -116.308), ('79:32:02.8', 'M', 3.62, 64.77, 5658.68, 5020.2, 64.784, -117.886)]),
 ('Third midcourse correction',  [('105:18:28.0', 'E', 19.63, -136.84, 152224.32, 4457.8, -79.673, 114.134), ('105:18:42.0', 'E', 19.50, -136.90, 152215.52, 4456.6, -79.765, 114.242)]),
 ('Fourth midcourse correction', [('137:39:51.5', 'E', 11.35, 113.39, 37808.58, 10109.1, -72.369, 118.663), ('137:40:13.0', 'E', 11.34, 113.32, 37776.05, 10114.6, -72.373, 118.660)]),
 ('Entry interface',             [('142:40:45.7', 'E', -28.23, 173.44, 65.83, 36210.6, -6.269, 77.210)]),
]
LANDING = ('142:54:41', -(21 + 38/60 + 24/3600), -(165 + 21/60 + 42/3600))

def build(heading_pole):
    rz = utc(RZ); ts = lambda t: t.timestamp()
    t_first = get(rz, EVENTS[0][1][0][0]); t_land = get(rz, LANDING[0])
    eph = Eph(t_first, t_land); mm = MoonModel()
    def state(e):
        g, body, lat, lon, alt, v, fpa, hdg = e; t = get(rz, g)
        if body == 'E': r, vel = earth_state(t, lat, lon, alt*NMI, v*FT, fpa, hdg)
        else:
            r, vel = mm.state(t, lat, lon, alt*NMI, v*FT, fpa, hdg, heading_pole)
            r = r + eph.m(ts(t)); vel = vel + eph.moon(ts(t) - eph.t0, 1)
        return t, r, vel
    path = []  # (t, r) Earth-centred
    total_dv = 0
    for i in range(len(EVENTS) - 1):
        name, burn = EVENTS[i]; nxt = EVENTS[i+1][1][0]
        # Short burns (seconds) are one point, the cutoff state: the table's rounded
        # latitudes put ignition and cutoff hundreds of km apart, which is not real.
        # The 4-minute transearth burn is drawn straight from ignition to cutoff.
        long_burn = len(burn) == 2 and (get(rz, burn[1][0]) - get(rz, burn[0][0])).total_seconds() > 60
        if long_burn:
            t_i, r_i, _ = state(burn[0]); path.append((ts(t_i), r_i))
        t0, r0, v0 = state(burn[-1]); t1, r1, _ = state(nxt if len(EVENTS[i+1][1]) == 1 or (get(rz, EVENTS[i+1][1][1][0]) - get(rz, nxt[0])).total_seconds() > 60 else EVENTS[i+1][1][1])
        v = shoot(accel_earth, r0, v0, ts(t0), ts(t1), r1, eph, name)
        total_dv += np.linalg.norm(v - v0)*1000
        sol = propagate(accel_earth, np.concatenate([r0, v]), ts(t0), ts(t1), eph, 300.0)
        path += [(sol.t[k], sol.y[:3, k]) for k in range(len(sol.t) - 1)]
        if EVENTS[i+1][0] == 'Transearth injection':
            dm = np.array([np.linalg.norm(sol.y[:3, k] - eph.m(sol.t[k])) for k in range(len(sol.t))]); k = dm.argmin()
            print(f'  pericynthion {dm[k]-R_MOON_REF:.0f} km = {(dm[k]-R_MOON_REF)/NMI:.1f} n.mi. at {dt.datetime.fromtimestamp(sol.t[k], dt.timezone.utc)} (GET {(sol.t[k]-ts(rz))/3600:.2f} h)')
    t_e, r_e, _ = state(EVENTS[-1][1][0]); path.append((ts(t_e), r_e))
    r_l, _ = earth_state(t_land, LANDING[1], LANDING[2], 0, 0, 0, 0); path.append((ts(t_land), r_l))
    print(f'  heading pole {heading_pole}: total shooting dv {total_dv:.1f} m/s')
    return path, total_dv, eph, rz

if __name__ == '__main__':
    results = {hp: build(hp) for hp in ('earth', 'moon')}
    hp = min(results, key=lambda k: results[k][1]); path, _, eph, rz = results[hp]
    print('using heading pole', hp)
    # closest approach: put the flyby on the scene's Moon within +-3 h of it
    dm = [np.linalg.norm(r - eph.m(t)) for t, r in path]; k = int(np.argmin(dm))
    trail = onto_scene_moon(path, eph, path[k][0] - 3*3600, path[k][0] + 3*3600)
    points = [[round(Time(t, format='unix').jd, 5)] + [round(x, 8) for x in (ECL @ r)/AU] for t, r in trail]
    ev = lambda g, l: {'jd': round(Time(get(rz, g)).jd, 5), 'label': l}
    data = {'id': 'apollo13', 'name': 'Apollo 13', 'units': 'AU', 'frame': 'geocentric ecliptic J2000', 'points': points,
            'source': 'NASA Apollo 13 Mission Report MSC-02680, Table 4-II; legs between burns integrated to join the tabulated states.',
            'launchJD': round(Time(utc(RZ)).jd, 5),
            'events': [ev(EVENTS[0][1][0][0], 'Translunar injection'), ev('55:54:53', 'Oxygen tank rupture'), ev('61:29:43.5', 'Free-return burn'),
                       ev('79:27:39.0', 'Transearth injection'), ev(EVENTS[-1][1][0][0], 'Entry interface'), ev(LANDING[0], 'Splashdown')]}
    print('points', len(points))
    json.dump(data, open('apollo13.json', 'w'), separators=(',', ':'))
