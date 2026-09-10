# Scenario A of Hibberd, Hein & Eubanks 2020 (arXiv 1902.04935, Table 2): E-J-6SR-1I.
# Launch 2033 MAY 08 (C3 121 km2/s2), Jupiter 2034 JUL 30 (unpowered), solar Oberth at 6 solar radii, 1I 2052 DEC 09.
import numpy as np, json
from scipy.optimize import least_squares
from scipy.integrate import solve_ivp
exec(open('lyra.py').read().split('# Table 2 schedule')[0])
E33,J34=load('earth2033.csv'),load('jupiter2034.csv')
T0,TJ,T1=jd('2033-05-08'),jd('2034-07-30'),jd('2052-12-09')
rE,vE=at(E33,T0); rJ,vJ=at(J34,TJ); r1,_=at(O,T1)
RP=6*695700/149597870.7  # 6 solar radii in au
# Leg 1: Earth -> Jupiter
vE1,vJin=lambert(rE,rJ,TJ-T0)
print('Earth v_inf %.2f km/s (paper C3 121 -> 11.0); Jupiter arrival v_inf %.2f km/s'%(np.linalg.norm(vE1-vE)*AUD,np.linalg.norm(vJin-vJ)*AUD))
def rhs(t,y): r=y[:3]; return np.concatenate([y[3:],-MU*r/np.linalg.norm(r)**3])
def perihelion(y0):
    # propagate until radial velocity turns positive (perihelion); event-based
    ev=lambda t,y: np.dot(y[:3],y[3:]); ev.terminal=True; ev.direction=1
    s=solve_ivp(rhs,(0,3000),y0,events=ev,rtol=1e-11,atol=1e-14,method='DOP853',max_step=20)
    if not s.t_events[0].size: return None
    return s.t_events[0][0], s.y_events[0][0]
def resid(x):
    vout=x[:3]; dv=x[3]
    p=perihelion(np.concatenate([rJ,vout]))
    if p is None: return np.array([10,10,10,10.])
    tp,yp=p; rp,vp=yp[:3],yp[3:]
    v2=vp+dv*vp/np.linalg.norm(vp)   # tangential burn
    s=solve_ivp(rhs,(0,T1-TJ-tp),np.concatenate([rp,v2]),rtol=1e-11,atol=1e-14,method='DOP853')
    rend=s.y[:3,-1]
    return np.concatenate([[ (np.linalg.norm(rp)-RP)/RP ], (rend-r1)/10.0])
# initial guess: nearly cancel Jupiter's orbital motion, keep the angular momentum for a 6 SR perihelion
hJ=np.cross(rJ,vJ); hn=hJ/np.linalg.norm(hJ); rn=rJ/np.linalg.norm(rJ); tn=np.cross(hn,rn)
best=None
for vt in (0.5,1.0,1.5):           # km/s tangential
    for vr in (-1.0,0.0,1.0):      # km/s radial
        for dv in (5.0,7.0,9.0):   # km/s at perihelion
            x0=np.concatenate([(vt*tn+vr*rn)/AUD,[dv/AUD]])
            try: r=least_squares(resid,x0,xtol=1e-12,ftol=1e-12,max_nfev=300)
            except Exception as e: continue
            if best is None or r.cost<best.cost: best=r
x=best.x; vout=x[:3]
tp,yp=perihelion(np.concatenate([rJ,vout])); rp,vp=yp[:3],yp[3:]
from datetime import datetime,timedelta
print('cost %.3g'%best.cost)
print('Jupiter v_inf in %.2f out %.2f km/s (paper: unpowered)'%(np.linalg.norm(vJin-vJ)*AUD,np.linalg.norm(vout-vJ)*AUD))
print('perihelion %.4f au = %.2f SR, on %s, speed %.1f km/s, burn %.2f km/s (paper 7.2)'%(np.linalg.norm(rp),np.linalg.norm(rp)/(695700/149597870.7),(datetime(2000,1,1,12)+timedelta(days=TJ+tp-2451545.0)).date(),np.linalg.norm(vp)*AUD,x[3]*AUD))
# flyby altitude for the turn from vJin to vout
vin=vJin-vJ; vo=vout-vJ; muJ=MU*(1/1047.3486); d=np.arccos(np.clip(np.dot(vin,vo)/np.linalg.norm(vin)/np.linalg.norm(vo),-1,1)); vinf=np.linalg.norm(vin)
rperi=muJ/vinf**2*(1/np.sin(d/2)-1); print('flyby turn %.1f deg -> periapsis %.2f Jupiter radii'%(np.degrees(d),rperi*149597870.7/71492))
# sample
pts=[]
dts=np.arange(0,TJ-T0,2); s=solve_ivp(rhs,(0,TJ-T0),np.concatenate([rE,vE1]),t_eval=dts,rtol=1e-11,atol=1e-14,method='DOP853')
for t,r in zip(dts,s.y[:3].T): pts.append([round(T0+t,3)]+[round(v,5) for v in r])
dts=np.concatenate([np.arange(0,tp-5,1.0),np.arange(tp-5,tp,0.05)]); s=solve_ivp(rhs,(0,tp),np.concatenate([rJ,vout]),t_eval=dts,rtol=1e-11,atol=1e-14,method='DOP853',max_step=20)
for t,r in zip(dts,s.y[:3].T): pts.append([round(TJ+t,3)]+[round(v,5) for v in r])
v2=vp+x[3]*vp/np.linalg.norm(vp); dur=T1-TJ-tp
dts=np.concatenate([np.arange(0,5,0.05),np.arange(5,200,1.0),np.arange(200,dur,30)]); s=solve_ivp(rhs,(0,dur),np.concatenate([rp,v2]),t_eval=dts,rtol=1e-11,atol=1e-14,method='DOP853')
for t,r in zip(dts,s.y[:3].T): pts.append([round(TJ+tp+t,3)]+[round(v,5) for v in r])
pts.append([round(T1,3)]+[round(v,5) for v in r1])
print('end error %.3f au'%np.linalg.norm(s.y[:3,-1]-r1), len(pts),'points')
json.dump({'tp':TJ+tp,'pts':pts},open('lyra1_points_tdb.json','w'))
