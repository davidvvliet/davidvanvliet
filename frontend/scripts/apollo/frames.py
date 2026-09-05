# Frame checks on the Apollo Image Archive state vectors.
import csv, numpy as np, datetime as dt
from astropy.coordinates import SkyCoord, FK4NoETerms, ICRS, GeocentricMeanEcliptic, BarycentricMeanEcliptic
from astropy.time import Time
import astropy.units as u

def load(m):
    rows=[r for r in csv.DictReader(open(f'AS{m}_Metric_SV.csv')) if r['x1950_x'] and r['selenographic_x']]
    rows.sort(key=lambda r:r['utc_time'])
    out=[]
    for r in rows:
        t=dt.datetime.fromisoformat(r['utc_time']).replace(tzinfo=dt.timezone.utc)
        a=np.array([float(r[k]) for k in ('x1950_x','x1950_y','x1950_z')])
        b=np.array([float(r[k]) for k in ('selenographic_x','selenographic_y','selenographic_z')])
        av=np.array([float(r[k]) for k in ('x1950_xdot','x1950_ydot','x1950_zdot')])
        out.append((t,a,av,b,r))
    return out

def kabsch(P,Q):
    # rotation R with R@P_i ~ Q_i (columns)
    H=P@Q.T; U,S,Vt=np.linalg.svd(H); d=np.sign(np.linalg.det(Vt.T@U.T))
    return Vt.T@np.diag([1,1,d])@U.T

def b1950_to_icrs_matrix():
    M=np.zeros((3,3))
    for i in range(3):
        v=np.zeros(3); v[i]=1
        c=SkyCoord(x=v[0],y=v[1],z=v[2],representation_type='cartesian',frame=FK4NoETerms(equinox='B1950')).transform_to(ICRS())
        M[:,i]=c.cartesian.xyz.value
    return M

if __name__=='__main__':
    B=b1950_to_icrs_matrix(); print('B1950->ICRS\n',B)
    for m in ('15','16','17'):
        rows=load(m)
        # rotation seleno->x1950 from a 2-hour window at the start
        t0=rows[0][0]; w=[r for r in rows if (r[0]-t0).total_seconds()<7200]
        P=np.array([r[3] for r in w]).T; Q=np.array([r[1] for r in w]).T
        R=kabsch(P,Q); res=np.linalg.norm(R@P-Q,axis=0)
        print(m,'window rows',len(w),'fit residual km max',res.max())
        pole=B@R[:,2]  # selenographic z (Moon north pole) in ICRS
        c=SkyCoord(x=pole[0],y=pole[1],z=pole[2],representation_type='cartesian',frame=ICRS()).transform_to(GeocentricMeanEcliptic(equinox='J2000'))
        print('  Moon pole ecliptic lat',c.lat.deg,'lon',c.lon.deg)
        # nadir consistency: seleno lon/lat vs nadir_point column
        r=rows[0]; b=r[3]; lon=np.degrees(np.arctan2(b[1],b[0])); lat=np.degrees(np.arcsin(b[2]/np.linalg.norm(b)))
        print('  seleno lon/lat',lon,lat,'nadir col',r[4]['nadir_point'])
        # rotation drift over the mission: compare window at end
        t1=rows[-1][0]; w2=[r for r in rows if (t1-r[0]).total_seconds()<7200]
        P2=np.array([r[3] for r in w2]).T; Q2=np.array([r[1] for r in w2]).T; R2=kabsch(P2,Q2)
        ang=np.degrees(np.arccos((np.trace(R.T@R2)-1)/2)); print('  rotation change start->end deg',ang,'over days',(t1-t0).total_seconds()/86400)
