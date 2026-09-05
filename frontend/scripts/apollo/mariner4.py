# Mariner 4: JPL TR 32-740 Table 90 (injection state, epoch 1964-11-28 15:07:27 GMT, and the
# pre-midcourse encounter prediction), midcourse burn 1964-12-05 16:09:25 GMT (16.70 m/s),
# Table 92 (post-midcourse encounter). One heliocentric leg, the burn shot onto Table 92.
import json, datetime as dt, numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import solar_system_ephemeris, get_body_barycentric, SkyCoord, FK4NoETerms, ICRS, FK5
solar_system_ephemeris.set('de432s')
from apollo import ECL, AU, b1950_to_icrs_matrix, utc

GM = {'sun': 1.32712440018e11, 'earth': 398600.4418, 'moon': 4902.800, 'mars': 42828.375, 'venus': 324858.592, 'jupiter': 1.26686534e8}
EPOCH = utc('1964-11-28 15:07:27'); BURN = utc('1964-12-05 16:09:25'); END = utc('1965-08-15 00:00:00')
R0 = np.array([5668.2509, 2146.6407, -3240.4334]); V0 = np.array([-1.8839630, 10.978611, -1.2281457])  # Earth-centred, km, km/s. Zdot sign: the table prints +, but the
# report's own Earth-fixed spherical set (flight path +13.165 deg at lat -28.13, azimuth 90.44) gives -1.228; with + the craft misses Mars by millions of km.
ENC_PRE = (utc('1965-07-17 01:28:15'), 249853.0, -224582.0, -121906.0)   # closest approach time, altitude km, B.T, B.R (Table 90)
ENC_POST = (utc('1965-07-15 01:08:03'), 8613.0, 7068.8, 12123.4)          # Table 92
R_MARS = 3387.0  # implied by Table 92: |B| 14,034 km and v_inf 4.4028 km/s give r_p ~ 12,000 km = 8,613 + 3,387

# barycentric ICRS spline of every body (km)
class Eph:
    def __init__(self):
        ts = np.arange(EPOCH.timestamp() - 86400, END.timestamp() + 86400, 21600.0); T = Time(ts, format='unix')
        self.t0 = ts[0]; self.sp = {}
        for b in ('sun', 'earth', 'moon', 'mars', 'venus', 'jupiter'):
            self.sp[b] = CubicSpline(ts - ts[0], get_body_barycentric(b, T).xyz.to(u.km).value.T)
    def pos(self, b, t): return self.sp[b](t - self.t0)
eph = Eph()
def accel(t, y):
    r = y[:3]; a = np.zeros(3)
    for b, mu in GM.items():
        d = eph.pos(b, t) - r; a += mu * d / np.linalg.norm(d)**3
    return np.concatenate([y[3:], a])
def prop(y0, t0, t1, step=None):
    ts = None if step is None else np.append(np.arange(t0, t1, step), t1)
    return solve_ivp(accel, (t0, t1), y0, method='DOP853', rtol=1e-10, atol=1e-6, t_eval=ts, dense_output=step is None)

def to_icrs(frame):
    if frame == 'B1950': M = b1950_to_icrs_matrix()
    else:  # mean equator and equinox of date (FK5, epoch of the state)
        M = np.zeros((3, 3)); eq = Time(EPOCH)
        for i in range(3):
            v = np.eye(3)[i]
            c = SkyCoord(x=v[0], y=v[1], z=v[2], representation_type='cartesian', frame=FK5(equinox=eq)).transform_to(ICRS())
            M[:, i] = c.cartesian.xyz.value
    return M

def encounter(sol_dense, t_guess):
    """Closest approach to Mars: time, radius, and B-plane components (T in the ecliptic plane)."""
    f = lambda t: np.linalg.norm(sol_dense.sol(t)[:3] - eph.pos('mars', t))
    from scipy.optimize import minimize_scalar
    grid = np.arange(sol_dense.t[0], sol_dense.t[-1], 3600.0); k = int(np.argmin([f(t) for t in grid]))
    res = minimize_scalar(f, bounds=(grid[max(k-1, 0)], grid[min(k+1, len(grid)-1)]), method='bounded')
    tca = res.x; y = sol_dense.sol(tca); r = y[:3] - eph.pos('mars', tca); v = y[3:] - CubicSpline.__call__(eph.sp['mars'], tca - eph.t0, 1)
    # B-plane: S = incoming asymptote direction (approximate by v at CA rotated: use h and e), T = S x ecliptic-pole, R = S x T
    mu = GM['mars']; h = np.cross(r, v); e = np.cross(v, h)/mu - r/np.linalg.norm(r)
    a = 1/(2/np.linalg.norm(r) - v@v/mu); vinf = np.sqrt(-mu/a)
    S = np.cos(np.arccos(-1/np.linalg.norm(e)))*e/np.linalg.norm(e) + np.sin(np.arccos(-1/np.linalg.norm(e)))*np.cross(h, e)/np.linalg.norm(np.cross(h, e))
    S = -S  # incoming direction
    N = ECL.T @ np.array([0, 0, 1.0]); Tv = np.cross(S, N); Tv /= np.linalg.norm(Tv); Rv = -np.cross(S, Tv)  # R sign chosen to match the report's B.R
    B = np.cross(h, S)/vinf * 0 + (np.linalg.norm(h)/vinf) * np.cross(S, h/np.linalg.norm(h))  # B vector, |B| = h/vinf, perpendicular to S in the orbit plane
    return tca, np.linalg.norm(r), B@Tv, B@Rv, vinf


def bangle(bt, br): return np.degrees(np.arctan2(br, bt))
def shoot(r0, v0, t0, target, label):
    """Adjust v0 so the closest approach matches (time, altitude, B-plane angle)."""
    t_ca, alt, bt, br = target; want = np.array([t_ca.timestamp()/3600, alt + R_MARS, bangle(bt, br)])
    def meas(v):
        sol = prop(np.concatenate([r0, v]), t0, END.timestamp()); tca, rca, b1, b2, _ = encounter(sol, 0)
        return np.array([tca/3600, rca, bangle(b1, b2)])
    v = v0.copy()
    for it in range(15):
        m = meas(v); miss = m - want; miss[2] = (miss[2] + 180) % 360 - 180
        print(f'  {label} iter {it}: dt {miss[0]:.2f} h, dr {miss[1]:.0f} km, dangle {miss[2]:.2f} deg, dv {np.linalg.norm(v-v0)*1000:.2f} m/s')
        if abs(miss[0]) < 0.02 and abs(miss[1]) < 20 and abs(miss[2]) < 0.05: break
        J = np.zeros((3, 3)); h = 2e-5
        for k in range(3):
            d = np.zeros(3); d[k] = h; mp = meas(v + d); mm = meas(v - d); dm = mp - mm; dm[2] = (dm[2] + 180) % 360 - 180; J[:, k] = dm / (2*h)
        step = np.linalg.solve(J, miss)
        for _ in range(6):
            m2 = meas(v - step); e2 = m2 - want; e2[2] = (e2[2] + 180) % 360 - 180
            if np.linalg.norm(e2/np.array([1, 1000, 1])) < np.linalg.norm(miss/np.array([1, 1000, 1])): break
            step *= 0.5
        v = v - step
    return v

M = to_icrs('date'); t0 = EPOCH.timestamp()
r0 = M@R0 + eph.pos('earth', t0); v0 = M@V0 + CubicSpline.__call__(eph.sp['earth'], t0 - eph.t0, 1)
# 1. pre-midcourse coast, injection velocity trimmed onto the report's pre-midcourse prediction
v_inj = shoot(r0, v0, t0, ENC_PRE, 'injection')
pre = prop(np.concatenate([r0, v_inj]), t0, BURN.timestamp())
# 2. midcourse burn, shot onto the report's post-midcourse encounter
rb, vb = pre.y[:3, -1], pre.y[3:, -1]
v_post = shoot(rb, vb, BURN.timestamp(), ENC_POST, 'midcourse')
print(f'  midcourse dv {np.linalg.norm(v_post - vb)*1000:.2f} m/s (report 16.70)')
post = prop(np.concatenate([rb, v_post]), BURN.timestamp(), END.timestamp())
tca, rca, bt, br, vinf = encounter(post, 0)
print(f'  encounter: {dt.datetime.fromtimestamp(tca, dt.timezone.utc)} alt {rca-R_MARS:,.0f} km, |B| {np.hypot(bt, br):,.0f} km, vinf {vinf:.4f} (table 4.4028)')
# post-encounter heliocentric elements check (Table 91: a 201,224,000, e 0.1686, i 2.9786)
tE = END.timestamp(); y = post.sol(tE); rs = eph.pos('sun', tE); vs = CubicSpline.__call__(eph.sp['sun'], tE - eph.t0, 1)
r = ECL@(y[:3]-rs); v = ECL@(y[3:]-vs); hh = np.cross(r, v); e = np.cross(v, hh)/GM['sun'] - r/np.linalg.norm(r); a = 1/(2/np.linalg.norm(r) - v@v/GM['sun'])
print(f'  post-encounter: a {a:,.0f} e {np.linalg.norm(e):.4f} i {np.degrees(np.arccos(hh[2]/np.linalg.norm(hh))):.4f}  (table 201,224,000 0.1686 2.9786)')
# output: heliocentric ecliptic, AU, 6-hourly (denser through the flyby)
pts = []
for sol, ta, tb in ((pre, t0, BURN.timestamp()), (post, BURN.timestamp(), tE)):
    ts = np.append(np.arange(ta, tb, 21600.0), tb)
    for t in ts:
        if abs(t - tca) < 2*86400 and t != ts[-1]: continue
    ts = np.unique(np.concatenate([ts, np.arange(tca - 2*86400, tca + 2*86400, 1800.0)]))
    ts = ts[(ts >= ta) & (ts <= tb)]
    for t in ts:
        y = sol.sol(t); r = ECL@(y[:3] - eph.pos('sun', t)) / AU
        pts.append([round(Time(t, format='unix').jd, 4)] + [round(x, 7) for x in r])
pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i-1][0]]
json.dump({'id': 'mariner4', 'name': 'Mariner 4', 'center': 'Sun', 'units': 'AU', 'frame': 'heliocentric ecliptic J2000',
           'source': 'JPL TR 32-740 Tables 90-92: injection state, midcourse burn, encounter conditions; integrated and shot onto them.',
           'launchJD': round(Time(EPOCH).jd, 4), 'points': pts,
           'events': [{'jd': round(Time(BURN).jd, 4), 'label': 'Midcourse correction'}, {'jd': round(Time(tca, format='unix').jd, 4), 'label': 'Mars flyby'}]},
          open('mariner4.json', 'w'), separators=(',', ':'))
print('points', len(pts))
