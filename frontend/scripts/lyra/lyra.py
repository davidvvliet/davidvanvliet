import numpy as np, json, sys
from scipy.optimize import minimize, brentq
MU = 2.9591220828559115e-04  # GM_sun, AU^3/day^2 (DE441 value)
AUD = 1731.456836805555      # km/s per AU/day
def load(f):
    rows=[]; on=False
    for l in open(f):
        if l.startswith('$$SOE'): on=True; continue
        if l.startswith('$$EOE'): break
        if on:
            p=l.split(','); rows.append([float(p[0])]+[float(x) for x in p[2:8]])
    return np.array(rows)
E,V,J,O = load('earth.csv'),load('venus.csv'),load('jupiter.csv'),load('oumuamua.csv')
def at(tab,jd):
    i=np.searchsorted(tab[:,0],jd); a,b=tab[i-1],tab[i]; f=(jd-a[0])/(b[0]-a[0])
    return a[1:4]+(b[1:4]-a[1:4])*f, a[4:7]+(b[4:7]-a[4:7])*f
from datetime import datetime
def jd(s): return (datetime.strptime(s,'%Y-%m-%d')-datetime(2000,1,1,12)).total_seconds()/86400+2451545.0
# Universal-variable Lambert (Bate, Mueller, White), prograde.
def stumpff(z):
    if z>1e-6: s=np.sqrt(z); return (s-np.sin(s))/s**3, (1-np.cos(s))/z
    if z<-1e-6: s=np.sqrt(-z); return (np.sinh(s)-s)/s**3, (np.cosh(s)-1)/-z
    return 1/6-z/120, 0.5-z/24
def lambert(r1,r2,dt,prograde=True):
    R1,R2=np.linalg.norm(r1),np.linalg.norm(r2)
    cz=np.cross(r1,r2)[2]; dth=np.arccos(np.clip(np.dot(r1,r2)/(R1*R2),-1,1))
    if (prograde and cz<0) or (not prograde and cz>=0): dth=2*np.pi-dth
    A=np.sin(dth)*np.sqrt(R1*R2/(1-np.cos(dth)))
    def y(z): S,C=stumpff(z); return R1+R2+A*(z*S-1)/np.sqrt(C)
    def F(z): S,C=stumpff(z); yy=y(z); return (yy/C)**1.5*S+A*np.sqrt(yy)-np.sqrt(MU)*dt
    # Bracket the root by scanning z (F is increasing in z where finite).
    zs=np.linspace(-4*np.pi**2,(2*np.pi)**2-0.05,4000); lo=hi=None; prev=None
    for zz in zs:
        try: fv=F(zz)
        except Exception: fv=np.nan
        if not np.isfinite(fv): continue
        if prev is not None and prev[1]<0<=fv: lo,hi=prev[0],zz; break
        prev=(zz,fv)
    if lo is None: raise ValueError('no Lambert root')
    z=brentq(F,lo,hi,xtol=1e-12,maxiter=500)
    S,C=stumpff(z); yy=y(z)
    f=1-yy/R1; g=A*np.sqrt(yy/MU); gd=1-yy/R2
    v1=(r2-f*r1)/g; v2=(gd*r2-r1)/g
    return v1,v2
def kepler_prop(r0,v0,dts):
    # universal variable propagation for an array of dt
    R0=np.linalg.norm(r0); vr0=np.dot(r0,v0)/R0; alpha=2/R0-np.dot(v0,v0)/MU
    out=[]
    for dt in dts:
        chi=np.sqrt(MU)*abs(alpha)*dt if abs(alpha)>1e-12 else np.sqrt(MU)*dt/R0
        for _ in range(60):
            z=alpha*chi**2; S,C=stumpff(z)
            f=R0*vr0/np.sqrt(MU)*chi**2*C+(1-alpha*R0)*chi**3*S+R0*chi-np.sqrt(MU)*dt
            fp=R0*vr0/np.sqrt(MU)*chi*(1-z*S)+(1-alpha*R0)*chi**2*C+R0
            d=f/fp; chi-=d
            if abs(d)<1e-10: break
        z=alpha*chi**2; S,C=stumpff(z)
        ff=1-chi**2/R0*C; gg=dt-chi**3/np.sqrt(MU)*S
        out.append(ff*r0+gg*v0)
    return np.array(out)
# Table 2 schedule (26-year mission)
sched=[('Earth',E,'2028-03-07'),('Venus',V,'2028-07-06'),('Earth',E,'2029-03-13'),('DSM',None,'2030-02-12'),('Earth',E,'2031-02-15'),('Jupiter',J,'2032-03-22'),('Oumuamua',O,'2054-03-01')]
T=[jd(s[2]) for s in sched]
P={i:at(s[1],T[i]) for i,s in enumerate(sched) if s[1] is not None}
# DSM position: 2.2 au, direction (lon,lat) fitted so that Earth-2029 departure v_inf = 6.279, DSM dv = 0.452, Earth-2031 arrival v_inf = 9.063 km/s
def legs(lon,lat):
    rd=2.2*np.array([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])
    v1,v2=lambert(P[2][0],rd,T[3]-T[2]); v3,v4=lambert(rd,P[4][0],T[4]-T[3])
    return rd,v1,v2,v3,v4
def cost(x):
    try: rd,v1,v2,v3,v4=legs(*x)
    except Exception: return 1e6
    vinf_dep=np.linalg.norm(v1-P[2][1])*AUD; dv=np.linalg.norm(v3-v2)*AUD; vinf_arr=np.linalg.norm(v4-P[4][1])*AUD
    return (vinf_dep-6.2791)**2+(dv-0.4518)**2+(vinf_arr-9.0627)**2
best=None
for lon0 in np.linspace(0,2*np.pi,24,endpoint=False):
    for lat0 in (-0.2,0,0.2):
        r=minimize(cost,[lon0,lat0],method='Nelder-Mead',options={'xatol':1e-8,'fatol':1e-10,'maxiter':4000})
        if best is None or r.fun<best.fun: best=r
rd,v1,v2,v3,v4=legs(*best.x)
print('DSM fit: lon %.1f lat %.1f deg, r=%.2f au, cost %.4g'%(np.degrees(best.x[0]),np.degrees(best.x[1]),np.linalg.norm(rd),best.fun))
# All legs
nodes=[(T[0],P[0][0])]
vel=[]
va,vb=lambert(P[0][0],P[1][0],T[1]-T[0]); vel.append((va,vb))
vc,vd=lambert(P[1][0],P[2][0],T[2]-T[1]); vel.append((vc,vd))
vel.append((v1,v2)); vel.append((v3,v4))
ve,vf=lambert(P[4][0],P[5][0],T[5]-T[4]); vel.append((ve,vf))
vg,vh=lambert(P[5][0],P[6][0],T[6]-T[5]); vel.append((vg,vh))
pos=[P[0][0],P[1][0],P[2][0],rd,P[4][0],P[5][0],P[6][0]]
print('%-10s %-12s %8s %8s %8s   table'%('body','date','arr','dep','dv'))
table=[(0,3.455,3.455),(5.6526,5.6511,0.007),(8.0443,6.2791,0.9708),(15.9254,15.4781,0.4518),(9.0627,13.2924,3.0),(18.5791,37.071,7.9588),(18.1348,18.1348,0)]
for i,s in enumerate(sched):
    vpl=P[i][1] if s[1] is not None else np.zeros(3)
    arr=np.linalg.norm(vel[i-1][1]-vpl)*AUD if i>0 else 0
    dep=np.linalg.norm(vel[i][0]-vpl)*AUD if i<6 else arr
    if s[0]=='DSM': dv=np.linalg.norm(vel[i][0]-vel[i-1][1])*AUD
    elif i==0: dv=dep
    elif i==6: dv=0
    else: dv=abs(dep-arr)  # powered flyby: table lists periapsis burn; compare vinf magnitudes
    print('%-10s %-12s %8.3f %8.3f %8.3f   %s'%(s[0],s[2],arr,dep,dv,table[i]))
# Sample the path by integrating two-body motion along each leg (2 d steps inside Jupiter, 30 d after).
from scipy.integrate import solve_ivp
def prop(r0,v0,ts):
    sol=solve_ivp(lambda t,y: np.concatenate([y[3:], -MU*y[:3]/np.linalg.norm(y[:3])**3]), (0,ts[-1]), np.concatenate([r0,v0]), t_eval=ts, method='DOP853', rtol=1e-11, atol=1e-13)
    return sol.y[:3].T
pts=[]
steps=[2,2,2,2,2,30]
for i in range(6):
    dts=np.arange(0,T[i+1]-T[i],steps[i]); dts=np.append(dts,T[i+1]-T[i])
    rr=prop(pos[i],vel[i][0],dts)
    print('leg %d closure error %.2e au'%(i,np.linalg.norm(rr[-1]-pos[i+1])))
    for dt,r in zip(dts[:-1],rr[:-1]): pts.append([round(T[i]+dt,3)]+[round(x,5) for x in r])
pts.append([round(T[6],3)]+[round(x,5) for x in pos[6]])
json.dump(pts,open('lyra_points_tdb.json','w'))
print(len(pts),'points; arrival r=%.1f au'%np.linalg.norm(pos[6]))
